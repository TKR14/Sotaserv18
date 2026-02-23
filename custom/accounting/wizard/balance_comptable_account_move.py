from odoo import fields, models
from datetime import datetime
import re


class AccountMove(models.Model):
    _inherit = 'account.move'

    def get_comptes_comptables(self, to_date):
        docs = self.env['account.move'].search([])    

        to_date = datetime.strptime(to_date, f"%d/%m/%Y").date()
        from_date = datetime.strptime(f"01/01/{to_date.year}", f"%d/%m/%Y").date()

        n1_from_date = datetime.strptime(f"01/01/{to_date.year - 1}", f"%d/%m/%Y").date()
        n1_to_date = datetime.strptime(f"31/12/{to_date.year - 1}", f"%d/%m/%Y").date()

        # debiteur = [2, 3, 5, 6] # d - c
        crediteur = [1, 4, 7, 28, 29, 39, 55] # c - d

        lines = []

        total_o_debit_bilan = 0
        total_o_credit_bilan = 0
        total_o_debit_gestion = 0
        total_o_credit_gestion = 0

        total_m_debit_bilan = 0
        total_m_credit_bilan = 0
        total_m_debit_gestion = 0
        total_m_credit_gestion = 0

        for o in docs:
            if o.date >= from_date and o.date <= to_date:
                for line in o.line_ids:

                    for i in range(6, 10):
                        if re.search(f'^{i}', str(line.account_id.code)):
                            total_m_debit_gestion += line.debit
                            total_m_credit_gestion += line.credit
                                
                    for i in range(1, 6):
                        if re.search(f'^{i}', str(line.account_id.code)):
                            total_m_debit_bilan += line.debit
                            total_m_credit_bilan += line.credit

                    # Check if line already in lines
                    skip = 0
                    for l in lines:
                        if l['compte'] == line.account_id.code:
                            l['m_debit'] += line.debit
                            l['m_credit'] += line.credit
                            skip = 1
                    if skip == 0:
                        soldes = 1
                        for r in crediteur:
                            if re.search(f'^{r}', str(line.account_id.code)):
                                soldes = 0

                        if line.debit != 0 or line.credit != 0:
                            l = {
                                'compte': line.account_id.code,
                                'intitule': line.account_id.name,
                                'o_debit': 0,
                                'o_credit': 0,
                                'm_debit': line.debit,
                                'm_credit': line.credit,
                                'soldes': soldes,
                            }
                            lines.append(l)

            elif o.date >= n1_from_date and o.date <= n1_to_date:
                for line in o.line_ids:
                    for i in range(1, 6):
                        if re.search(f'^{i}', str(line.account_id.code)):
                            total_o_debit_bilan += line.debit
                            total_o_credit_bilan += line.credit

                            skip = 0
                            for l in lines:
                                if l['compte'] == line.account_id.code:
                                    l['o_debit'] += line.debit
                                    l['o_credit'] += line.credit
                                    skip = 1
                            if skip == 0:
                                soldes = 1
                                for r in crediteur:
                                    if re.search(f'^{r}', str(line.account_id.code)):
                                        soldes = 0

                                if line.debit != 0 or line.credit != 0:
                                    l = {
                                        'compte': line.account_id.code,
                                        'intitule': line.account_id.name,
                                        'o_debit': line.debit,
                                        'o_credit': line.credit,
                                        'm_debit': 0,
                                        'm_credit': 0,
                                        'soldes': soldes,
                                    }
                                    lines.append(l)

        totals = [total_o_debit_bilan, total_o_credit_bilan, total_m_debit_bilan, total_m_credit_bilan,
                  total_o_debit_gestion, total_o_credit_gestion, total_m_debit_gestion, total_m_credit_gestion]
        
        return [sorted(lines, key=lambda d: d['compte']), totals]
