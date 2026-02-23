from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError
from lxml import etree

class PurchaseOrderLineDetail(models.Model):
    _name = "purchase.order.line.detail"
    _description = 'Purchase Order Line Detail'

    name = fields.Char(string='Description', required=True)
    quantity_type = fields.Selection([
        ("quantity", "Q"),
        ("percentage", "%"),
    ], default="percentage", string="Quantité", required=True)
    quantity_pr = fields.Float(string='Quantité', required=True)
    unit_measurement = fields.Many2one('uom.uom', string='Unité de mesure', required=True)
    price_unit = fields.Float(string='Prix ​​unitaire', required=True)
    subtotal = fields.Float(string='Prix total', compute='_compute_subtotal', required=True)
    
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='Ligne de bon de commande')
    # entry_line_id = fields.Many2one('purchase.entry.line')

    @api.onchange('quantity_type')
    def _onchange_quantity_type(self):
        if self.quantity_type == "percentage":
            self.quantity_pr = 100
        else:
            self.quantity_pr = 0

    @api.constrains('name', 'purchase_order_line_id')
    def _check_unique_name_per_line(self):
        for record in self:
            existing_line = self.search([
                ('name', '=', record.name),
                ('purchase_order_line_id', '=', record.purchase_order_line_id.id),
                ('id', '!=', record.id)
            ])
            if existing_line:
                raise ValidationError(f"La description '{record.name}' est déjà utilisé. Veuillez corriger la ligne concernée SVP.")

    @api.depends('quantity_pr', 'price_unit')
    def _compute_subtotal(self):
        for record in self:
            if record.quantity_type == "percentage":
                record.subtotal = record.price_unit
            else:
                record.subtotal = record.quantity_pr * record.price_unit

    @api.model
    def default_get(self, fields_list):
        res = super(PurchaseOrderLineDetail, self).default_get(fields_list)
        if self.env.context.get('default_purchase_order_line_id'):
            res['purchase_order_line_id'] = self.env.context.get('default_purchase_order_line_id')
        return res
    
    @api.constrains('quantity_pr')
    def _check_quantity_pr(self):
        for record in self:
            if record.quantity_pr <= 0:
                raise ValidationError(
                    f"La quantité doit être supérieure à 0 pour la ligne '{record.name}'. Veuillez corriger cette ligne SVP."
                )
    
    @api.constrains('price_unit')
    def _check_price_unit(self):
        for record in self:
            if record.price_unit <= 0:
                raise ValidationError(
                    f"Le prixe unitaire doit être supérieure à 0 pour la ligne '{record.name}'. Veuillez corriger cette ligne SVP."
                )
    