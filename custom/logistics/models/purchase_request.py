from odoo import models, fields, api


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        if self.env.context.get('is_logistic'):
            logistic_site = self.env['building.site'].search([('number', '=', '002')], limit=1)
            if logistic_site:
                res['site_id'] = logistic_site.id

        return res
    

class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        ctx = self.env.context
        # if ctx.get('is_logistic'):
        #     if 'category_type' in res:
        #         res['category_type']['selection'] = [
        #             (value, label)
        #             for value, label in res['category_type']['selection']
        #             if value != 'other'
        #         ]
        return res
    
    # @api.onchange('category_type')
    # def _onchange_category_type_logistic(self):
    #     for line in self:
    #         if self.env.context.get('is_logistic'):
    #             if line.category_type == 'other':
    #                 line.category_type = False

    #         domain = []
    #         if line.category_type:
    #             request = line.request_id
    #             used_products = request.line_ids.filtered(lambda l: l.id != line.id).mapped('product_id').ids
    #             domain = [
    #                 ('categ_id.category_type', '=', line.category_type),
    #                 ('id', 'not in', used_products)
    #             ]

    #         return {'domain': {'product_id': domain}}

