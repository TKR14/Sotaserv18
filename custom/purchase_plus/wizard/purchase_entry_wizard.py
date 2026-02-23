from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import ValidationError

    
class PurchaseEntryWizard(models.Model):
    _name = "purchase.entry.wizard"
    _description = 'Purchase Entry Wizard'

    purchase_id = fields.Many2one('purchase.order', string='Bon de Commande', required=True)
    supplier_id = fields.Many2one('res.partner', string='Fournisseur', required=True)
    site_id = fields.Many2one('building.site', string='Affaire', domain="[]", required=True)
    start_date = fields.Date(string='Date de début')
    end_date = fields.Date(string='Date de fin')
    number = fields.Char(string='Numéro', readonly=True)

    # def action_confirm(self):
    #     entry_lines = []

    #     count = self.env['purchase.entry'].search_count([
    #         ('purchase_id', '=', self.purchase_id.id)
    #     ]) + 1
    #     number = f"{self.purchase_id.name}-{str(count).zfill(4)}"

    #     new_entry = self.env['purchase.entry'].create({
    #         'purchase_id': self.purchase_id.id,
    #         'supplier_id': self.supplier_id.id,
    #         'site_id': self.site_id.id,
    #         'start_date': self.start_date,
    #         'end_date': self.end_date,
    #         'number': number
    #     })

    #     for line in self.purchase_id.order_line:
    #         line_details = self.env['purchase.order.line.detail'].search([
    #             ('purchase_order_line_id', '=', line.id),
    #         ])

    #         new_entry_line = self.env['purchase.entry.line'].create({
    #             'price_unit': line.price_unit,
    #             # 'product_qty': line.product_qty,
    #             'product_uom': line.product_uom.id,
    #             'name': line.product_id.name,
    #             'product_id': line.product_id.id,
    #             'entry_id': new_entry.id,
    #             'tax_ids': [(6, 0, line.taxes_id.ids)],
    #             'order_line_id': line.id,
    #         })
            
    #         for detail in line_details:
    #             self.env['purchase.entry.line.detail'].create({
    #                 'name': detail.name,
    #                 'unit_measurement': detail.unit_measurement.id,
    #                 'quantity_type': detail.quantity_type,
    #                 'quantity_pr': detail.quantity_pr,
    #                 'price_unit': detail.price_unit,
    #                 'detail_id': detail.id,
    #                 'tax_ids': detail.purchase_order_line_id[0].taxes_id,
    #                 'entry_line_id': new_entry_line.id
    #             })

    #         entry_lines.append(new_entry_line.id)

    #     new_entry.line_ids = [(6, 0, entry_lines)]

    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Attachement',
    #         'view_mode': 'form',
    #         'res_model': 'purchase.entry',
    #         'target': 'current',
    #         "res_id": new_entry.id,
    #         "views": [
    #             (self.env.ref("purchase_plus.purchase_entry_view_form").id, "form"),
    #         ],
    #     }

    def action_confirm(self):
        entry_lines = []

        count = self.env['purchase.entry'].search_count([
            ('purchase_id', '=', self.purchase_id.id)
        ]) + 1
        number = f"{self.purchase_id.name}-{str(count).zfill(4)}"

        new_entry = self.env['purchase.entry'].create({
            'purchase_id': self.purchase_id.id,
            'supplier_id': self.supplier_id.id,
            'site_id': self.site_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'number': number
        })

        for line in self.purchase_id.order_line:
            line_details = self.env['purchase.order.line.detail'].search([
                ('purchase_order_line_id', '=', line.id),
            ])

            new_entry_line = self.env['purchase.entry.line'].create({
                'price_unit': line.price_unit,
                'product_uom': line.product_uom.id,
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'entry_id': new_entry.id,
                'tax_ids': [(6, 0, line.taxes_id.ids)],
                'order_line_id': line.id,
            })

            for detail in line_details:
                previous_entries = self.env['purchase.entry'].search([
                    ('site_id', '=', self.site_id.id),
                    ('supplier_id', '=', self.supplier_id.id),
                    ('purchase_id', '=', self.purchase_id.id),
                    ('id', '<', new_entry.id)
                ], order='id desc', limit=1)

                cumulative_quantity = 0

                if previous_entries:
                    previous_lines = previous_entries.mapped('line_ids')
                    previous_details = previous_lines.mapped('detail_id').filtered(
                        lambda prev_detail: prev_detail.entry_line_id.order_line_id.id == line.id and prev_detail.name == detail.name 
                    )

                    if previous_details:
                        cumulative_quantity = sum(prev_detail.cumulative_quantity for prev_detail in previous_details)

                self.env['purchase.entry.line.detail'].create({
                    'name': detail.name,
                    'unit_measurement': detail.unit_measurement.id,
                    'quantity_type': detail.quantity_type,
                    'quantity_pr': detail.quantity_pr,
                    'price_unit': detail.price_unit,
                    'detail_id': detail.id,
                    'tax_ids': detail.purchase_order_line_id[0].taxes_id,
                    'entry_line_id': new_entry_line.id,
                    'cumulative_quantity': cumulative_quantity,
                })

            entry_lines.append(new_entry_line.id)

        new_entry.line_ids = [(6, 0, entry_lines)]
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attachement',
            'view_mode': 'form',
            'res_model': 'purchase.entry',
            'target': 'current',
            "res_id": new_entry.id,
            "views": [
                (self.env.ref("purchase_plus.purchase_entry_view_form").id, "form"),
            ],
        }


    @api.onchange('site_id')
    def _onchange_purchase_id(self):
        approved_sites = self.env['purchase.order'].search([
            ('state_2', '=', 'approved'),
            ('is_attachment', '=', True)
        ]).mapped('site_id')

        if approved_sites:
            return {
                'domain': {
                    'site_id': [('id', 'in', approved_sites.ids)]
                }
            }
        else:
            return {
                'domain': {
                    'site_id': []
                }
            }

    @api.onchange('site_id')
    def _onchange_site_id_update_suppliers(self):
        if self.site_id:
            related_suppliers = self.env['purchase.order'].search([
                ('state_2', '=', 'approved'),
                ('site_id', '=', self.site_id.id)
            ]).mapped('partner_id')

            return {
                'domain': {
                    'supplier_id': [('id', 'in', related_suppliers.ids)]
                }
            }
        else:
            return {
                'domain': {
                    'supplier_id': []
                }
            }

    @api.onchange('supplier_id', 'site_id')
    def _onchange_supplier_or_site_id(self):
        if self.supplier_id and self.site_id:
            not_yet_attachments = self.env["purchase.entry"].search([("is_invoiced", "!=", True)]).mapped("purchase_id")
            related_purchase_orders = self.env['purchase.order'].search([
                ('id', 'not in', not_yet_attachments.ids),
                ('partner_id', '=', self.supplier_id.id),
                ('state', '!=', 'po_canceled'),
                ('state_2', '=', 'approved'),
                ('is_done', '!=', True),
                ('site_id', '=', self.site_id.id)
            ])
            return {
                'domain': {
                    'purchase_id': [('id', 'in', related_purchase_orders.ids)]
                }
            }
        else:
            return {
                'domain': {
                    'purchase_id': []
                }
            }
        
    @api.constrains('start_date', 'end_date')
    def _check_start_date_after_end_date(self):
        for record in self:
            if record.start_date >= record.end_date:
                raise ValidationError(_("La date de début d'attachement doit être postérieure à la date de fin d'attachement."))
            
            if record.purchase_id.date_approve:
                date_approve = fields.Date.from_string(record.purchase_id.date_approve)
                if record.start_date < date_approve:
                    raise ValidationError(_("La date de début d'attachement doit être postérieure à la date du bon de commande."))

            
            last_entry = self.env['purchase.entry'].search([('site_id', '=', record.site_id.id),('is_invoiced', '=', True),('purchase_id', '=', record.purchase_id.id)], order='id desc', limit=1)
            if last_entry and last_entry.end_date:
                if record.start_date <= last_entry.end_date:
                    last_date_formatted = last_entry.end_date.strftime('%d-%m-%Y')
                    raise ValidationError(_(
                        "La date de début d'attachement doit être postérieure à la date du dernier attachement ({last_date})."
                    ).format(last_date=last_date_formatted))