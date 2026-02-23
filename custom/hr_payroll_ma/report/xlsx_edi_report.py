from odoo import models

class PayslipEdiXlsx(models.AbstractModel):
    _name = 'report.hr_payroll_ma.report_payslip_edi_excel'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, employees):
        sheet = workbook.add_worksheet(employees.name)

        ths = ['N°', ' N° C.N.P.S', 'NOM ET PRENOMS', 'Type de travailleur', 'Emploi ou Qualité', 'Code Emploi','Régime Général', 'Sexe', 'Nationalité', 'Local/Expatrié',
            'Etat civil', 'Nombre d\'enfants',  
            'Nombre de parts', 'Nombre de jours d\'application des paiements', 'Montant des salaires et rémunérations accessoires', 
            'Montant des avantages en nature suivant barème réglementaire', 'Montant des avantages en nature selon valeur réelle',
            'Rémuneration totale brute', 'Révenus non imposables', 'Rémuneration brute imposable', 
            'Réduction d\'impôt pour charges de famille(RICF)', 'Brut', 'Net', 'Ajustement', 'Net à payer', 'Montant', 'Désignation']

        sous_ths = ["", "", "", "", "", "", "", "", "", "",  
                    "Etat civil", "Nombre d'enfants à charge",  
                    "", "", "", "", "", "", "", "", "", "Brut", "Net", "Ajustement*", "Net à payer", "", ""]

        header_format = workbook.add_format({'bold': True, 'bg_color': '#b2eb87', 'font_color': 'black', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        title_format = workbook.add_format({'bold': True, 'bg_color': '#fbfce3', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True})

        sheet.merge_range(0, 10, 0, 11, "Situation de famille la plus favorable\n(au 1er janvier ou au 31 décembre)", title_format)
        sheet.merge_range(0, 21, 0, 24, "ITS Salariés", title_format)

        for col, header in enumerate(ths):
            if sous_ths[col] == "": 
                sheet.merge_range(0, col, 1, col, header, header_format)
            else: 
                sheet.write(0, col, header, header_format)

        for col, sub_header in enumerate(sous_ths):
            if sub_header: 
                sheet.write(1, col, sub_header, header_format)

        sheet.set_row(0, 30)  
        sheet.set_row(1, 20)  
        sheet.freeze_panes(2, 0)

        marital_translation = { "single": "C", "married": "M", "widower": "V", "divorced": "D"}
        gender_translation = {"male": "H", "female": "F",}
        right_align_format = workbook.add_format({'align': 'right'})
        left_align_format = workbook.add_format({'align': 'left'})
        center_align_format = workbook.add_format({'align': 'center'})

        sorted_slips = sorted(employees.slip_ids, key=lambda e: e.employee_id.registration_number or '')

        row = 2
        name_col_width = 0
        for index, e in enumerate(sorted_slips, start=1):
            sheet.write(row, 0, f"{index:02d}")
           
            sheet.write(row, 2, e.employee_id.name)
            if len(e.employee_id.name) > name_col_width:
                name_col_width = len(e.employee_id.name)
                sheet.set_column(2, 2, name_col_width)

            sheet.write(row, 1, e.employee_id.ssnid if e.employee_id.ssnid else '')
            sheet.write(row, 3, "Salarié")
            sheet.write(row, 4, e.employee_id.job_title)
            sheet.write(row, 5,"EQ", center_align_format)
            sheet.write(row, 6, "G", center_align_format)
            translated_gender = gender_translation.get(e.employee_id.gender, " ")
            sheet.write(row, 7, translated_gender, center_align_format)
            sheet.write(row, 8, e.employee_id.nationality_code if e.employee_id.nationality_code else '', center_align_format)
            sheet.write(row, 9, e.employee_id.category, center_align_format)
            translated_marital = marital_translation.get(e.employee_id.marital, " ")
            sheet.write(row, 10, translated_marital, center_align_format)
            sheet.write(row, 11, e.employee_id.children, center_align_format)
            nb_parts_amount = 0 
            for line in e.line_ids:
                if line.code == "NB_PARTS":
                    nb_parts_amount = line.amount
                    break
            sheet.write(row, 12, nb_parts_amount, center_align_format)

            paid_days_amount = 0 
            for line in e.line_ids:
                if line.code == "TOT_PAID_DAYS":
                    paid_days_amount = line.amount
                    break
            sheet.write(row, 13, paid_days_amount, center_align_format)

            accesoires_amount = 0 
            for line in e.line_ids:
                if line.code == "BRUT_TOT":
                    accesoires_amount = line.amount
                    break
            sheet.write(row, 14, "{:,.0f}".format(accesoires_amount).replace(',', ' '), right_align_format)
            sheet.write(row, 15, "0", right_align_format)

            origin_value_amount = 0 
            for line in e.line_ids:
                if line.code == "IND_N_IMPOSABLE":
                    origin_value_amount = line.amount
                    break
            sheet.write(row, 16,  "{:,.0f}".format(origin_value_amount).replace(',', ' '), right_align_format)
            sheet.write(row, 17, "{:,.0f}".format(accesoires_amount).replace(',', ' '), right_align_format)
            sheet.write(row, 18, "0", right_align_format)
            sheet.write(row, 19, "{:,.0f}".format(accesoires_amount).replace(',', ' '), right_align_format)
            
            ricf_amount = 0 
            for line in e.line_ids:
                if line.code == "RICF":
                    ricf_amount = line.amount
                    break
            sheet.write(row, 20,  "{:,.0f}".format(ricf_amount).replace(',', ' '), right_align_format)
            
            its_brut_amount = 0 
            for line in e.line_ids:
                if line.code == "ITS":
                    its_brut_amount = line.amount
                    break
            sheet.write(row, 21,  "{:,.0f}".format(its_brut_amount).replace(',', ' '), right_align_format)

            its_net_amount = 0 
            for line in e.line_ids:
                if line.code == "TRFS":
                    its_net_amount = line.amount
                    break
            sheet.write(row, 22,  "{:,.0f}".format(its_net_amount).replace(',', ' '), right_align_format)

            sheet.write(row, 23, "0", right_align_format)
            sheet.write(row, 24, "{:,.0f}".format(its_net_amount).replace(',', ' '), right_align_format)
            sheet.write(row, 25, "0", right_align_format)
            sheet.write(row, 26, " ", right_align_format)

            row += 1


