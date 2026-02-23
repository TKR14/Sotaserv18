from odoo import models, fields, api
from lxml import etree


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    category_type = fields.Selection(related='categ_id.category_type', string='Type de Catégorie', store=True, readonly=True)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if self.env.context.get('is_logistic_product_template'):
            if 'toolbar' in res:
                res['toolbar']['action'] = []
                res['toolbar']['print'] = []

            if view_type == 'form' and 'arch' in res:
                doc = etree.XML(res['arch'])
                for button in doc.xpath("//button[@name='copy'] | //button[@name='unlink'] | //button[@name='toggle_active']"):
                    button.getparent().remove(button)
                res['arch'] = etree.tostring(doc, encoding='unicode')

        return res

