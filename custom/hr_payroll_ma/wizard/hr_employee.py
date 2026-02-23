from odoo import models

class hr_employee(models.Model):
    _inherit = 'hr.employee'

    def get_employees(self):
        employees = self.search([])

        return sorted(employees, key=lambda x: x.name)
