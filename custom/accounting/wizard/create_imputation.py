# -*- coding: utf-8 -*-

from odoo import api, fields, models


class CreateImputationWizard(models.TransientModel):
    _name = "create.imputation.wizard"
    _description = "Create Imputation Wizard"

    date_from = fields.Date(string='Date de début')
    date_to = fields.Date(string='Date de fin')

    def print_imputation(self):
        data = {
            'form': self.read()[0],
        }
        return self.env.ref('accounting.action_report_jr_imputation').report_action(self, data=data)
