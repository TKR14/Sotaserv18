from odoo import models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    def name_get(self):
        return [(picking_type.id, picking_type.name) for picking_type in self]

    def get_stock_picking_action(self):
        site = self.env["building.site"].search([("warehouse_id", "=", self.warehouse_id.id)], limit=1)
        view_form_id = self.env.ref("stock.view_picking_form").id

        if self.env.user.has_group("building_plus.sotaserv_conduct_trv"):
            view_form_id = self.env.ref("stock_plus.stock_picking_view_form_conduct_trv").id
        if self.env.user.has_group("building_plus.sotaserv_directrice_technique"):
            view_form_id = self.env.ref("stock_plus.stock_picking_view_form_conduct_trv").id
        if self.env.user.has_group("building_plus.sotaserv_magasinier_chantier"):
            view_form_id = self.env.ref("stock_plus.stock_picking_view_form_magasinier_chantier").id

        views = [
            (self.env.ref("stock_plus.stock_picking_view_tree_no_buttons").id, "list"),
            (view_form_id, "form"),
        ]
        domain = [("site_id", "=", site.id), ("picking_type_id.sequence_code", "=", self.sequence_code), ("location_dest_id.usage", "!=", "mobile")]
        if self.code == "outgoing":
            domain.append(("is_outgoing_process", "=", True))
            views = [
                (self.env.ref("stock_plus.stock_picking_view_tree_outgoing").id, "list"),
                (self.env.ref("stock_plus.stock_picking_view_form_outgoing").id, "form"),
            ]

        return {
            "name": self.name,
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "stock.picking",
            "domain": domain,
            "views": views,
        }