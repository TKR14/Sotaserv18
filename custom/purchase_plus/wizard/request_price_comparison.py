from odoo import api, fields, models


class PurchaseRequestPriceComparisonCodes(models.TransientModel):
    _name = 'purchase.request.price.comparison.codes'

    name = fields.Char()

class PurchaseRequestPriceComparison(models.TransientModel):
    _inherit = 'purchase.request.price.comparison'

    @api.model
    def initialize(self):
        env = self.env["purchase.request.price.comparison.codes"]
        env.search([]).unlink()

        available_po_records = self.env["purchase.order"].search([("purchase_order_code", "!=", False), ("state", "=", "draft")])
        available_po_records = available_po_records.mapped("purchase_order_code")
        available_po_records = [rec for rec in available_po_records if available_po_records.count(rec) > 1]

        used_po_records = self.env["purchase.price.comparison"].search([("state", "=", "draft")])
        available_po_codes = list(set(available_po_records) - set(used_po_records.mapped("purchase_order_code")))

        for code in available_po_codes:
            env.create({"name": code})

    purchase_order_codes = fields.Many2one("purchase.request.price.comparison.codes", string="Demande de prix")
    