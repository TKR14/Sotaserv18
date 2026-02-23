from odoo import models

class PayslipEdiXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_ma.report_payslip_edisa_excel'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, employees):
        sheet = workbook.add_worksheet(employees.name)
        ths = ['MATRICULE', ' NOM', 'PRENOMS', ' N° C.N.P.S', 'ANNEE DE NAISSANCE ', 'Date d embauche', 'Date de départ','H/M', 'SALAIRE BRUT',
               'Gratification','cumul salaire brut annuel','MOIS', 'BASE AT/PF ANNUEL', 'SAL RET', 'salaire BRUTS plafonné', 'TRANSP NON IMPOSABLE', 'TRANSPORT IMPOSABLE',
               ]
            
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#ebb187',  
            'font_color': 'black',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1  
        })

        for i, header in enumerate(ths):
            sheet.write(0, i, header, header_format)

        sheet.freeze_panes(1, 0)

        marital_translation = {
            "single": "C",
            "married": "M",
            "widower": "V",
            "divorced": "D"
        }

        gender_translation = {
            "male": "H",
            "female": "F",
        }

        sorted_slips = sorted(employees.slip_ids, key=lambda e: e.employee_id.registration_number or '')

        row = 1
        name_col_width = 0
        for e in sorted_slips:
            sheet.write(row, 0, e.employee_id.registration_number)
            sheet.write(row, 1, e.employee_id.last_name)
            sheet.write(row, 2, e.employee_id.first_name)
            if len(e.employee_id.first_name) > name_col_width:
                name_col_width = len(e.employee_id.first_name)
                sheet.set_column(2, 2, name_col_width)
            sheet.write(row, 3, e.employee_id.ssnid)
            date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
            sheet.write(row, 4, e.employee_id.birthday, date_format)
            sheet.write(row, 5, e.employee_id.recruitment_date, date_format)
            sheet.write(row, 6, e.contract_id.date_start, date_format)
            # translated_gender = gender_translation.get(e.employee_id.gender, "Non spécifié")
            # sheet.write(row, 7, translated_gender)
            sheet.write(row, 7, e.contract_id.wage_type or '')
            # sheet.write(row, 8, "{:,.0f}".format(e.contract_id.salaire_c).replace(',', ' '))
            salaire_brut_amount = 0 
            for line in e.line_ids:
                if line.code == "BRUT_TOT":
                    salaire_brut_amount = line.amount
                    break

            sheet.write(row, 8,  "{:,.0f}".format(salaire_brut_amount).replace(',', ' '))
            sheet.write(row, 9, e.contract_id.salaire_c * 0.75 if e.contract_id.salaire_c else 0)
            sheet.write(row, 10, e.contract_id.salaire_c * 1.75 if e.contract_id.salaire_c else 0)
            # Récupérer l'année de la période en cours
            annee_courante = e.date_from.year  

            bulletins = self.env['hr.payslip'].search([
                ('employee_id', '=', e.employee_id.id),
                ('date_from', '>=', f'{annee_courante}-01-01'),
                ('date_from', '<=', f'{annee_courante}-12-31')
            ])

            mois_distincts = {b.date_from.month for b in bulletins}

            sheet.write(row, 11, len(mois_distincts))
            
            # sheet.write(row, 11, str(e.date_from.month)) 
            sheet.write(row, 12, "75 000")
            sheet.write(row, 13, "#")
            sheet.write(row, 14, "#")
            sheet.write(row, 15, e.contract_id.travel_allowance)
            sheet.write(row, 16, "#")

            row += 1

