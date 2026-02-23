from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking.line"
    

    compliant_quantity = fields.Float("Quantité conforme", digits='Product Unit of Measure', required=True, compute="_compute_compliant_quantity")
    quantity = fields.Float(string="Quantité non conforme")

    @api.depends("quantity")
    def _compute_compliant_quantity(self):
        for line in self:
            if line.move_id.is_compliant == "notcompliant":
                line.compliant_quantity = line.move_id.product_uom_qty - line.quantity
            else:
                line.quantity = 0
                line.compliant_quantity = line.move_id.product_uom_qty

    @api.onchange("quantity")
    def _compute_quantity(self):
        for line in self:
            if line.quantity > line.move_id.product_uom_qty:
                line.quantity = line.move_id.product_uom_qty