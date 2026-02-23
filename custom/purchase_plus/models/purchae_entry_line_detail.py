from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PurchaseEntryLineDetail(models.Model):
    _name = 'purchase.entry.line.detail'

    name = fields.Char(string='Description')
    unit_measurement = fields.Many2one('uom.uom', string='UDM')
    quantity_type = fields.Selection([
        ("quantity", "Q"),
        ("percentage", "%"),
    ], default="percentage", string="Quantité")
    quantity_pr = fields.Float(string='Quantité')
    price_unit = fields.Float(string='Prix ​​unitaire')
    detail_id = fields.Many2one('purchase.order.line.detail', 'entry_line_id')
    cumulative_quantity = fields.Float(string='Cumul Actuel')

    quantity_president = fields.Float(string="Cumul Précédent", compute="_compute_quantity_president")

    cumulative_quantity_invoiced = fields.Float(string="Quantité", compute="_compute_cumulative_quantity_invoiced")

    product_id = fields.Many2one('product.product', string='Article')
    tax_ids = fields.Many2many('account.tax', string='Taxes')

    entry_line_id = fields.Many2one(
        'purchase.entry.line',
        string='Purchase Entry Line',
        ondelete='cascade'
    )

    is_quantity_exceeded = fields.Boolean(string="Dépassement quantité", compute="_compute_is_quantity_exceeded")

    is_validated = fields.Boolean(string="Is Validated", default=False)

    cumulative_amount_ht = fields.Float(string='Montant cumulée', compute="_comput_cumulative_amount")
    amount_ht_invoiced = fields.Float(string='Montant cumulée', compute="_comput_amount_ht_invoiced")

    @api.depends('cumulative_quantity', 'quantity_president')
    def _compute_cumulative_quantity_invoiced(self):
        for record in self:
            record.cumulative_quantity_invoiced = record.cumulative_quantity - record.quantity_president
            
    # @api.onchange('cumulative_quantity')
    # def _update_entry_done_status(self):
    #     if self.entry_line_id and self.env.context.get('attachment_view'):
    #         entry = self.entry_line_id.entry_id

    #         total_quantity_pr = 0.0
    #         total_cumulative_quantity = 0.0

    #         for line in self:
    #             total_quantity_pr += line.quantity_pr
    #             total_cumulative_quantity += line.cumulative_quantity

    #         if (total_cumulative_quantity - total_quantity_pr) == 0:
    #             entry.is_done = True
    #             entry.is_automatically_done = True
    #         else:
    #             entry.is_done = False
    #             entry.is_automatically_done = False

    @api.depends('quantity_president', 'quantity_pr')
    def _compute_is_quantity_exceeded(self):
        for detail in self:
            if detail.quantity_pr == detail.quantity_president:
                detail.is_quantity_exceeded = True
                detail.cumulative_quantity = detail.quantity_president
            else:
                detail.is_quantity_exceeded = False

    # @api.onchange('cumulative_quantity')
    # def _update_entry_done_status(self):
    #     # self.entry_line_id.entry_id.check_done()
    #     if self.entry_line_id and self.env.context.get('attachment_view'):
    #         entry = self.entry_line_id.entry_id

    #         total_quantity_pr = 0.0
    #         total_cumulative_quantity = 0.0
    #         total_quantity_president = 0.0

    #         for line in entry.line_ids:
    #             for detail in line.detail_id:
    #                 total_quantity_pr += detail.quantity_pr
    #                 total_cumulative_quantity += detail.cumulative_quantity
    #                 total_quantity_president += detail.quantity_president

    #         # self.total_quantity_pr, self

    #         # raise Exception(total_cumulative_quantity + total_quantity_president)
    #         if (total_cumulative_quantity + total_quantity_president) == total_quantity_pr:
    #             # entry.is_done = True
    #             # entry.is_automatically_done = True
    #             query = """UPDATE TABLE purchase_entry SET is_done = true;"""
    #             cr = self._cr
    #             cr.execute(query)
    #             # entry.sudo().write({
    #             #     "is_done": True
    #             # })
    #         else:
    #             entry.is_done = False
    #             entry.is_automatically_done = False

    @api.depends('entry_line_id')
    def _compute_quantity_president(self):
        for record in self:
            previous_quantity = 0.0

            if record.entry_line_id and record.entry_line_id.entry_id:
                previous_entries = self.env['purchase.entry'].search([
                    ('site_id', '=', record.entry_line_id.entry_id.site_id.id),
                    ('supplier_id', '=', record.entry_line_id.entry_id.supplier_id.id),
                    ('purchase_id', '=', record.entry_line_id.entry_id.purchase_id.id),
                    ('id', '<', record.entry_line_id.entry_id.id)
                ], order='id desc', limit=1)

                if previous_entries:
                    entry_lines = previous_entries.mapped('line_ids')

                    if entry_lines:
                        previous_details = entry_lines.mapped('detail_id').filtered(
                            lambda detail: detail.name == record.name and detail.entry_line_id.order_line_id.id == record.entry_line_id.order_line_id.id
                        )

                        if previous_details:
                            previous_quantity = previous_details.cumulative_quantity

            record.quantity_president = previous_quantity
    
    @api.depends('cumulative_quantity', 'price_unit')
    def _comput_cumulative_amount(self):
        for record in self:
            if record.quantity_type == "quantity":
                record.cumulative_amount_ht = record.cumulative_quantity * record.price_unit
            else:
                record.cumulative_amount_ht = (record.cumulative_quantity / 100) * record.price_unit
            

    @api.depends('cumulative_quantity_invoiced', 'price_unit')
    def _comput_amount_ht_invoiced(self):
        for record in self:
            if record.quantity_type == "quantity":
                record.amount_ht_invoiced = record.cumulative_quantity_invoiced * record.price_unit
            else:
                record.amount_ht_invoiced = (record.cumulative_quantity_invoiced / 100) * record.price_unit

    @api.constrains('cumulative_quantity')
    def _check_cumulative_quantity(self):
        for record in self:
            if record.cumulative_quantity < record.quantity_president:
                raise ValidationError(
                    "La quantité cumulée dans la ligne '{}' ne peut être inférieure à la quantité des Attachements précédents.".format(record.name)
                )

            if record.cumulative_quantity > record.quantity_pr:
                raise ValidationError(
                    "La quantité cumulée dans la ligne '{}' ne peut pas dépasser la quantité indiquée dans le détail de la ligne de Bon de commande '{}'. La quantité indiquée dans le détail de la ligne est de {}.".format(record.name, record.name, record.quantity_pr)
                )

            # if (record.cumulative_quantity + record.quantity_president) > record.quantity_pr:
            #     difference = (record.cumulative_quantity + record.quantity_president) - record.quantity_pr
            #     raise ValidationError(
            #         "La quantité cumulée pour la ligne '{}' dépasse la quantité autorisée dans le Bon de commande ({}). La différence est de {}.".format(
            #             record.name, 
            #             record.quantity_pr, 
            #             difference
            #         )
            #     )