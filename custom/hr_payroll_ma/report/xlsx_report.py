from odoo import models

class PayslipXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_ma.report_payslip_excel'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, employees):
        sheet = workbook.add_worksheet(employees.name)
        ths = ['NOMS ET PRENOMS', 'DATE DE NAISSANCE', 'LIEU DE NAISSANCE', 'FONCTION', 'QUALIFICATION', 'MATRICULE', 'N° CNPS','DATE D EMBAUCHE', 'TAUX ANCIENNETE', 'SITUATION FAMILIALE', 'NBRE D ENFANT', 'NB Part', 'SALAIRE DE BASE', 'SURSALAIRE', 'CONGE STC', 'GRATIFICATION', 'Indemnité de licenciement','Indemnité de fin contrat','PREAVIS', 'RAPPEL', 'AUTRES PRIMES ET AVANTAGES', 'ANCIENNETE', 'BRUT IMPOSABLE',
               'ITS Tranche 1 (0%°)j','ITS Tranche 2 (16%)','ITS Tranche 3 (21%)','ITS Tranche 4 (24%)','ITS Tranche 5 (28%)','ITS Tranche  6 (32%)','ITS','RICF','TOTAL RETENUE FISCALE SALARIALES','CNPS (C R)','CMU','TOTAL RETENUES','AVANCES & ACOMPTES','IND. NON IMPOSABLES','NET A PAYER','FDFP (FPC)',
               'TAXE D APPRENT','ITS','TOTAL CHARGES FISCALES PATRONALES','CAISSE DE RETRAITE','PRESTATION FAMILIALE','ASSURANCE MATERNITE','ACCIDENT DE TRAVAIL','CMU','TOTAL CHARGES SOCIALES PATRONALES ', 'TOTAL CHARGES FISCALES SOCIALES PATRONALES',
               ]
            
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#87CEEB',  
            'font_color': 'black',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1  
        })

        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#fefefe',  
            'font_color': 'black',
            'align': 'center',
            'border': 1
        })

        for i, header in enumerate(ths):
            sheet.write(0, i, header, header_format)

        sheet.freeze_panes(1, 0)

        codes_to_extract = [
            "ANC_MNT", "BRUT_TOT", "ITS1", "ITS2", "ITS3", "ITS4", "ITS5", "ITS6", "ITS", 
            "RICF", "TRFS", "CNPS_CR", "CMU", "RET_TOT", "AVANCE_ACOMPTE", 
            "IND_N_IMPOSABLE", "NET", "FDFP_FPC", "TAXE_APPRENT", "ITS_PAT",
            "TCF_PAT", "CAISSE_RETRAITE", "PREST_FAM", "ASS_MAT", "ACC_TRAV", 
            "CMU_PAT","TCS_PAT","TCFS_PAT"
        ]

        marital_translation = {
            "single": "Célibataire",
            "married": "Marié(e)",
            "widower": "Veuf/Veuve",
            "divorced": "Divorcé(e)"
        }

        sorted_slips = sorted(employees.slip_ids, key=lambda e: int(e.employee_id.registration_number) if e.employee_id.registration_number and e.employee_id.registration_number.isdigit() else float('inf'))

        row = 1
        name_col_width = 0
        for e in sorted_slips:
            sheet.write(row, 0, e.employee_id.name)
            if len(e.employee_id.name) > name_col_width:
                name_col_width = len(e.employee_id.name)
                sheet.set_column(0, 0, name_col_width)

            date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
            senrioty_taux = e.line_ids.filtered(lambda l:l.code == "ANC_TAUX").total
            nb_parts_amount = e.line_ids.filtered(lambda l:l.code == "NB_PARTS").total
            salaire_c = e.line_ids.filtered(lambda l:l.code == "SALAIRE_C").total
            sal_base = e.line_ids.filtered(lambda l:l.code == "SAL_BASE").total
            s_salaire = e.line_ids.filtered(lambda l:l.code == "S_SALAIRE").total
            a_p_imposable = e.line_ids.filtered(lambda l:l.code == "A_P_IMPOSABLE").total
            conge = e.line_ids.filtered(lambda l:l.code == "STC").total
            gratification = e.line_ids.filtered(lambda l:l.code == "GRATIF").total
            ind_licenciement = e.line_ids.filtered(lambda l:l.code == "LICENCE").total
            ind_fin_contrat = e.line_ids.filtered(lambda l:l.code == "FIN_CONTRAT").total
            preavis = e.line_ids.filtered(lambda l:l.code == "PREAVIS").total
            rappel = e.line_ids.filtered(lambda l:l.code == "RAPPEL").total


            translated_marital = marital_translation.get(e.employee_id.marital, "Non spécifié")

            sheet.write(row, 1, e.employee_id.birthday, date_format)
            sheet.write(row, 2, e.employee_id.place_of_birth)
            sheet.write(row, 3, e.employee_id.job_id.name)
            sheet.write(row, 4, e.employee_id.job_title)
            sheet.write(row, 5, e.employee_id.registration_number)
            sheet.write(row, 6, e.employee_id.ssnid if e.employee_id.ssnid else '')
            sheet.write(row, 7, e.contract_id.date_start, date_format)
            sheet.write(row, 8, senrioty_taux, workbook.add_format({'num_format': '0%'}))
            sheet.write(row, 9, translated_marital)
            sheet.write(row, 10, e.employee_id.children)                
            sheet.write(row, 11, nb_parts_amount)
            sheet.write(row, 12, salaire_c)
            sheet.write(row, 13, s_salaire)
            sheet.write(row, 14, conge)
            sheet.write(row, 15, gratification)
            sheet.write(row, 16, ind_licenciement)
            sheet.write(row, 17, ind_fin_contrat)
            sheet.write(row, 18, preavis)
            sheet.write(row, 19, rappel)
            sheet.write(row, 20, a_p_imposable)


            for col_index, code in enumerate(codes_to_extract, start=21):
                amount = next((line.amount for line in e.line_ids if line.code == code), 0)
                sheet.write(row, col_index, amount)

            row += 1

        # Ligne "TOTAL"
        total_row = row
        sheet.write(total_row, 0, "TOTAL", total_format)

        def get_column_letter(index):
            letters = ''
            while index >= 0:
                letters = chr(index % 26 + 65) + letters
                index = index // 26 - 1
            return letters

        for col_index in range(10, len(ths)):
            col_letter = get_column_letter(col_index) 
            formula = f"=SUM({col_letter}2:{col_letter}{row})"  
            sheet.write_formula(total_row, col_index, formula, total_format)
