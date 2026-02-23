from odoo import fields, models
from datetime import datetime


class CpcWizard(models.TransientModel):
    _name = "cpc.wizard"


class ResultatWizard(models.TransientModel):
    _name = "resultat.wizard"

    from_date = fields.Date(string="Date de debut")
    to_date = fields.Date(string="Date de fin", required=True)
    state = fields.Selection([('all', 'Tous'), ('posted', '	Comptabilisé')], 'État', default='all')

    def print_dates(self):
        get = self.read()[0]

        if not get['from_date']:
            get['from_date'] = datetime.strptime(f"{get['to_date'].year}-1-1", "%Y-%m-%d").date()

        data = {
            'from_date': get['from_date'], 
            'to_date': get['to_date'],
            
            'from_f_date': get['from_date'].strftime('%d/%m/%Y'), 
            'to_f_date': get['to_date'].strftime('%d/%m/%Y'),

            'state': get['state'],
        }

        data['n1_to_date'] = datetime.strptime(f"{(get['to_date'].year - 1)}-12-31", "%Y-%m-%d").date()
        data['n1_to_f_date'] = data['n1_to_date'].strftime('%d/%m/%Y')

        return self.env.ref('accounting.report_resultat_wizard').report_action(self, data=data)