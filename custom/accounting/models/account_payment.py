from odoo import models, fields, api
from datetime import datetime
import re


class account_payment(models.Model):
    _inherit = 'account.payment'


    def amount_in_word(self, amount):

        word_num = str(self.currency_id.amount_to_text(amount))
        return word_num

class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    @api.model
    def _get_payment_method_information(self):
        dict_payment = {}
        for method in self.search([]):
            dict_payment[method.code] = {'mode': 'multi', 'domain': [('type', 'in', ('bank', 'cash'))]}
        return dict_payment
