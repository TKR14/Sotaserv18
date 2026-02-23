from odoo import models


class PayslipEdiXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_ma.report_payslip_ecnps_excel'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, employees):
        sheet = workbook.add_worksheet(employees.name)
        ths = ['N° C.N.P.S', ' NOM', 'PRENOMS', 'ANNEE DE NAISSANCE ', 'Date d embauche', 'Date de départ','H/M', 'MOIS', 'SALAIRE BRUT',
               ]
            
        right_align_format = workbook.add_format({'align': 'right'})
        left_align_format = workbook.add_format({'align': 'left'})
        center_align_format = workbook.add_format({'align': 'center'})
    
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#c8eb87',  
            'font_color': 'black',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1  
        })

        for i, header in enumerate(ths):
            sheet.write(0, i, header, header_format)

        sheet.freeze_panes(1, 0)

        marital_translation = {
            "single": "Célibataire",
            "married": "Marié(e)",
            "widower": "Veuf/Veuve",
            "divorced": "Divorcé(e)"
        }

        gender_translation = {
            "male": "H",
            "female": "F",
        }

        sorted_slips = sorted(employees.slip_ids, key=lambda e: e.employee_id.registration_number or '')

        row = 1
        name_col_width = 0
        for e in sorted_slips:
            sheet.write(row, 0, e.employee_id.ssnid or '')
            sheet.write(row, 1, e.employee_id.last_name or '')
            sheet.write(row, 2, e.employee_id.first_name or '')
            if len(e.employee_id.first_name) > name_col_width:
                name_col_width = len(e.employee_id.first_name)
                sheet.set_column(2, 2, name_col_width)
            date_center_format = workbook.add_format({'num_format': 'dd/mm/yyyy', 'align': 'center'})
            sheet.write(row, 3, e.employee_id.birthday or '', date_center_format)
            sheet.write(row, 4, e.contract_id.date_start or '', date_center_format)
            sheet.write(row, 5, e.contract_id.date_end if e.contract_id.date_end else '', date_center_format or '')
            # translated_gender = gender_translation.get(e.employee_id.gender, "Non spécifié")
            # sheet.write(row, 6, translated_gender)
            sheet.write(row, 6, e.contract_id.wage_type or '', center_align_format)
            # sheet.write(row, 7, str(e.date_from.month), center_align_format)
            sheet.write(row, 7, "1", center_align_format)
            # sheet.write(row, 8, "{:,.0f}".format(e.contract_id.salaire_c).replace(',', ' '))
            
            salaire_brut_amount = 0 
            for line in e.line_ids:
                if line.code == "BRUT_TOT":
                    salaire_brut_amount = line.amount
                    break

            sheet.write(row, 8,  "{:,.0f}".format(salaire_brut_amount).replace(',', ' '), right_align_format)

            row += 1

