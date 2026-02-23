from odoo import _, fields, models, api
from odoo.exceptions import UserError


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    balance_end_real = fields.Monetary(string='Solde final', compute='_compute_balance_end_real', store=True, readonly=True)

    @api.depends('balance_end')
    def _compute_balance_end_real(self):
        for rec in self:
            rec.balance_end_real = rec.balance_end