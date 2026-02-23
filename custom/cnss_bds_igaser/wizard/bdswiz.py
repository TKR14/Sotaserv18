from odoo import api, fields, models
from datetime import datetime
from dateutil.relativedelta import relativedelta

import base64
from datetime import timedelta


class BdsWizard(models.TransientModel):
    _name = "bds.wizard"

    annee = fields.Integer(string="Année",size=4, required=True)
    mois = fields.Integer(string="Mois",size=2, required=True)
    id_trans = fields.Char(string='ID Transfert CNSS', required=True)
    sent_date = fields.Date(string="Date de l’émission", required=True)

    def print_data(self):
        # data = {'form': self.read()}

        # if data['form']['from_date'] == False:
        #     data['form']['from_date'] = datetime.strptime(f"{datetime.today().year}-1-1", "%Y-%m-%d").date()
            # self.env['cnss.bds'].action_genere_bds()
        get = self.read()[0]

        data = {
            'annee': get['annee'], 
            'mois': get['mois'],
            'id_trans': get['id_trans'],
            'sent_date': get['sent_date'],
            
            # 'from_f_date': get['from_date'].strftime('%d/%m/%Y'), 
            # 'to_f_date': get['to_date'].strftime('%d/%m/%Y'),
        }
           
        return self.env['cnss.bds'].action_genere_bdsV1(data=data)
        # return self.env.ref('accounting.report_esg_wizard').report_action(self, data=data)