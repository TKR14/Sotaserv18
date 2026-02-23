from odoo import models, fields, api


class DashboardStockWizard(models.TransientModel):
    _name = "dashboard.stock.wizard"
    _description = "Stock Dashboard Wizard"

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", "SOTASERV_MAGASINIER_CHANTIER")])
        result["site_ids"] = profile_ids.mapped("site_id")
        return result

    site_ids = fields.Many2many("building.site", string="Affaires")
    site_id = fields.Many2one("building.site", string="Affaire", domain="[('id', 'in', site_ids)]")
    date = fields.Date(string="Date de début", readonly=True, default=lambda _: fields.Date.today().replace(month=1, day=1))
    type = fields.Selection(string="Type d'articles", default="stock", selection=[
        ("stock", "Stock"),
        ("fuel", "Gasoil"),
    ])      

    def action_confirm(self):
        self.env["stock.dashboard"].search([]).unlink()
        
        pickings = self._get_pickings()
        products = pickings.mapped("move_line_ids_without_package.product_id").filtered(lambda p: p.categ_id.is_fuel == (self.type == "fuel"))
        lines = []

        for product in products:
            moves = self.env["stock.move.line"].search([
                ("picking_id", "in", pickings.ids),
                ("product_id", "=", product.id),
                ("picking_id.site_id", "=", self.site_id.id),
                ("picking_id.date_done", ">=", self.date),
            ])

            in_moves = moves.filtered(lambda m: m.picking_id.picking_type_id.code in ["incoming", "internal"])
            out_moves = moves.filtered(lambda m: m.picking_id.picking_type_id.code == "outgoing")
            stock_in = sum(in_moves.mapped("qty_done"))
            stock_out = sum(out_moves.mapped("qty_done"))

            moves = self.env["stock.move.line"].search([
                ("product_id", "=", product.id),
                ("picking_id.site_id", "=", self.site_id.id),
                ("picking_id.date_done", "<", self.date),
            ])

            initial_stock_in = sum(moves.filtered(lambda m: m.picking_id.picking_type_id.code == "incoming").mapped("qty_done"))
            initial_stock_out = sum(moves.filtered(lambda m: m.picking_id.picking_type_id.code == "outgoing").mapped("qty_done"))

            initial = initial_stock_in - initial_stock_out
            current = initial + stock_in - stock_out

            lines.append((0, 0, {
                "warehouse_id": product.warehouse_id.id,
                "location_id": product.location_id.id,
                "product_id": product.id,
                "initial": initial,
                "stock_in": stock_in,
                "stock_out": stock_out,
                "current": current,
                "in_move_ids": in_moves.ids,
                "out_move_ids": out_moves.ids,
            }))

        dashboard = self.env["stock.dashboard"].create({
            "site_id": self.site_id.id,
            "date": self.date,
            "type": self.type,
            "line_ids": lines,
        })

        return {
            "type": "ir.actions.act_window",
            "name": "Tableau de bord",
            "res_model": "stock.dashboard",
            "res_id": dashboard.id,
            "view_mode": "form",
            "target": "main",
        }   

    def _get_pickings(self):
        return self.env["stock.picking"].search([
            ("site_id", "=", self.site_id.id),
            ("date_done", ">=", self.date),
            ("state", "=", "done"),
        ])