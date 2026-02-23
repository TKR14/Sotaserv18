from odoo import models

class PayslipEdiXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_ma.report_payslip_etat301_excel'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, employees):
        sheet = workbook.add_worksheet(employees.name)
        ths = ['MATRICULE', ' NOM', 'PRENOMS', 'FONCTION/EMPLOI', 'REGIME GENERAL G OU AGRICOLE A', 'SEXE', 'NATIONNALITE', 'E/LOCAL', 'SITUATION MATRIMONIALE',
               'NOMBRE D ENFANTS', 'NOMBRE DE PARTS', ' N° C.N.P.S', 'ANNEE DE NAISSANCE ', 'Date d embauche', 'Date de départ', 'H/M', 'SALAIRE BRUT', 'MOIS',
               'AVANTAGE EN NATURE', 'BRUT IMPOSABLE', 'ITS', 'B NON IMPOSABLE', '#', 'SAL RET', 'BRUTS', 'TRANSP NON IMPOSABLE', 'TRANSPORT IMPOSABLE',
               ]
            
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#87ebe3',  
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
            "male": "Homme",
            "female": "Femme",
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
            sheet.write(row, 3, e.employee_id.job_title)
            sheet.write(row, 4, "#")
            translated_gender = gender_translation.get(e.employee_id.gender, "Non spécifié")
            sheet.write(row, 5, translated_gender)
            sheet.write(row, 6, e.employee_id.country_id.name if e.employee_id.country_id else "")
            sheet.write(row, 7, e.employee_id.place_of_birth)
            translated_marital = marital_translation.get(e.employee_id.marital, "Non spécifié")
            sheet.write(row, 8, translated_marital)
            sheet.write(row, 9, e.employee_id.children)
            nb_parts_amount = 0 
            for line in e.line_ids:
                if line.code == "NB_PARTS":
                    nb_parts_amount = line.amount
                    break
            sheet.write(row, 10, nb_parts_amount)
            sheet.write(row, 11, e.employee_id.ssnid)
            date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
            sheet.write(row, 12, e.employee_id.birthday, date_format)
            sheet.write(row, 13, e.employee_id.recruitment_date, date_format)
            sheet.write(row, 14, e.contract_id.date_start, date_format)
            sheet.write(row, 15, translated_gender)
            sheet.write(row, 16, e.contract_id.salaire_c)
            sheet.write(row, 17, "#")
            sheet.write(row, 18, "#")
            sheet.write(row, 19, "#")
            its_amount = 0 
            for line in e.line_ids:
                if line.code == "ITS":
                    its_amount = line.amount
                    break
            sheet.write(row, 20, nb_parts_amount)
            sheet.write(row, 21, "#")
            sheet.write(row, 22, "#")
            sheet.write(row, 23, "#")
            sheet.write(row, 24, "#")
            sheet.write(row, 25, e.contract_id.travel_allowance)
            sheet.write(row, 26, "#")

            row += 1
