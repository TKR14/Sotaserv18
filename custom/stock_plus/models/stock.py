from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from lxml import etree


class BuildingSite(models.Model):
    _inherit = "building.site"

    warehouse_id = fields.Many2one("stock.warehouse", string="Entrepôt")

    def _create_warehouse(self):
        warehouse = self.env["stock.warehouse"].create(
            {
                "name": self.name,
                "code": self.number[-3:],
                "site_id": self.id,
            }
        )
        self.warehouse_id = warehouse.id
        warehouse.view_location_id.name = self.code


class StockLocation(models.Model):
    _inherit = "stock.location"

    usage = fields.Selection(
        [
            ('view', 'View'),
            ('internal', 'Internal Location'),
            ("fuel", "Emplacement carburant"),
            ('transit', 'Transit Location'),
            ('mobile', 'Mobile'),
            ('release', 'Emplacement sortie'),
            ('supplier', 'Vendor Location'),
            ('customer', 'Customer Location'),
            ('inventory', 'Inventory Loss'),
            ('production', 'Production'),
        ]
    )


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    def name_get(self):
        return [(warehouse.id, warehouse.site_id and (warehouse.site_id.code or warehouse.site_id.number[-3:]) or "") for warehouse in self]

    site_id = fields.Many2one("building.site", string="Affaire")
    fuel_location_id = fields.Many2one("stock.location", string="Emplacement de carburant")
    transit_location_id = fields.Many2one("stock.location", string="Emplacement de transit")
    release_location_id = fields.Many2one("stock.location", string="Emplacement de sortie")
    rebut_location_id = fields.Many2one("stock.location", string="Emplacement de Rebut")
    mobile_location_id = fields.Many2one("stock.location", string="Mobile", domain=[("usage", "=", "mobile")])

    def create_release_location_ids(self):
        for warehouse in self:
            warehouse.write({"name": warehouse.name[:-1]})

    def _get_locations_values(self, vals, code=False):
        result = super(StockWarehouse, self)._get_locations_values(vals, code)
        code = vals.get("code") or code or ""
        code = code.replace(' ', '').upper()
        result.update({
            "fuel_location_id": {
                "name": "Carburant",
                "active": True,
                "usage": "fuel",
                "barcode": f"{code}-FUEL",
            },
            "transit_location_id": {
                "name": "Transit",
                "active": True,
                "usage": "transit",
                "barcode": f"{code}-TRANSIT",
            },
            "release_location_id": {
                "name": "Sortie",
                "active": True,
                "usage": "release",
                "barcode": f"{code}-RELEASE",
            },
            "rebut_location_id": {
                "name": "Rebut",
                "active": True,
                "usage": "inventory",
                "barcode": f"{code}-REBUT",
            },
        })
        return result
    
    def create_rebut_locations(self):
        """Créer un emplacement Rebut pour tous les entrepôts qui n'en ont pas encore"""
        for wh in self.search([]):
            if not wh.rebut_location_id:
                location = self.env['stock.location'].create({
                    'name': "Rebut",
                    'location_id': wh.view_location_id.id,
                    'usage': 'inventory',
                    'company_id': wh.company_id.id,
                    'active': True,
                    'barcode': f"{wh.name}-REBUT",
                    'scrap_location': True,
                })
                wh.rebut_location_id = location.id
        return True

    def _get_picking_type_create_values(self, max_sequence):
        result = super(StockWarehouse, self)._get_picking_type_create_values(max_sequence)
        result[0]["in_type_id"]["name"] = "Réception"
        result[0]["int_type_id"]["name"] = "Transfert"
        result[0]["out_type_id"]["name"] = "Sortie"
        return result


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    direction_qty = fields.Float("Quantité", compute="_compute_direction_qty")

    def _compute_direction_qty(self):
        for line in self:
            sign = line.picking_code == "outgoing" and -1 or 1
            line.direction_qty = line.qty_done * sign

    @api.constrains('qty_done')
    def _check_positive_qty_done(self):
        if any([ml.qty_done < 0 for ml in self]):
            raise ValidationError(_('You can not enter negative quantities.'))

        def _format_number(number):
            return f"{number:,.2f}".replace(",", " ").replace(".", ",")

        def _exceeded_tolerated_quantity(line):
            order_line_id = line.move_id.purchase_line_id
            tolerated_quantity = order_line_id.product_qty * (1 + line.company_id.purchase_tolerance / 100)
            received_quantity = order_line_id.qty_received
            remaining_quantity = tolerated_quantity - received_quantity
            to_be_received = received_quantity + line.qty_done
            if to_be_received > tolerated_quantity and line.picking_id.picking_type_id.code == "incoming":
                return f"- {line.product_id.name} {_format_number(remaining_quantity)} ({_format_number(tolerated_quantity)})"
            else:
                return False

        exceeding_lines = [_exceeded_tolerated_quantity(ml) for ml in self]
        if any(exceeding_lines):
            message = "Vous ne pouvez pas dépasser la quantité tolérée.\n"
            for line in exceeding_lines:
                message += f"\n{line}"
            raise ValidationError(message)


class StockMove(models.Model):
    _inherit = "stock.move"

    request_line_id = fields.Many2one("purchase.request.line", string="Ligne de demande")
    outgoing_available = fields.Float("Disponible", compute="_compute_outgoing_available")
    direction_qty = fields.Float("Demande", compute="_compute_direction_qty")

    @api.onchange("product_uom_qty")
    def onchange_product_uom_qty(self):
        for move in self:
            if move.product_id and (move.product_uom_qty <= 0 or move.product_uom_qty > move.outgoing_available):
                raise UserError(f"Quantité invalide pour {move.product_id.name}.")

    @api.constrains("product_uom_qty")
    def _check_product_uom_qty(self):
        for move in self:
            if move.picking_id.is_outgoing_process:
                if move.product_uom_qty <= 0 or move.product_uom_qty > move.outgoing_available:
                    raise UserError("Merci de saisir des quantités de Sortie valides.")

    @api.onchange("product_id")
    def _onchange_product_id(self):
        self._compute_outgoing_available()

    @api.depends("picking_id.move_ids_without_package", "product_id")
    def _compute_outgoing_available(self):
        for move in self:
            if self.env.context.get("outgoing_process") or self.env.context.get("scrap_process") or self.env.context.get("return_process") or self.env.context.get("internal_transfer_process"):
                stock = self.env["stock.quant"].search([("site_id", "=", move.site_id.id), ("location_id", "=", move.location_id.id), ("product_id", "=", move.product_id.id)])
                move.outgoing_available = stock.available_quantity
            else: 
                move.outgoing_available = 0

    def _get_out_move_lines(self):
        """ Returns the `stock.move.line` records of `self` considered as outgoing. It is done thanks
        to the `_should_be_valued` method of their source and destionation location as well as their
        owner.

        :returns: a subset of `self` containing the outgoing records
        :rtype: recordset
        """
        
        res = self.env['stock.move.line']
        for move_line in self.move_line_ids:
            try:
                if move_line.owner_id and move_line.owner_id != move_line.company_id.partner_id:
                    continue
                if move_line.location_id._should_be_valued() and not move_line.location_dest_id._should_be_valued():
                    res |= move_line
            except:
                raise Exception(move_line.location_id, move_line.location_dest_id)
        return res

    def _compute_direction_qty(self):
        for move in self:
            sign = move.picking_code == "outgoing" and -1 or 1
            move.direction_qty = move.product_uom_qty * sign


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.model
    def _get_quants_action(self, domain=None, extend=False):
        domain.append(("location_id.barcode", "not ilike", "%-RELEASE"))
        return super(StockQuant, self)._get_quants_action(domain, extend)