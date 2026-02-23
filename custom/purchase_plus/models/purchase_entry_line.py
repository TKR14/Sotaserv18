from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PurchaseEntryLine(models.Model):
    _name = 'purchase.entry.line'
    _description = 'Purchase Entry Line'

    entry_id = fields.Many2one('purchase.entry', ondelete='cascade')
    name = fields.Char(string='Description')
    unit_measurement = fields.Many2one('uom.uom', string='UDM')
    # quantity_type = fields.Selection([
    #     ("quantity", "Q"),
    #     ("percentage", "%"),
    # ], default="percentage", string="Quantité")
    quantity_pr = fields.Float(string='Quantité')
    price_unit = fields.Float(string='Prix ​​unitaire')
    product_qty = fields.Float(string='Quantité', compute="_compute_product_qty")
    product_uom = fields.Many2one("uom.uom", "UDM")

    cumulative_quantity = fields.Float(string='Quantité cumulée')
    previous_counts_quantity = fields.Float(string='Quantité décomptes précédents', compute='_compute_previous_counts_quantity', store=True)
    current_count_quantity = fields.Float(string='Quantité décompte courant') #compute='_compute_current_count_quantity'

    product_id = fields.Many2one('product.product', string='Article')

    # detail_id = fields.Many2one('purchase.order.line.detail', 'entry_line_id')

    # price_unit = fields.Float(string='Prix Unitaire', digits='Product Price')
    tax_ids = fields.Many2many('account.tax', string="Taxes")
    # cumulative_amount = fields.Float(string='Montant cumulée', compute="_comput_cumulative_amount")
    cumulative_amount = fields.Float(string='Montant cumulée')
    Amount_to_be_invoiced = fields.Float(string='Montant à facturée', compute="_comput_amount_to_be_invoiced")

    detail_id = fields.One2many(
        'purchase.entry.line.detail',
        'entry_line_id',
        string='Line Details'
    )

    order_line_id = fields.Many2one('purchase.order.line', string='Purchase Order Line', ondelete='cascade')

    cumulative_ht = fields.Float(string='Cumulé (HT)', compute='_cumulative_ht')
    cumulative_tva = fields.Float(string='Cumulé (TVA)', compute='_cumulative_tva')
    cumulative_ttc = fields.Float(string='Cumulé (TTC)', compute='_compute_cumulative_ttc')

    amount_ht = fields.Float(string='Montant HT', compute="_compute_amount_ht", store=True)
    amount_ht_invoiced = fields.Float(string='Montant HT', compute='_compute_amount_ht_invoiced')

    amount_invoiced_tva = fields.Float(compute='_compute_amount_invoiced_tva')

    @api.depends('amount_ht_invoiced')
    def _compute_amount_invoiced_tva(self):
        for line in self:
            if line.detail_id and line.detail_id.tax_ids:
                tax_rate = line.detail_id.tax_ids.amount or 0.0
                line.amount_invoiced_tva = (line.amount_ht_invoiced * tax_rate) / 100
            else:
                line.amount_invoiced_tva = 0.0


    @api.depends('amount_ht_invoiced', 'price_unit')           
    def _compute_product_qty(self):
        for line in self:
            if line.price_unit != 0:
                line.product_qty = line.amount_ht_invoiced / line.price_unit
            else:
                line.product_qty = 0 

    @api.depends('detail_id')           
    def _compute_amount_ht(self):
        for line in self:
            if line.detail_id:
                line.amount_ht = sum(detail.cumulative_amount_ht for detail in line.detail_id)
            else:
                line.amount_ht = 0.0

    @api.depends('order_line_id')
    def _compute_ordered_ht(self):
        for line in self:
            if line.order_line_id:
                line.ordered_ht = line.order_line_id.price_subtotal
            else:
                line.ordered_ht = 0.0

    @api.depends('order_line_id')
    def _compute_amount_ht_invoiced(self):
        for line in self:
            if line.detail_id:
                line.amount_ht_invoiced = sum(detail.amount_ht_invoiced for detail in line.detail_id)
            else:
                line.amount_ht_invoiced = 0.0

    @api.depends('cumulative_ht', 'cumulative_tva')
    def _compute_cumulative_ttc(self):
        for line in self:
            line.cumulative_ttc = line.cumulative_ht + line.cumulative_tva

    @api.depends('detail_id')
    def _cumulative_ht(self):
        for line in self:
            if line.detail_id:
                line.cumulative_ht = sum(detail.cumulative_amount_ht for detail in line.detail_id)
            else:
                line.cumulative_ht = 0.0

    @api.depends('detail_id')
    def _cumulative_tva(self):
        for line in self:
            if line.detail_id:
                line.cumulative_tva = sum(((detail.cumulative_amount_ht) * detail.tax_ids.amount ) / 100 for detail in line.detail_id)
            else:
                line.cumulative_tva = 0.0
           
    ordered_ht = fields.Float(string='Commandé (HT)', compute='_compute_ordered_ht')

    def show_detail(self): 
        return {
            'type': 'ir.actions.act_window',
            'name': 'Détails de la ligne de l\'attachement',
            'view_mode': 'form',
            'res_model': 'purchase.entry.line',
            'target': 'new',
            'context': {
                'create': False,
                'delete': False,
                'edit': False,
            },
            'domain': [('entry_line_id', '=', self.id)],
            "res_id": self.id,
            "views": [
                (self.env.ref("purchase_plus.view_purchase_entry_line_detail_form").id, "form"),
            ],
        }
    
    def show_detail_decompte(self): 
        return {
            'type': 'ir.actions.act_window',
            'name': 'Détail de la ligne de l\'attachement',
            'view_mode': 'form',
            'res_model': 'purchase.entry.line',
            'target': 'new',
            'context': {
                'create': False,
                'delete': False,
                'edit': False,
            },
            'domain': [('entry_line_id', '=', self.id)],
            "res_id": self.id,
            "views": [
                (self.env.ref("purchase_plus.view_purchase_entry_line_detail_decompte_form").id, "form"),
            ],
        }

    def show_to_be_invoiced_detail(self): 
        return {
            'type': 'ir.actions.act_window',
            'name': 'Détail À facturer',
            'view_mode': 'form',
            'res_model': 'purchase.entry.line',
            'target': 'new',
            'context': {
                'create': False,
                'delete': False,
                'edit': False,
            },
            'domain': [('entry_line_id', '=', self.id)],
            "res_id": self.id,
            "views": [
                (self.env.ref("purchase_plus.view_purchase_entry_line_detail_to_be_invoiced_detail_form").id, "form"),
            ],
        }
    
    # display_type = fields.Selection([
    # ('line_section', "Section"),
    # ('line_note', "Note")], default=False)

    # @api.depends('cumulative_quantity', 'price_unit')
    # def _comput_cumulative_amount(self):
    #     for record in self:
    #         if record.quantity_type == "quantity":
    #             record.cumulative_amount = record.cumulative_quantity * record.price_unit
    #         else:
    #             record.cumulative_amount = (record.cumulative_quantity / 100) * record.price_unit

    @api.depends('current_count_quantity', 'price_unit')
    def _comput_amount_to_be_invoiced(self):
        for record in self:
            record.Amount_to_be_invoiced = record.current_count_quantity * record.price_unit

    @api.depends('entry_id.site_id', 'entry_id.supplier_id', 'entry_id.purchase_id', 'product_id')
    def _compute_previous_counts_quantity(self):
        for record in self:
            previous_quantity = 0.0
            previous_cum_quantity = 0.0
            
            if record.entry_id:
                previous_entries = self.env['purchase.entry'].search([
                    ('site_id', '=', record.entry_id.site_id.id),
                    ('supplier_id', '=', record.entry_id.supplier_id.id),
                    ('purchase_id', '=', record.entry_id.purchase_id.id),
                    ('id', '<', record.entry_id._origin.id)
                ], order='id desc', limit=1)

                if previous_entries:
                    previous_entry_lines = previous_entries.mapped('line_ids').filtered(
                        lambda line: line.product_id == record.product_id and line.order_line_id == record.order_line_id
                    )

                    if previous_entry_lines:
                        previous_details = previous_entry_lines.mapped('detail_id').filtered(
                            lambda detail: detail.product_id == record.product_id and detail.entry_line_id == record.id
                        )

                        if previous_details:
                            previous_quantity = sum(detail.current_count_quantity for detail in previous_details)
                            previous_cum_quantity = sum(detail.cumulative_quantity for detail in previous_details)

            record.previous_counts_quantity = previous_quantity
            record.cumulative_quantity = previous_cum_quantity

    
    # @api.constrains('cumulative_quantity', 'detail_id')
    # def _check_cumulative_quantity(self):
    #     for record in self:
    #         if record.cumulative_quantity < record.previous_counts_quantity:
    #             raise ValidationError(
    #                 "La quantité cumulée dans la ligne '{}' ne peut être inférieure à la quantité Quantité décomptes précédents.".format(record.name)
    #             )
    #         for detail in record.detail_id:
    #             if record.cumulative_quantity > detail.quantity_pr:
    #                 raise ValidationError(
    #                     "La quantité cumulée dans la ligne '{}' ne peut pas dépasser la quantité indiquée dans le détail de la ligne de Bon de commande '{}'. La quantité indiquée dans le détail de la ligne est de {}.".format(record.name, detail.name, detail.quantity_pr)
    #                     )
    
    # comment hh2
    # @api.depends('cumulative_quantity', 'previous_counts_quantity')
    # def _compute_current_count_quantity(self):
    #     for record in self:
    #         prev_counts_quantities = 0.0
    #         previous_entries = self.env['purchase.entry'].search([
    #             ('site_id', '=', record.entry_id.site_id.id),
    #             ('supplier_id', '=', record.entry_id.supplier_id.id),
    #             ('purchase_id', '=', record.entry_id.purchase_id.id),
    #             ('id', '<', record.entry_id._origin.id)
    #         ])
    #         if previous_entries:
    #             previous_entry_lines = previous_entries.mapped('line_ids').filtered(lambda l: l.name == record.name and l.detail_id.id == record.detail_id.id)
    #             prev_counts_quantities = sum(previous_entry_lines.mapped("current_count_quantity"))
    #         record.current_count_quantity = record.cumulative_quantity - prev_counts_quantities

    def unlink(self):
        for record in self:
            dependent_records = self.env['purchase.order.line.detail'].search([('entry_line_id', '=', record.id)])
            if dependent_records:
                dependent_records.unlink()
        return super(PurchaseEntryLine, self).unlink()

    def action_archive(self):
        self.write({'active': False})