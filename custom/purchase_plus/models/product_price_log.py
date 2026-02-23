from odoo import fields, models


class ProductPriceLog(models.Model):
    _name = "product.price.log"
    _order = "create_date desc"

    site_id = fields.Many2one("building.site", string="Affaire")
    order_id = fields.Many2one("purchase.order", string="Bon de commande")
    product_id = fields.Many2one("product.template", string="Article")
    old_price = fields.Float("Ancien prix")
    new_price = fields.Float("Nouveau prix")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    price_log_ids = fields.One2many("product.price.log", "product_id", string="Journal des prix")


class ProductProduct(models.Model):
    _inherit = "product.product"

    reference_price = fields.Float("Prix référence", related="product_tmpl_id.reference_price")