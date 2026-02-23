
from odoo import fields, models


class PurchaseVerificationLine(models.TransientModel):
    _name = "purchase.verification.line"
    
    purchase_verification_id = fields.Many2one("purchase.verification", "Vérification d'achat")
    line_id = fields.Many2one("purchase.request.line", "Ligne de demande d'achat")
    request_id = fields.Many2one("purchase.request", "Demande d'achat", related="line_id.request_id")
    product_id = fields.Many2one("product.product", "Article", related="line_id.product_id")
    product_qty = fields.Float("Quantité à acheter", digits="Product Unit of Measure")
    available_qty = fields.Float("Quantité disponible", digits="Product Unit of Measure")
    product_uom_id = fields.Many2one("uom.uom", "UoM", required=True)
    purchase_type = fields.Selection([("purchase_validated", "Achat validé"), ("transfer_validated", "Transfert validé")], string="Type d'achat", default="purchase_validated")