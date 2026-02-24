from odoo import models, fields, api


class StockInventory(models.Model):
    _inherit = "stock.quant"

    from_excel = fields.Boolean()
    site_ids = fields.Many2many("building.site", "Affaires", compute="_compute_site_ids")
    site_id = fields.Many2one("building.site", "Affaire", domain="[('id', 'in', site_ids)]")

    @api.depends("display_name")
    def _compute_site_ids(self):
        for record in self:
            profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", "SOTASERV_CHEF_PROJET")])
            record.site_ids = profile_ids.mapped("site_id")

    @api.onchange("site_id")
    def _onchange_site_id(self):
        if self.site_id:
            self.location_ids = self.site_id.warehouse_id.lot_stock_id.ids
        else:
            self.location_ids = False

    def action_get_user_stock_inventory(self):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", "SOTASERV_CHEF_PROJET")])
        site_ids = profile_ids.mapped("site_id").ids

        return {
            "type": "ir.actions.act_window",
            "name": "Ajustements de l'inventaire",
            "res_model": self._name,
            "view_mode": "list,form",
            "domain": [("site_id", "in", site_ids)],
            "context": {"search_default_status": True, "search_default_site_id": True},
        }

    def action_open_inventory_lines(self):
        result = super().action_open_inventory_lines()
        result["name"] = "Lignes"
        result["context"].update({
            "create": False,
            "delete": False,
        })
        return result