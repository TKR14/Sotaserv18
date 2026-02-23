from odoo import fields, models, api
from datetime import datetime
import calendar


class BalanceComptable(models.TransientModel):
    _name = "balance.comptable"

    to_date = fields.Date("Au", required=True)

    def get_month(self):
        edit_date = datetime.strftime(datetime.today().date(), "%d/%m/%Y")

        to_date = f"{self.to_date.day:02d}/{self.to_date.month:02d}/{self.to_date.year}"
        
        data = {'edit_date': edit_date,
                'to_date': to_date,
                }

        return self.env.ref('accounting.balance_comptable_report').report_action(self, data=data)
