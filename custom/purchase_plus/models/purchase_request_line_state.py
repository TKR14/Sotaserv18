from odoo import models, fields


class PurchaseRequestLineState(models.Model):
    _name = "purchase.request.line.state"
    _description = "États des LDA"
    _order = "sequence"

    name = fields.Char(string="Nom", required=True)
    sequence = fields.Integer(string="Séquence", required=True)
    selection_id = fields.Many2one("ir.model.fields.selection")
    selection_ids = fields.Many2many("ir.model.fields.selection", compute="_compute_selection_ids")

    def _compute_selection_ids(self):
        exclude = self.search([]).mapped("selection_id").ids
        include = self.env["ir.model.fields.selection"].search([("field_id.model_id.model", "=", "purchase.request.line"), ("field_id.name", "=", "state"), ("id", "not in", exclude)])
        self.search([]).selection_ids = include