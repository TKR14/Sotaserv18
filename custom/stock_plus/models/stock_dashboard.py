from odoo import models, fields

import xlsxwriter
import base64
import io
import os


class StockDashboard(models.TransientModel):
    _name = "stock.dashboard"

    def name_get(self):
        return [(record.id, "Tableau de bord") for record in self]

    site_id = fields.Many2one("building.site", string="Affaire")
    date = fields.Date(string="Date", default=fields.Datetime.now)
    type = fields.Selection(string="Type d'articles", selection=[
        ("stock", "Stock"),
        ("fuel", "Gasoil"),
    ])
    line_ids = fields.One2many("stock.dashboard.line", "parent_id")

    def download_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet_name = f"{self.site_id.display_name} le {self.create_date.strftime('%d_%m_%Y')}"
        worksheet = workbook.add_worksheet(sheet_name)

        header_format = workbook.add_format({
            "bold": True,
            "border": 1,
            "border_color": "#333333",
            "bg_color": "#D9D9D9",
        })

        cell_format = workbook.add_format({
            "border": 1,
            "border_color": "#333333",
        })

        headers = ["Article", "Initial", "Entré", "Sortie", "Actuel"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        for row, line in enumerate(self.line_ids, start=1):
            worksheet.write(row, 0, line.product_id.name, cell_format)
            worksheet.write(row, 1, line.initial, cell_format)
            worksheet.write(row, 2, line.stock_in, cell_format)
            worksheet.write(row, 3, line.stock_out, cell_format)
            worksheet.write(row, 4, line.current, cell_format)

        worksheet.autofit()
        workbook.close()
        output.seek(0)

        encoded = base64.b64encode(output.read())
        attachment = self.env["ir.attachment"].create({
            "name": sheet_name,
            "datas": encoded,
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "new"
        }


class StockDashboardLine(models.TransientModel):
    _name = "stock.dashboard.line"

    parent_id = fields.Many2one("stock.dashboard")
    warehouse_id = fields.Many2one("stock.warehouse", string="Entrepôt")
    location_id = fields.Many2one("stock.location", string="Emplacement")
    product_id = fields.Many2one("product.product", string="Article")
    initial = fields.Float("Initial")
    stock_in = fields.Float("Entré")
    stock_out = fields.Float("Sortie")
    current = fields.Float("Actuel")
    in_move_ids = fields.Many2many("stock.move.line")
    out_move_ids = fields.Many2many("stock.move.line", relation="stock_dashboard_line_stock_move_line_out_rel")

    def action_open_in_moves(self):
        return {
            "name": f"{self.product_id.name} / Entrés",
            "type": "ir.actions.act_window",
            "res_model": "stock.move.line",
            "view_mode": "list",
            "domain": [("id", "in", self.in_move_ids.ids)],
            "context": { "create": False, "delete": False, "edit": False },
            "target": "current",
        }

    def action_open_out_moves(self):
        return {
            "name": f"{self.product_id.name} / Sorties",
            "type": "ir.actions.act_window",
            "res_model": "stock.move.line",
            "view_mode": "list",
            "domain": [("id", "in", self.out_move_ids.ids)],
            "context": { "create": False, "delete": False, "edit": False },
            "target": "current",
        }