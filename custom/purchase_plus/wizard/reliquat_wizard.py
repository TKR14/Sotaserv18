from odoo import fields, models, api
from odoo.exceptions import UserError

class ReliquatWizard(models.TransientModel):
    _name = 'reliquat.wizard'
    _description = 'Reliquat Message Wizard'

    message = fields.Text(string="Message")

    def action_confirm(self):
        active_id = self.env.context.get('active_id')
        if not active_id:
            raise UserError("L'ID actif n'est pas disponible dans le contexte.")

        purchase_entry = self.env['purchase.entry'].browse(active_id)

        if not purchase_entry.is_remaining_advance and not purchase_entry.avance:
            raise UserError("Veuillez saisir le montant de l'avance ou cocher le reliquat avant de confirmer.")

        purchase_entry.state_decompte = "provider_validated"
        purchase_entry.state_decompte_not_done = "provider_validated"

        move_type = self.env['account.move.type'].search([('name', '=', 'Décompte')], limit=1)
  
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': purchase_entry.supplier_id.id,
            'invoice_origin': purchase_entry.purchase_id.name,
            'site_id': purchase_entry.site_id.id,
            'is_attachment': True,
            'ref': purchase_entry.number,
            'avance': purchase_entry.avance,
            'penalty': purchase_entry.penalty,
            'return_of_guarantee': purchase_entry.return_of_guarantee,
            'invoice_type': 'standard',
            'move_type_id': move_type.id if move_type else False,
            'invoice_line_ids': [],
        }

        for line in purchase_entry.line_ids:
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': 1,
                'price_unit': line.amount_ht_invoiced - purchase_entry.penalty,
                'tax_ids': line.tax_ids,
                'account_id': self.env['account.account'].search([('code', '=', '6058000')], limit=1).id,
                'exclude_from_invoice_tab': False,
                'credit': 0,
            }))


        invoice = self.env['account.move'].create(invoice_vals)

        purchase_entry.is_invoiced = True

        purchase_entry.account_move_id = invoice.id

        invoice.write({
            'name': purchase_entry.number,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'target': 'current',
        }

