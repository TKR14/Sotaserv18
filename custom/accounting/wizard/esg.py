from odoo import api, fields, models
from datetime import datetime
from dateutil.relativedelta import relativedelta


class EsgWizard(models.TransientModel):
    _name = "esg.wizard"

    from_date = fields.Date(string="Date de debut")
    to_date = fields.Date(string="Date de fin", required=True)
    entries = fields.Selection(string='Entrées', selection=[('all', 'Tous'), ('posted', 'Confirmé')], default='all')

    def print_data(self):
        data = {'form': self.read()[0]}

        if data['form']['from_date'] == False:
            data['form']['from_date'] = datetime.strptime(f"{datetime.today().year}-1-1", "%Y-%m-%d").date()

        return self.env.ref('accounting.report_esg_wizard').report_action(self, data=data)

