from odoo import models


class hr_payslip(models.Model):
    _inherit = 'hr.payslip'

    # def calc_rubrique_total(self, year, employee, rub_code):
    #     paysilps = self.search([('date_to', 'like', year), ('contract_id.name', '=', employee.contract_id.name)])

    #     if len(rub_code) != 0:
    #         totals = []
    #         for rub in rub_code:
    #             totals += [line.total for payslip in paysilps for line in payslip.line_ids if line.code == rub]
            
    #         return sum(totals)
            
    #     else:
    #         return 0

    def get_employees(self, year):
        payslips = self.search([('date_to', 'like', year)])
        employees = list(set([payslip.employee_id for payslip in payslips]))
        return employees

    def calc_rubrique_total(self, year, employee, rub_code):
        payslip = self.search([('date_to', 'like', year), ('employee_id', '=', employee.id)])
        v_tot_amt = 0
        
        for ps in payslip:
             
            for rb in rub_code:
                if rb == 'WDAYS':
                    for l in ps.worked_days_line_ids:
                            if l.code == 'WORK100':
                                if l.number_of_days > 26:
                                    v_tot_amt += 26
                                else:  
                                     v_tot_amt += l.number_of_days

                else:
                        for line in ps.line_ids:
                            if line.code == rb:
                                v_tot_amt += line.total

            
        return v_tot_amt
