from odoo import models, fields
from odoo.exceptions import ValidationError


class StockPickingTransfer(models.TransientModel):
    _name = "stock.picking.transfer"
    
    line_ids = fields.One2many("stock.picking.transfer.line", "parent_id", string="Lignes")

    def button_transfer(self):
        for i, line in enumerate(self.line_ids, 1):
            if line.quantity > line.quantity_available:
                raise ValidationError(f"La quantité demandée est indisponible.\n\nArticle {line.product_id.name} / Ligne {i}.")

        if not self.line_ids:
            return

        request_lines = self.line_ids.mapped("request_line_id")
        requests = request_lines.mapped("request_id")
        to_transit = self.line_ids.filtered(lambda l: not l.request_line_id.product_id.categ_id.is_fuel)
        to_mobile = self.line_ids.filtered(lambda l: l.request_line_id.product_id.categ_id.is_fuel)
        transit_groups = [(request, to_transit.filtered(lambda line: line.request_line_id.request_id == request)) for request in requests if bool(to_transit.filtered(lambda line: line.request_line_id.request_id == request))]
        mobile_groups = [(request, to_mobile.filtered(lambda line: line.request_line_id.request_id == request)) for request in requests if bool(to_mobile.filtered(lambda line: line.request_line_id.request_id == request))]

        warehouse = self.env["stock.warehouse"].search([("code", "=", "000")], limit=1)
        source_id = warehouse.lot_stock_id.id
        mobile_id = warehouse.mobile_location_id.id
        picking_type_id = self.env["stock.picking.type"].search([("sequence_code", "=", "INT"), ("warehouse_id", "=", warehouse.id)], limit=1).id

        ids = []
        for request, lines in transit_groups:
            destination_id = request.site_id.warehouse_id.transit_location_id.id
            picking = self.env["stock.picking"].create(
                {
                    "site_id": request.site_id.id,
                    "location_id": source_id,
                    "location_dest_id": destination_id,
                    "picking_type_id": picking_type_id,
                    "origin": request.name,
                }
            )

            def _line_values(line):
                return {
                    "picking_id": picking.id,
                    "product_id": line.product_id.id,
                    "product_uom_qty": line.quantity,
                    "location_id": source_id,
                    "location_dest_id": destination_id,
                    "request_line_id": line.request_line_id.id,
                    "name": line.product_id.name,
                    "product_uom": line.product_id.uom_id.id,
                }

            picking.move_ids_without_package = self.env["stock.move"].create([_line_values(line) for line in lines])
            picking.action_confirm()
            picking.action_assign()
            ids.append(picking.id)

        # FUEL: 1/ HEADQUARTER TO MOBILE
        for request, lines in mobile_groups:
            picking = self.env["stock.picking"].create(
                {
                    "site_id": request.site_id.id,
                    "location_id": source_id,
                    "location_dest_id": mobile_id,
                    "picking_type_id": picking_type_id,
                    "origin": request.name,
                }
            )
            def _line_values(line):
                return {
                    "picking_id": picking.id,
                    "product_id": line.product_id.id,
                    "product_uom_qty": line.quantity,
                    "quantity_done": line.quantity,
                    "location_id": source_id,
                    "location_dest_id": mobile_id,
                    # "request_line_id": line.request_line_id.id,
                    "name": line.product_id.name,
                    "product_uom": line.product_id.uom_id.id,
                }
            picking.move_ids_without_package = self.env["stock.move"].create([_line_values(line) for line in lines])
            picking.action_confirm()
            picking.action_assign()
            picking.button_validate()

        # FUEL: 2/ MOBILE TO SITE
        for request, lines in mobile_groups:
            destination_id = request.site_id.warehouse_id.lot_stock_id.id
            picking = self.env["stock.picking"].create(
                {
                    "site_id": request.site_id.id,
                    "location_id": mobile_id,
                    "location_dest_id": destination_id,
                    "picking_type_id": picking_type_id,
                    "origin": request.name,
                }
            )
            def _line_values(line):
                return {
                    "picking_id": picking.id,
                    "product_id": line.product_id.id,
                    "product_uom_qty": line.quantity,
                    "location_id": mobile_id,
                    "location_dest_id": destination_id,
                    "request_line_id": line.request_line_id.id,
                    "name": line.product_id.name,
                    "product_uom": line.product_id.uom_id.id,
                }
            picking.move_ids_without_package = self.env["stock.move"].create([_line_values(line) for line in lines])
            picking.action_confirm()
            picking.action_assign()
            ids.append(picking.id)

        request_lines.state = "transfer_established"
        return {
            "name": "Transfert",
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "view_mode": "tree,form",
            "target": "current",
            "domain": [("id", "in", ids)],
        }


class StockPickingTransferLine(models.TransientModel):
    _name = "stock.picking.transfer.line"

    parent_id = fields.Many2one("stock.picking.transfer", string="Parent")
    request_line_id = fields.Many2one("purchase.request.line", string="Ligne de demande")
    product_id = fields.Many2one("product.product", string="Article")
    quantity = fields.Integer(string="Quantité")
    quantity_available = fields.Integer(string="Quantité disponible")
    source_id = fields.Many2one("stock.location", string="De")
    destination_id = fields.Many2one("stock.location", string="Vers")