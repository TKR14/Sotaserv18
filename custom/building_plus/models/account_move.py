from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_get_site_user(self, readonly=False, nocreate=False):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
        ])

        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'create': False,
            'delete': False,
            'edit': False,
            'hide_actions':True, 
            'default_move_type': 'in_invoice',
            'group_by': ['payment_state']
        }

        domain = [
            ('site_id', 'in', site_ids),
            ('move_type', '=', 'in_invoice')
        ]


        return {
            'name': 'Factures fournisseurs',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'views': [
                (self.env.ref('account.view_in_invoice_tree').id, "tree"),
                (self.env.ref('building_plus.account_invoice_readonly_form_view').id, "form")
            ],
            'domain': domain,
            'context': context,
        }