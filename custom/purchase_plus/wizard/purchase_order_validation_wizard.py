from odoo import fields, models, api

from datetime import datetime


class PurchaseOrderValidationWizard(models.TransientModel):
    _name = "purchase.order.validation.wizard.line"

    parent_id = fields.Many2one("purchase.order.validation.wizard")
    order_line_id = fields.Many2one("purchase.order.line")
    product_id = fields.Many2one("product.product", related="order_line_id.product_id", string="Article")
    product_price = fields.Float(related="product_id.reference_price", string="Prix référence", readonly=True, help="")
    need_price = fields.Float("LDB", readonly=True)
    offer_price = fields.Float(related="order_line_id.price_unit", string="Offre")
    update_need = fields.Boolean("MAJ LDB")
    update_product = fields.Boolean("MAJ Article")
    can_update_product = fields.Boolean("Peut MAJ Article", compute="_compute_can_update_product")

    @api.depends("offer_price", "product_price")
    def _compute_can_update_product(self):
        for line in self:
            line.can_update_product = line.offer_price != line.product_price


class PurchaseOrderValidationWizard(models.TransientModel):
    _name = "purchase.order.validation.wizard"

    order_id = fields.Many2one("purchase.order")
    site_id = fields.Many2one("building.site", related="order_id.site_id", string="Affaire")
    currency_id = fields.Many2one("res.currency", related="order_id.currency_id", string="Devise")
    line_ids = fields.One2many("purchase.order.validation.wizard.line", "parent_id", string="Lignes")

    def button_validate(self):       
        def _format_price(price):
            return f"{price:,.2f}".replace(',', ' ').replace('.', ',')

        for line in self.line_ids:
            if line.update_need:
                need = self.env["building.purchase.need"].search([("site_id", "=", self.site_id.id)])
                new_price = line.offer_price
                need_line = line.order_line_id._get_need_line()            
                if need_line:
                    old_price = need_line.price_unit
                    need_line.price_unit = new_price
                    self.env["building.purchase.need.flow"].create({
                        "need_id": need.id,
                        "user_id": self.env.user.id,
                        "date": datetime.now(),
                        "note": f"{line.product_id.name} - {_format_price(old_price)} > {_format_price(new_price)}"
                    })
            if line.update_product:
                product = line.product_id.product_tmpl_id
                new_price = line.offer_price
                old_price = product.reference_price
                product.sudo().write({"reference_price": new_price})
                self.env["product.price.log"].create({
                    "site_id": self.site_id.id,
                    "order_id": self.order_id.id,
                    "product_id": product.id,
                    "old_price": old_price,
                    "new_price": new_price,
                })

        self.order_id.state = "validated_2"
        return {"type": "ir.actions.act_window_close"}