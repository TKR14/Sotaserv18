from odoo import fields, models, api


class PersonnelPermanenet(models.TransientModel):
    _name = "personnel.permanent"

    year = fields.Date("Année", required=True)

    def get_year(self):
        data = {'year': self.year.year}

        return self.env.ref('hr_payroll_ma.personnel_permanent_report').report_action(self, data=data)
