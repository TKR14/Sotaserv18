from odoo import models, fields, api
from odoo.exceptions import UserError

from datetime import date


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_outgoing_process = fields.Boolean(default=False)
    is_logistic = fields.Boolean(default=False)
    is_scrap_process = fields.Boolean(default=False)
    is_return_process = fields.Boolean(default=False)
    is_internal_transfer_process = fields.Boolean(default=False)
    product_ids = fields.Many2many("product.product", string="Articles Disponible")
    reason = fields.Char(string="Motif", tracking=True)
    out_number = fields.Char("N° de sortie")
    scrap_number = fields.Char("N° de rebut")
    return_number = fields.Char("N° de retour")
    internal_transfer_number = fields.Char("N° de Transfert")
    employee_id = fields.Many2one("hr.employee", "Demandeur")
    transfer_group_reference = fields.Char("Référence Bon de Transfert")
    scrap_state = fields.Selection([
        ("draft", "Brouillon"),
        ("submitted", "Soumis"),
        ("confirmed", "Confirmé"),
        ("done", "Traité"),
    ], string="Statut de Rebut", default="draft", tracking=True)
    return_state = fields.Selection([
        ("draft", "Brouillon"),
        ("submitted", "Soumis"),
        ("done", "Validé"),
    ], string="Statut de Retour", default="draft", tracking=True)
    internal_transfer_state = fields.Selection([
        ("draft", "Brouillon"),
        ("submitted", "Soumis"),
        ("validated", "Validé"),
        ("done", "Cloturé"),
    ], string="Statut de Transfert intersiège", default="draft", tracking=True)

    destination_site_id = fields.Many2one('building.site', "Affaire Destination", domain="[('id','!=', site_id)]")

    is_user_site = fields.Boolean(compute="_compute_user_sites", store=False)
    is_user_destination_site = fields.Boolean(compute="_compute_user_sites", store=False)

    def action_open_user_stock_picking_log(self, group):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
            ("group_id.name", "=", group),
            ("active", "=", True)
        ])
        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'search_default_origin': 1,
            'create': False, 
            'edit': False, 
            'delete': False
        }

        domain = [
            ('is_logistic', '=', True),
            ('site_id', 'in', site_ids)
        ]

        return {
            'name': 'Affectations',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': domain,
            'context': context,
            'search_view_id': self.env.ref('stock.view_picking_internal_search').id,
        }

    @api.depends('site_id', 'destination_site_id')
    def _compute_user_sites(self):
        Profile = self.env['building.profile.assignment']
        group = self.env.ref('building_plus.sotaserv_magasinier_chantier')

        user_id = self.env.user.id

        for record in self:
            record.is_user_site = False
            record.is_user_destination_site = False

            if record.site_id:
                record.is_user_site = bool(Profile.search([
                    ('user_id', '=', user_id),
                    ('group_id', '=', group.id),
                    ('site_id', '=', record.site_id.id),
                ], limit=1))

            if record.destination_site_id:
                record.is_user_destination_site = bool(Profile.search([
                    ('user_id', '=', user_id),
                    ('group_id', '=', group.id),
                    ('site_id', '=', record.destination_site_id.id),
                ], limit=1))

    def _set_number(self):
        site_code = self.site_id.code
        year = self.scheduled_date.year
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        if self.is_outgoing_process:
            number = self.search_count([
                ("id", "!=", self.id),
                ("state", "=", "done"),
                ("site_id", "=", self.site_id.id),
                ("is_outgoing_process", "=", True),
                ("picking_type_id.code", "=", "outgoing"),
                ("scheduled_date", ">=", start_date),
                ("scheduled_date", "<=", end_date),
            ]) + 1
            self.out_number = f"{site_code}/{year}/S/{number:06}" # SITE_CODE/2024/S/000004
            
        if self.is_scrap_process:
            number = self.search_count([
                ("id", "!=", self.id),
                ("scrap_state", "=", "confirmed"),
                ("site_id", "=", self.site_id.id),
                ("is_scrap_process", "=", True),
                ("picking_type_id.code", "=", "internal"),
                ("scheduled_date", ">=", start_date),
                ("scheduled_date", "<=", end_date),
            ]) + 1
            self.scrap_number = f"{site_code}/{year}/R/{number:06}" # SITE_CODE/2024/R/000004

        if self.is_return_process:
            number = self.search_count([
                ("id", "!=", self.id),
                ("return_state", "=", "done"),
                ("site_id", "=", self.site_id.id),
                ("is_return_process", "=", True),
                ("picking_type_id.code", "=", "outgoing"),
                ("scheduled_date", ">=", start_date),
                ("scheduled_date", "<=", end_date),
            ]) + 1
            self.return_number = f"{site_code}/{year}/RT/{number:06}" # SITE_CODE/2024/RT/000004

        if self.is_internal_transfer_process:
            number = self.search_count([
                ("id", "!=", self.id),
                ("internal_transfer_state", "=", "done"),
                ("site_id", "=", self.site_id.id),
                ("is_internal_transfer_process", "=", True),
                ("picking_type_id.code", "=", "internal"),
                ("scheduled_date", ">=", start_date),
                ("scheduled_date", "<=", end_date),
            ]) + 1
            self.internal_transfer_number = f"{site_code}/{year}/TR/{number:06}" # SITE_CODE/2024/RT/000004

    def button_cancel_with_reason(self, reason=None):
        for picking in self:
            picking.write({'reason': reason, 'state': 'cancel'})

    def button_express(self):
        if not self.note:
            raise UserError("Merci d'ajouter le motif de sortie.")
        if len(self.move_ids_without_package) == 0:
            raise UserError("Merci d'ajouter des lignes.")
        if any(move.product_uom_qty > move.outgoing_available for move in self.move_ids_without_package):
            raise UserError("Merci de saisir des quantités de Sortie valides.")
        self.action_confirm()
        self.action_assign()
        for move in self.move_ids_without_package:
            move.quantity_done = move.product_uom_qty
        self.button_validate()
        self._set_number()

    def open_cancellation_reason_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Assistant de retour",
            "res_model": "cancellation.reason",
            "view_mode": "form",
            "target": "new",
        }
    
    def button_draft_internal_transfer(self, reason=None):
        self.write({"internal_transfer_state": "draft"})
        self.message_post(body=f"""
            <ul>
                <li>Retour à l'état <strong>{dict(self._fields['scrap_state'].selection).get(self.scrap_state, self.scrap_state)}</strong></li>
                <li>Motif : {reason}</li>
            </ul>
        """)

    def button_resubmitted_internal_transfer(self, reason=None):
        self.write({"internal_transfer_state": "submitted"})
        self.message_post(body=f"""
            <ul>
                <li>Retour à l'état <strong>{dict(self._fields['scrap_state'].selection).get(self.scrap_state, self.scrap_state)}</strong></li>
                <li>Motif : {reason}</li>
            </ul>
        """)

    def button_draft_scrap(self, reason=None):
        self.write({"scrap_state": "draft"})
        self.message_post(body=f"""
            <ul>
                <li>Retour à l'état <strong>{dict(self._fields['scrap_state'].selection).get(self.scrap_state, self.scrap_state)}</strong></li>
                <li>Motif : {reason}</li>
            </ul>
        """)

    def button_resubmit_scrap(self, reason=None):
        for move in self.move_ids_without_package:
            move.state = 'draft'
            quant = self.env["stock.quant"].search([
                ("product_id", "=", move.product_id.id),
                ("location_id", "=", move.location_dest_id.id),
            ], limit=1)
            if quant:
                quant._update_available_quantity(move.product_id, move.location_dest_id, -move.product_uom_qty)
                quant._update_available_quantity(move.product_id, move.location_id, move.product_uom_qty)
        self.write({"scrap_state": "submitted"})
        self.message_post(body=f"""
            <ul>
                <li>Retour à l'état <strong>{dict(self._fields['scrap_state'].selection).get(self.scrap_state, self.scrap_state)}</strong></li>
                <li>Motif : {reason}</li>
            </ul>
        """)

    def button_draft_return(self, reason=None):
        self.write({"return_state": "draft"})
        self.message_post(body=f"""
            <ul>
                <li>Retour à l'état <strong>{dict(self._fields['return_state'].selection).get(self.return_state, self.return_state)}</strong></li>
                <li>Motif : {reason}</li>
            </ul>
        """)

    def button_submit_scrap(self):
        if not self.note:
            raise UserError("Merci d'ajouter le motif de Rebut.")
        if len(self.move_ids_without_package) == 0:
            raise UserError("Merci d'ajouter des lignes.")
        if any(move.product_uom_qty <= 0 or move.product_uom_qty > move.outgoing_available for move in self.move_ids_without_package):
            raise UserError("Merci de saisir des quantités de Rebut valides.")
        self.write({"scrap_state": "submitted"})
        self._set_number()

    def button_confirm_scrap(self):
        self.action_confirm()
        self.action_assign()
        for move in self.move_ids_without_package:
            move.quantity_done = move.product_uom_qty
        self.button_validate()
        self.write({"scrap_state": "confirmed"})

    def button_done_scrap(self):
        self.scrap_state = "done"

        warehouse = self.picking_type_id.warehouse_id
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "outgoing"), ("warehouse_id", "=", warehouse.id)],
            limit=1
        )

        new_picking = self.env["stock.picking"].create({
            "is_outgoing_process": True,
            "site_id": self.site_id.id,
            "scheduled_date": self.scheduled_date,
            "employee_id": self.employee_id.id,
            "picking_type_id": picking_type.id,
            "location_id": warehouse.rebut_location_id.id,
            "location_dest_id": warehouse.release_location_id.id,
            "note": f"Sortie de rebut {self.name}",
            "move_ids_without_package": [(0, 0, {
                "name": move.product_id.display_name,
                "product_id": move.product_id.id,
                "product_uom_qty": move.product_uom_qty,
                "product_uom": move.product_uom.id,
                "location_id": warehouse.rebut_location_id.id,
                "location_dest_id": warehouse.release_location_id.id,
            }) for move in self.move_ids_without_package],
        })

        new_picking.button_express()

    def button_submit_return(self):
        if not self.note:
            raise UserError("Merci d'ajouter le motif de Retour.")
        if len(self.move_ids_without_package) == 0:
            raise UserError("Merci d'ajouter des lignes.")
        if any(move.product_uom_qty <= 0 for move in self.move_ids_without_package):
            raise UserError("Merci de saisir des quantités de Retour valides.")
        self.write({"return_state": "submitted"})
        self._set_number()

    def button_submit_internal_transfer(self):
        if not self.note:
            raise UserError("Merci d'ajouter le motif de Transfert intersiège.")
        if len(self.move_ids_without_package) == 0:
            raise UserError("Merci d'ajouter des lignes.")
        if any(move.product_uom_qty <= 0 for move in self.move_ids_without_package):
            raise UserError("Merci de saisir des quantités de Transfert valides.")
        self.write({"internal_transfer_state": "submitted"})
        self._set_number()

    def button_validate_internal_transfert(self):
        self.write({"internal_transfer_state": "validated"})

    def button_done_internal_transfert(self):
        self.action_confirm()
        self.action_assign()
        for move in self.move_ids_without_package:
            move.quantity_done = move.product_uom_qty
        self.button_validate()
        self.write({"internal_transfer_state": "done"})

    def button_done_return(self):
        self.action_confirm()
        self.action_assign()
        for move in self.move_ids_without_package:
            move.quantity_done = move.product_uom_qty
        self.button_validate()
        self.write({"return_state": "done"})

    @api.onchange("site_id")
    def _onchange_site_id(self):
        if not self.site_id:
            self.picking_type_id = False
            self.location_id = False
            self.location_dest_id = False
            return

        warehouse = self.site_id.warehouse_id

        if self.is_outgoing_process:
            picking_type = self.env["stock.picking.type"].search(
                [("code", "=", "outgoing"), ("warehouse_id", "=", warehouse.id)], limit=1
            )
            self.picking_type_id = picking_type.id
            self.location_id = warehouse.lot_stock_id.id
            self.location_dest_id = warehouse.release_location_id.id

        elif self.is_scrap_process:
            picking_type = self.env["stock.picking.type"].search(
                [("code", "=", "internal"), ("warehouse_id", "=", warehouse.id)], limit=1
            )
            self.picking_type_id = picking_type.id
            self.location_id = warehouse.lot_stock_id.id
            self.location_dest_id = warehouse.rebut_location_id.id

        elif self.is_return_process:
            picking_type = self.env["stock.picking.type"].search(
                [("code", "=", "outgoing"), ("warehouse_id", "=", warehouse.id)], limit=1
            )
            self.picking_type_id = picking_type.id
            self.location_id = warehouse.lot_stock_id.id
            siege_warehouse = self.env["stock.warehouse"].search(
                [("code", "=", "000")], limit=1
            )
            self.location_dest_id = siege_warehouse.lot_stock_id.id

        elif self.is_internal_transfer_process:
            picking_type = self.env["stock.picking.type"].search(
                [("code", "=", "internal"), ("warehouse_id", "=", warehouse.id)], limit=1
            )
            self.picking_type_id = picking_type.id
            self.location_id = warehouse.lot_stock_id.id

    @api.onchange('destination_site_id')
    def _onchange_destination_site_id(self):
        if not self.destination_site_id:
            self.location_dest_id = False
            return

        warehouse = self.destination_site_id.warehouse_id
        self.location_dest_id = warehouse.lot_stock_id.id

    def _get_need_line_ids_product_ids(self):
        product_ids = self.env["building.purchase.need.line"].search([
            ("id", "in", self.env["building.purchase.need"].search([
                ("site_id", "=", self.site_id.id)
            ]).line_ids.ids)
        ]).mapped("product_id").ids
        return product_ids

    @api.onchange("location_id", "move_ids_without_package")
    def _onchange_location_id(self):
        if self.is_outgoing_process or self.is_scrap_process or self.is_return_process or self.is_internal_transfer_process:
            if self.location_id:
                exclude_ids = self.move_ids_without_package.mapped("product_id").ids
                domain = [
                    ("location_id", "=", self.location_id.id),
                    ("product_id", "not in", exclude_ids),
                    ("quantity", ">", 0),
                ]
                if self.env.context.get("is_logistic"):
                    domain.append(("product_id.categ_id.category_type", "in", ["equipment", "small_equipment"]))
                else:
                    domain.append(("product_id.categ_id.category_type", "=", "other"))

                self.product_ids = self.env["stock.quant"].search(domain).mapped("product_id")
            else:
                self.product_ids = False

    def action_get_user_stock_picking_incoming(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").mapped("location_id").ids
        types = self.env["stock.picking.type"].search([("code", "=", "incoming")]).ids

        return {
            "name": "Réceptions",
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "stock.picking",
            "views": [
                (self.env.ref("stock.vpicktree").id, "list"),
                (self.env.ref("stock.view_picking_form").id, "form")
            ],
            "domain": [("location_dest_id", "in", site_ids), ("picking_type_id", "in", types)],
        }
    
    def action_get_user_stock_picking_int(self, group, is_logistic=False):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        warehouse_ids = profile_ids.mapped("site_id").mapped("warehouse_id")

        lot_stock_ids = warehouse_ids.mapped("lot_stock_id").ids
        fuel_location_ids = warehouse_ids.mapped("fuel_location_id").ids
        transit_location_ids = warehouse_ids.mapped("transit_location_id").ids

        location_ids = lot_stock_ids + fuel_location_ids + transit_location_ids

        domain = [("location_dest_id", "in", location_ids), ("picking_type_code", "=", "internal")]

        name = "Transfert Interne"

        if is_logistic:
            domain.append(("is_logistic", "=", True))
            name = "Transfert Logistique"

        return {
            "name": name,
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "stock.picking",
            "views": [
                (self.env.ref("stock.vpicktree").id, "list"),
                (self.env.ref("stock.view_picking_form").id, "form")
            ],
            "domain": domain,
        }
    
    def action_get_stock_picking_int(self):
        site_002 = self.env["building.site"].search([("number", "=", "002")], limit=1)

        warehouse_ids = site_002.mapped("warehouse_id")
        lot_stock_ids = warehouse_ids.mapped("lot_stock_id").ids
        fuel_location_ids = warehouse_ids.mapped("fuel_location_id").ids
        transit_location_ids = warehouse_ids.mapped("transit_location_id").ids

        location_ids = lot_stock_ids + fuel_location_ids + transit_location_ids

        return {
            "name": "Transferts",
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "stock.picking",
            "views": [
                (self.env.ref("stock.vpicktree").id, "list"),
                (self.env.ref("stock.view_picking_form").id, "form")
            ],
            "domain": [("location_dest_id", "in", location_ids), ("picking_type_code", "=", "internal")],
        }

    def action_get_user_stock_picking_outgoing(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids

        return {
            "name": "Sortie de fourniture",
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "stock.picking",
            "views": [
                (self.env.ref("stock_plus.stock_picking_view_tree_outgoing").id, "list"),
                (self.env.ref("stock_plus.stock_picking_view_form_outgoing").id, "form"),
            ],
            "domain": [
                ("picking_type_code", "=", "outgoing"),
                ("site_id", "in", site_ids),
                ("is_outgoing_process", "=", True)
            ],
            "context": {
                "outgoing_process": True,
                "default_is_outgoing_process": True,
                "site_ids": site_ids,
                "default_picking_type_code": "outgoing",
            }
        }

    def action_get_user_stock_picking_return(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids

        domain = [("picking_type_code", "=", "outgoing"), ("site_id", "in", site_ids), ("is_return_process", "=", True)]
        context = {
            "return_process": True,
            "default_is_return_process": True,
            "site_ids": site_ids,
            "default_picking_type_code": "outgoing",
        }

        if group in ["SOTASERV_MAGASINIER"]:
            context.update({"create": False, "delete": False})
            domain = [
                ("picking_type_code", "=", "outgoing"),
                ("is_return_process", "=", True),
                ("return_state", "!=", "draft"),
            ]

        return {
            "name": "Retour",
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "stock.picking",
            "views": [
                (self.env.ref("stock_plus.stock_picking_view_tree_return").id, "list"),
                (self.env.ref("stock_plus.stock_picking_view_form_return").id, "form"),
            ],
            "domain": domain,
            "context": context,
        }

    def action_get_user_stock_picking_internal_transfer(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids

        domain = [("picking_type_code", "=", "internal"), ("site_id", "in", site_ids), ("is_internal_transfer_process", "=", True)]
        context = {
            "internal_transfer_process": True,
            "default_is_internal_transfer_process": True,
            "site_ids": site_ids,
            "default_picking_type_code": "internal",
        }

        if group in ["SOTASERV_MAGASINIER_CHANTIER"]:
            context.update({"create": False, "delete": False})
            domain.append(("internal_transfer_state", "!=", "draft"))

        return {
            "name": "Transfert intersiège",
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "stock.picking",
            "views": [
                (self.env.ref("stock_plus.stock_picking_view_tree_internal_transfer").id, "list"),
                (self.env.ref("stock_plus.stock_picking_view_form_internal_transfer").id, "form"),
            ],
            "domain": domain,
            "context": context,
        }
    
    def action_get_user_stock_picking_scrap(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids

        domain = [("picking_type_code", "=", "internal"), ("site_id", "in", site_ids), ("is_scrap_process", "=", True)]
        context = {
            "scrap_process": True,
            "default_is_scrap_process": True,
            "site_ids": site_ids,
            "default_picking_type_code": "internal",
        }

        if group in ["SOTASERV_CHEF_PROJET", "SOTASERV_DIRECTEUR_ZONE", "SOTASERV_MAGASINIER"]:
            context.update({"create": False, "delete": False})

        return {
            "name": "Rebut",
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "stock.picking",
            "views": [
                (self.env.ref("stock_plus.stock_picking_view_tree_scrap").id, "list"),
                (self.env.ref("stock_plus.stock_picking_view_form_scrap").id, "form"),
            ],
            "domain": domain,
            "context": context,
        }
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context.get

        if context('default_is_scrap_process'):
            employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            if employee:
                res['employee_id'] = employee.id

        if context('default_is_return_process'):
            employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            if employee:
                res['employee_id'] = employee.id

        if (context('default_is_outgoing_process') or context('default_is_scrap_process')) and context('is_logistic'):
            site = self.env['building.site'].search([('number', '=', '002')], limit=1)
            res['is_logistic'] = True
            if site:
                res['site_id'] = site.id

        if context('default_is_internal_transfer_process'):
            employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            if employee:
                res['employee_id'] = employee.id

        return res

class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    code = fields.Selection([
        ("incoming", "Réception"),
        ("outgoing", "Sortie"),
        ("internal", "Transfert"),
    ])

    def action_get_user_stock_picking_type(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        warehouse_ids = profile_ids.mapped("site_id").mapped("warehouse_id").ids

        domain = [("warehouse_id", "in", warehouse_ids)]
        if group == "SOTASERV_CONDUCT_TRV":
            domain.append(("code", "=", "incoming"))
        if group == "SOTASERV_DIRECTRICE_TECHNIQUE" or group == "SOTASERV_AUDITEUR":
            domain = []

        return {
            "name": "Aperçu de l'inventaire",
            "type": "ir.actions.act_window",
            "res_model": "stock.picking.type",
            "view_mode": "kanban",
            "domain": domain,
            "context": {
                "search_default_groupby_warehouse_id": True,
            }
        }


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def action_get_user_stock_quant(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        warehouse_ids = profile_ids.mapped("site_id").mapped("warehouse_id")

        lot_stock_ids = warehouse_ids.mapped("lot_stock_id").ids
        fuel_location_ids = warehouse_ids.mapped("fuel_location_id").ids
        transit_location_ids = warehouse_ids.mapped("transit_location_id").ids

        location_ids = lot_stock_ids + fuel_location_ids + transit_location_ids

        return {
            "name": "Stocks par emplacement",
            "type": "ir.actions.act_window",
            "res_model": "stock.quant",
            "view_mode": "list,form",
            "domain": [("location_id", "in", location_ids), ("location_id.usage", "=", "internal")],
            "context": {
                "search_default_sitegroup": True,
                "search_default_locationgroup": True,
            }
        }
    
    def action_get_site_user(self, readonly=False, nocreate=False):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
        ])

        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'create': False,
            'delete': False,
            'edit': False,
            'hide_actions':True,
        }

        domain = [
            ('site_id', 'in', site_ids),
        ]

        return {
            'name': 'Stocks par Emplacement',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'stock.quant',
            'views': [
                (self.env.ref('building.view_stock_quant_readonly_tree_inherit').id, 'list'),
                (self.env.ref('stock.view_stock_quant_form').id, 'form'),
            ],
            'domain': domain,
            'context': context,
        }