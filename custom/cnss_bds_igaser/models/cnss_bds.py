import calendar
from odoo import models, fields
from datetime import datetime
import base64
from datetime import timedelta


class CnssBdsIgaser(models.Model):
    _name = 'cnss.bds'
    # Les caractéristiques des CNSS_BDS
    l_type_enreg = fields.Char('Type Enregistrement', size=3, required=True)
    n_num_affilie = fields.Char(
        'N°affiliation entreprise', size=7, required=True)
    l_annee = fields.Integer('Année', size=4, required=True)
    l_mois = fields.Integer('Mois', size=2, required=True)
    l_period = fields.Char('Période', size=6)
    n_num_assure = fields.Char('N°Immat assuré', size=9, required=True)
    employee_ids = fields.Many2one('hr.employee', size=60, string='Employees')
    l_num_cin = fields.Char('N°CIN', size=8)
    n_enfants = fields.Integer('Nombre Enfants', size=2)
    n_af_a_payer = fields.Integer(
        'N_AF_A_Payer', digits='Product Unit of Measure')
    n_af_a_deduire = fields.Integer(
        'N_AF_A_Deduire', digits='Product Unit of Measure')
    n_af_net_a_payer = fields.Integer(
        'N_AF_Net_A_Payer', digits='Product Unit of Measure')
    n_af_a_reverser = fields.Integer(
        'AF_A_Reverser', digits='Product Unit of Measure')
    # n_jour_declares = fields.Char('Jours_Declares', size=2)
    n_jour_declares = fields.Integer(
        'Jours_Declares', digits='Product Unit of Measure')
    n_salaire_reel = fields.Integer(
        'Salaire_Reel', digits='Product Unit of Measure')
    n_salaire_plaf = fields.Integer(
        'Salaire_Plaf', digits='Product Unit of Measure')
    n_situation = fields.Char('Situation', size=2)
    n_ctr = fields.Integer('CTR', digits='Product Unit of Measure')
    n_filler = fields.Char('Filler', size=104)
    l_status = fields.Char('Statut', size=10, required=True, default='NEW')

    def action_genere_bds(self):
        dict_type_1 = {
            'L_Type_Enreg': 3,
            'N_Identif_Transfert': 14,
            'L_Cat': 2,
            'L_filler': 241
        }

        dict_type_2 = {
            'L_Type_Enreg': 3,
            'N_Num_Affilie ': 7,
            'L_Periode': 6,
            'L_Raison_Sociale': 40,
            'L_Activite': 40,
            'L_Adresse': 120,
            'L_Ville': 20,
            'C_Code_Postal': 6,
            'C_Code_Agence': 2,
            'D_Date_Emission': 8,
            'D_Date_Exig': 8
        }

        dict_type_3 = {
            'L_Type_Enreg': 3,
            'N_Num_Affilie ': 7,
            'L_Periode': 6,
            'N_Num_Assure': 9,
            'L_Nom_Prenom': 60,
            'N_Enfants': 2,
            'N_AF_A_Payer': 6,
            'N_AF_A_Deduire': 6,
            'N_AF_Net_A_Payer': 6,
            'N_AF_A_Reverser': 6,
            'N_Jours_Declares': 2,
            'N_Salaire_Reel': 13,
            'N_Salaire_Plaf': 9,
            'L_Ville': 20,
            'L_Situation': 2,
            'S_Ctr': 19,
            'L_filler': 104
        }

        dict_type_4 = {
            'L_Type_Enreg': 3,
            'N_Num_Affilie ': 7,
            'L_Periode': 6,
            'N_Nbr_Salaries': 6,
            'N_T_Enfants': 6,
            'N_T_AF_A_Payer': 12,
            'N_T_AF_A_Deduire': 12,
            'N_T_AF_Net_A_Payer': 12,
            'N_T_Num_Imma': 15,
            'L_filler': 116
        }

        dict_type_5 = {
            'L_Type_Enreg': 3,
            'N_Num_Affilie ': 7,
            'L_Periode': 6,
            'L_filler': 124
        }

        dict_type_6 = {
            'L_Type_Enreg': 3,
            'N_Num_Affilie ': 7,
            'L_Periode': 6,
            'L_filler': 170
        }

        identif_Transfert = '27038922211011'
        num_imma = '000081351100199'
        agence = '13'
        myDateStart = datetime.strptime(
            f"01/03/2022", f"%d/%m/%Y").date()  # self.date_start
        myMonthStart = myDateStart.strftime("%m")
        mYearStart = myDateStart.strftime("%Y")
        # date end + 10days
        date_end = datetime.strptime(
            f"31/03/2022", f"%d/%m/%Y").date()
        myDateEnd = date_end + timedelta(days=10)
        mYearEnd = date_end.strftime("%Y")
        myMonthEnd = date_end.strftime("%m")
        myDayEnd = myDateEnd.strftime("%d")
        # date_sent_cnss = self.date_sent_cnss.strftime(
        #     "%Y%m%d") if self.date_sent_cnss else ''
        date_exig = myDateEnd.strftime("%Y%m%d")

        #############
        n_gt_nbr_salaries = 0
        n_gt_num_assur = 0
        n_gt_jours_dec = 0
        n_gt_salaire_reel = 0
        n_gt_salaire_plaf = 0
        l_gt_ctr = 0

        with open("/data/instances/test/extra/cnss_tst.txt", "w") as file:
            # first element(A00)
            line0 = 'B00' + str(identif_Transfert) + 'B0' + \
                ' '*dict_type_1['L_filler'] + '\n'
            file.write(line0)

            ##############################################################################
            line1 = 'B01' + str(identif_Transfert[0:7]) + str(mYearStart) + str(myMonthStart) + str(self.env.user.company_id.name) + ' '*(dict_type_2['L_Raison_Sociale']-len(self.env.user.company_id.name)) + ' '*dict_type_2['L_Activite'] + str(self.env.user.company_id.street) + ' '*(dict_type_2['L_Adresse']-len(self.env.user.company_id.street)) + str(
                self.env.user.company_id.city) + ' '*(dict_type_2['L_Ville']-len(self.env.user.company_id.city)) + str(self.env.user.company_id.zip) + ' '*(dict_type_2['C_Code_Postal']-len(self.env.user.company_id.zip)) + str(agence) + ' '*(dict_type_2['D_Date_Emission']) + str(date_exig) + '\n'
            file.write(line1)
            ##############################################################################
            bds_cnss = self.env['cnss.bds'].search(
                [('l_status', '=', 'TRAITE'), ('l_type_enreg', '=', 'B02')])

            num_affilie = ''
            period = ''
            nbr_salaries = 0
            total_childrens = 0
            n_t_num_assur = 0
            n_t_af_a_payer = 0
            n_t_af_a_deduire = 0
            n_t_af_net_a_payer = 0
            n_t_af_a_reverser = 0
            n_t_salaire_reel = 0
            n_t_salaire_plaf = 0
            n_t_jours_dec = 0
            l_t_ctr = 0

            for bds in bds_cnss:

                children = str(bds.n_enfants).rjust(2, '0')
                # if len(children) < 2:
                #     children = '0' + children

                mois = str(bds.l_mois).rjust(2, '0')

                l_situation = str(bds.n_situation).rjust(2)

                nbr_jour_dec = str(
                    int(float(bds.n_jour_declares))).rjust(2, '0')

                l_ctr = str(int(bds.n_ctr)).rjust(19, '0')
                l_filler = str(bds.n_filler).rjust(104)

                n_af_a_payer_str = str(bds.n_af_a_payer).ljust(6, '0')
                n_af_a_deduire_str = str(bds.n_af_a_deduire).ljust(6, '0')
                n_af_net_a_payer_str = str(
                    bds.n_af_net_a_payer).ljust(6, '0')
                n_af_a_reverser_str = str(
                    bds.n_af_a_reverser).ljust(6, '0')
                n_salaire_reel_str = str(bds.n_salaire_reel).ljust(13, '0')
                n_salaire_plaf_str = str(bds.n_salaire_plaf).ljust(9, '0')

                l_last_name = ''
                l_first_name = ''
                if bds.employee_ids.name:
                    full_name = bds.employee_ids.name
                    x = full_name.split()

                    if len(x) == 3:
                        l_last_name = str(x[0])+" "+str(x[1])
                        l_first_name = str(x[2])
                    elif len(x) == 2:
                        l_last_name = str(x[0])
                        l_first_name = str(x[1])

                l_last_name_str = str(l_last_name.ljust(30))
                l_first_name_str = str(l_first_name.ljust(30))
                # l_full_name_str = l_last_name_str+l_first_name_str

                line2 = str(bds.l_type_enreg) + str(bds.n_num_affilie[0:7]) + str(
                    bds.l_annee) + str(mois) + str(bds.n_num_assure) + str(l_last_name_str[0:30]) + str(l_first_name_str[0:30]) + children + n_af_a_payer_str + n_af_a_deduire_str + n_af_net_a_payer_str + n_af_a_reverser_str + str(nbr_jour_dec) + n_salaire_reel_str + n_salaire_plaf_str + l_situation + l_ctr + ' '*dict_type_3['L_filler'] + '\n'

                num_affilie = bds.n_num_affilie
                period = str(bds.l_annee) + str(mois)
                nbr_salaries += 1
                total_childrens += bds.n_enfants
                n_t_num_assur += int(bds.n_num_assure)
                n_t_af_a_payer += bds.n_af_a_payer
                n_t_af_a_deduire += bds.n_af_a_deduire
                n_t_af_net_a_payer += bds.n_af_net_a_payer
                n_t_af_a_reverser += bds.n_af_a_reverser
                n_t_salaire_reel += bds.n_salaire_reel
                n_t_salaire_plaf += bds.n_salaire_plaf
                n_t_jours_dec += int(float(bds.n_jour_declares))
                l_t_ctr += int(float(bds.n_ctr))

                file.write(line2)
            ##############################################################################

            l_type_enreg = "B03"
            n_num_affilie = num_affilie
            l_period = period
            n_t_nbr_salaries = str(nbr_salaries).rjust(6, '0')
            n_t_nbr_child = str(total_childrens).rjust(6, '0')
            n_t_af_a_payer_str = str(n_t_af_a_payer).ljust(12, '0')
            n_t_af_a_deduire_str = str(n_t_af_a_deduire).ljust(12, '0')
            n_t_af_net_a_payer_str = str(n_t_af_net_a_payer).ljust(12, '0')
            n_t_num_assur_str = str(n_t_num_assur).rjust(15, '0')
            n_t_af_a_reverser_str = str(n_t_af_a_reverser).ljust(12, '0')
            n_t_jours_dec_str = str(n_t_jours_dec).rjust(6, '0')
            n_t_salaire_reel_str = str(n_t_salaire_reel).ljust(15, '0')
            n_t_salaire_plaf_str = str(n_t_salaire_plaf).ljust(13, '0')
            l_t_ctr_str = str(l_t_ctr).rjust(19, '0')
            # TOT GLOBAL#####################################"

            n_gt_nbr_salaries += nbr_salaries
            n_gt_num_assur += n_t_num_assur
            n_gt_jours_dec += n_t_jours_dec
            n_gt_salaire_reel += n_t_salaire_reel
            n_gt_salaire_plaf += n_t_salaire_plaf
            l_gt_ctr += l_t_ctr

            # """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

            line3 = str(l_type_enreg)+str(n_num_affilie)+str(l_period) + str(n_t_nbr_salaries) + n_t_nbr_child + n_t_af_a_payer_str + n_t_af_a_deduire_str + \
                n_t_af_net_a_payer_str + n_t_num_assur_str + n_t_af_a_reverser_str+n_t_jours_dec_str + \
                n_t_salaire_reel_str+n_t_salaire_plaf_str + \
                l_t_ctr_str + ' '*dict_type_4['L_filler'] + '\n'
            file.write(line3)
            ##############################################################################
            bds_cnss = self.env['cnss.bds'].search(
                [('l_status', '=', 'TRAITE'), ('l_type_enreg', '=', 'B04')])
            num_affilie = ''
            period = ''
            nbr_salaries = 0
            n_t_num_assur = 0
            n_t_salaire_reel = 0
            n_t_salaire_plaf = 0
            n_t_jours_dec = 0
            l_t_ctr = 0
            for bds in bds_cnss:

                mois = str(bds.l_mois).rjust(2, '0')
                n_cin = str(bds.l_num_cin).ljust(8)

                nbr_jour_dec = str(
                    int(bds.n_jour_declares)).rjust(2, '0')

                l_ctr = str(bds.n_ctr).rjust(19, '0')
                l_filler = str(bds.n_filler).rjust(104)

                n_salaire_reel_str = str(bds.n_salaire_reel).rjust(13, '0')
                n_salaire_plaf_str = str(bds.n_salaire_plaf).rjust(9, '0')

                full_name = str(bds.employee_ids.name).ljust(60)
                # l_last_name = ''
                # l_first_name = ''
                # if bds.employee_ids.name:
                #     full_name = bds.employee_ids.name
                #     x = full_name.split()

                #     if len(x) == 3:
                #         l_last_name = str(x[0])+" "+str(x[1])
                #         l_first_name = str(x[2])
                #     elif len(x) == 2:
                #         l_last_name = str(x[0])
                #         l_first_name = str(x[1])

                # l_last_name_str = str(l_last_name.ljust(30))
                # l_first_name_str = str(l_first_name.ljust(30))
                # l_full_name_str = l_last_name_str+l_first_name_str

                num_affilie = bds.n_num_affilie
                period = str(bds.l_annee) + str(mois)
                nbr_salaries += 1
                n_t_num_assur += int(bds.n_num_assure)
                n_t_jours_dec += int(float(bds.n_jour_declares))
                n_t_salaire_reel += bds.n_salaire_reel
                n_t_salaire_plaf += bds.n_salaire_plaf
                l_t_ctr += int(float(bds.n_ctr))

                line4 = str(bds.l_type_enreg) + str(bds.n_num_affilie[0:7]) + str(
                    bds.l_annee) + str(mois) + str(bds.n_num_assure) + full_name + n_cin + str(nbr_jour_dec) + n_salaire_reel_str + n_salaire_plaf_str + l_ctr + ' '*dict_type_5['L_filler'] + '\n'

                # + ' '*(dict_type_3['L_Nom_Prenom']-len(payslip.employee_id.name)) + str(
                #     children) + ' '*(dict_type_3['N_AF_A_Payer']-len(amount_af_str)) + amount_af_str + ' '*(dict_type_3['N_AF_A_Deduire']-len(amount_ded_str)) + amount_ded_str + ' '*(dict_type_3['N_AF_Net_A_Payer']-len(net_apy_str)) + net_apy_str + ' '*dict_type_3['L_filler'] + '\n'

                file.write(line4)
            l_type_enreg = "B05"
            n_num_affilie = num_affilie
            l_period = period
            n_t_nbr_salaries = str(nbr_salaries).rjust(6, '0')
            n_t_num_assur_str = str(n_t_num_assur).rjust(15, '0')
            n_t_jours_dec_str = str(n_t_jours_dec).rjust(6, '0')
            n_t_salaire_reel_str = str(n_t_salaire_reel).ljust(15, '0')
            n_t_salaire_plaf_str = str(n_t_salaire_plaf).ljust(13, '0')
            l_t_ctr_str = str(l_t_ctr).rjust(19, '0')

            line5 = str(l_type_enreg)+str(n_num_affilie)+str(l_period) + str(n_t_nbr_salaries) + n_t_num_assur_str + n_t_jours_dec_str + \
                n_t_salaire_reel_str+n_t_salaire_plaf_str + \
                l_t_ctr_str + ' '*dict_type_6['L_filler'] + '\n'
            n_gt_nbr_salaries += nbr_salaries
            n_gt_num_assur += n_t_num_assur
            n_gt_jours_dec += n_t_jours_dec
            n_gt_salaire_reel += n_t_salaire_reel
            n_gt_salaire_plaf += n_t_salaire_plaf
            l_gt_ctr += l_t_ctr
            file.write(line5)

            l_type_enreg = "B06"
            n_gt_nbr_salaries_str = str(n_gt_nbr_salaries).rjust(6, '0')
            n_gt_num_assur_str = str(n_gt_num_assur).rjust(15, '0')
            n_gt_jours_dec_str = str(n_gt_jours_dec).rjust(6, '0')
            n_gt_salaire_reel_str = str(n_gt_salaire_reel).ljust(15, '0')
            n_gt_salaire_plaf_str = str(n_gt_salaire_plaf).ljust(13, '0')
            l_gt_ctr_str = str(l_gt_ctr).rjust(19, '0')
            line6 = str(l_type_enreg)+str(n_num_affilie)+str(l_period) + str(n_gt_nbr_salaries_str) + n_gt_num_assur_str + n_gt_jours_dec_str + \
                n_gt_salaire_reel_str+n_gt_salaire_plaf_str + \
                l_gt_ctr_str + ' '*dict_type_6['L_filler'] + '\n'
            file.write(line6)

            file.close()

        data = open("/data/instances/test/extra/cnss_tst.txt", "rb").read()
        encoded = base64.b64encode(data)
        # file_name = 'AFFEBDS_' + \
        #     str(date_sent_cnss) + '_' + str(mYearStart) + \
        #     str(myMonthStart) + '.txt'
        file_name = 'AFFEBDS'
        attach = self.env['ir.attachment'].create(
            {'name': file_name, 'type': 'binary', 'datas': encoded})
        download_url = '/web/content/' + str(attach.id) + '?download=true'

        return {
            'type': 'ir.actions.act_url',
            'url': str(download_url),
            'target': 'new'
        }

    def action_genere(self):

        # nbr_enfants = 2
        emp_cnss = self.env['hr.employee'].search(
            [('ssnid', '=', self.n_num_assure)])
        self.n_enfants = emp_cnss.children
        self.employee_ids = emp_cnss.id

        ####################################

        payslip_date = datetime.strptime(
            f"15/{self.l_mois}/{self.l_annee}", f"%d/%m/%Y").date()
        payslip = self.env['hr.payslip'].search([('employee_id', '=', self.employee_ids.id), (
            'date_to', '>=', payslip_date), ('date_from', '<=', payslip_date)])

        for ps in payslip:
            line_af = self.env['hr.payslip.line'].search(
                [('slip_id', '=', ps.id), ('code', '=', 'AF')])
            amount_af = 0
            if line_af:
                amount_af = line_af.total
                self.n_af_a_payer = amount_af
            line_sb = self.env['hr.payslip.line'].search(
                [('slip_id', '=', ps.id), ('code', '=', 'SBG')])
            amount_sbg = 0
            if line_sb:
                amount_sbg = line_sb.total
                self.salaire_brut = amount_sbg
            # amount_ded = 0
            # net_apy = amount_af-amount_ded
            # children = str(payslip.employee_id.children)
            # amount_af_str = str(int(round(amount_af, 2)))[0:6]
            # amount_ded_str = str(int(round(amount_ded, 2)))[0:6]
            # net_apy_str = str(int(round(net_apy, 2)))[0:6]

    def action_genere_bdsV1(self, data):
        dict_type_1 = {
            'L_Type_Enreg': 3,
            'N_Identif_Transfert': 14,
            'L_Cat': 2,
            'L_filler': 241
        }

        dict_type_2 = {
            'L_Type_Enreg': 3,
            'N_Num_Affilie ': 7,
            'L_Periode': 6,
            'L_Raison_Sociale': 40,
            'L_Activite': 40,
            'L_Adresse': 120,
            'L_Ville': 20,
            'C_Code_Postal': 6,
            'C_Code_Agence': 2,
            'D_Date_Emission': 8,
            'D_Date_Exig': 8
        }

        dict_type_3 = {
            'L_Type_Enreg': 3,
            'N_Num_Affilie ': 7,
            'L_Periode': 6,
            'N_Num_Assure': 9,
            'L_Nom_Prenom': 60,
            'N_Enfants': 2,
            'N_AF_A_Payer': 6,
            'N_AF_A_Deduire': 6,
            'N_AF_Net_A_Payer': 6,
            'N_AF_A_Reverser': 6,
            'N_Jours_Declares': 2,
            'N_Salaire_Reel': 13,
            'N_Salaire_Plaf': 9,
            'L_Ville': 20,
            'L_Situation': 2,
            'S_Ctr': 19,
            'L_filler': 104
        }

        dict_type_4 = {
            'L_Type_Enreg': 3,
            'N_Num_Affilie ': 7,
            'L_Periode': 6,
            'N_Nbr_Salaries': 6,
            'N_T_Enfants': 6,
            'N_T_AF_A_Payer': 12,
            'N_T_AF_A_Deduire': 12,
            'N_T_AF_Net_A_Payer': 12,
            'N_T_Num_Imma': 15,
            'L_filler': 116
        }

        dict_type_5 = {
            'L_Type_Enreg': 3,
            'N_Num_Affilie ': 7,
            'L_Periode': 6,
            'L_filler': 124
        }

        dict_type_6 = {
            'L_Type_Enreg': 3,
            'N_Num_Affilie ': 7,
            'L_Periode': 6,
            'L_filler': 170
        }

        identif_Transfert = data['id_trans']
        agence = '13'
        bds_annee = data['annee']
        bds_mois = data['mois']
        res = calendar.monthrange(bds_annee, bds_mois)
        day = res[1]
        date_end = datetime.strptime(
            f"{day}/{bds_mois}/{bds_annee}", f"%d/%m/%Y").date()
        myDateEnd = date_end + timedelta(days=10)
        date_sent_cnss = data['sent_date'].strftime("%Y%m%d")
        date_exig = myDateEnd.strftime("%Y%m%d")
        bds_annee_str = str(bds_annee)
        bds_mois_str = str(bds_mois).rjust(2, '0')
        #############
        n_gt_nbr_salaries = 0
        n_gt_num_assur = 0
        n_gt_jours_dec = 0
        n_gt_salaire_reel = 0
        n_gt_salaire_plaf = 0
        l_gt_ctr = 0

        with open("/data/instances/test/extra/cnss_tst.txt", "w") as file:
            # with open("./cnss_tst.txt", "w") as file:
            # first element(A00)
            line0 = 'B00' + str(identif_Transfert) + 'B0' + \
                ' '*dict_type_1['L_filler'] + '\n'

            file.write(line0)

            ##############################################################################
            # str(self.env.user.company_id.name)
            # str(self.env.user.company_id.street)
            line1 = 'B01' + str(identif_Transfert[0:7]) + bds_annee_str + bds_mois_str + ' STE IGASER  SARL' + ' '*(dict_type_2['L_Raison_Sociale']-len(' STE IGASER  SARL')) + ' '*dict_type_2['L_Activite'] + 'LOT 315 ZONE INDUSTRIELLE' + ' '*(dict_type_2['L_Adresse']-len('LOT 315 ZONE INDUSTRIELLE')) + str(
                self.env.user.company_id.city) + ' '*(dict_type_2['L_Ville']-len(self.env.user.company_id.city)) + str(self.env.user.company_id.zip) + ' '*(dict_type_2['C_Code_Postal']-len(self.env.user.company_id.zip)) + str(agence) + str(date_sent_cnss) + str(date_exig) + '\n'
            file.write(line1)
            ##############################################################################
            str_bds_annee = str(bds_annee)
            str_bds_mois = str(bds_mois)
            if len(str(bds_mois)) < 2:
                str_bds_mois = '0'+str(bds_mois)

            bds_cnss = self.env['cnss.bds'].search([('l_status', '=', 'TRAITE'), (
                'l_type_enreg', '=', 'B02'), ('l_annee', '=', bds_annee), ('l_mois', '=', bds_mois)])

            num_affilie = ''
            period = ''
            nbr_salaries = 0
            total_childrens = 0
            n_t_num_assur = 0
            n_t_af_a_payer = 0
            n_t_af_a_deduire = 0
            n_t_af_net_a_payer = 0
            n_t_af_a_reverser = 0
            n_t_salaire_reel = 0
            n_t_salaire_plaf = 0
            n_t_jours_dec = 0
            l_t_ctr = 0

            for bds in bds_cnss:

                children = str(bds.n_enfants).rjust(2, '0')
                # if len(children) < 2:
                #     children = '0' + children

                mois = str(bds.l_mois).rjust(2, '0')

                if bds.n_situation:
                    l_situation = str(bds.n_situation).rjust(2)
                else:
                    l_situation = "  "

                nbr_jour_dec = str(
                    int(bds.n_jour_declares)).rjust(2, '0')

                l_filler = str(bds.n_filler).rjust(104)

                # v_l_ctr = (bds.n_salaire_reel)+(bds.n_salaire_plaf)+int(bds.n_jour_declares)+int(bds.n_num_assure)

                l_ctr = str(bds.n_ctr).rjust(19, '0')

                n_af_a_payer_str = str(int(bds.n_af_a_payer)).rjust(6, '0')
                n_af_a_deduire_str = str(
                    int(bds.n_af_a_deduire)).rjust(6, '0')
                n_af_net_a_payer_str = str(
                    int(bds.n_af_net_a_payer)).rjust(6, '0')
                n_af_a_reverser_str = str(
                    int(bds.n_af_a_reverser)).rjust(6, '0')
                n_salaire_reel_str = str(
                    int(bds.n_salaire_reel)).rjust(13, '0')
                n_salaire_plaf_str = str(
                    int(bds.n_salaire_plaf)).rjust(9, '0')

                l_last_name = ''
                l_first_name = ''
                if bds.employee_ids.name:
                    full_name = bds.employee_ids.name
                    x = full_name.split()

                    if len(x) == 3:
                        l_last_name = str(x[0])+" "+str(x[1])
                        l_first_name = str(x[2])
                    elif len(x) == 2:
                        l_last_name = str(x[0])
                        l_first_name = str(x[1])

                l_last_name_str = str(l_last_name.ljust(30))
                l_first_name_str = str(l_first_name.ljust(30))
                # l_full_name_str = l_last_name_str+l_first_name_str

                line2 = str(bds.l_type_enreg) + str(bds.n_num_affilie[0:7]) + str(
                    bds.l_annee) + str(mois) + str(bds.n_num_assure) + str(l_last_name_str[0:30]) + str(l_first_name_str[0:30]) + children + n_af_a_payer_str + n_af_a_deduire_str + n_af_net_a_payer_str + n_af_a_reverser_str + str(nbr_jour_dec) + n_salaire_reel_str + n_salaire_plaf_str + l_situation + l_ctr + ' '*dict_type_3['L_filler'] + '\n'

                num_affilie = bds.n_num_affilie
                period = str(bds.l_annee) + str(mois)
                nbr_salaries += 1
                total_childrens += bds.n_enfants
                n_t_num_assur += int(bds.n_num_assure)
                n_t_af_a_payer += bds.n_af_a_payer
                n_t_af_a_deduire += bds.n_af_a_deduire
                n_t_af_net_a_payer += bds.n_af_net_a_payer
                n_t_af_a_reverser += bds.n_af_a_reverser
                n_t_salaire_reel += bds.n_salaire_reel
                n_t_salaire_plaf += bds.n_salaire_plaf
                n_t_jours_dec += bds.n_jour_declares
                l_t_ctr += bds.n_ctr

                file.write(line2)
            ##############################################################################

            l_type_enreg = "B03"
            n_num_affilie = num_affilie
            l_period = period
            n_t_nbr_salaries = str(nbr_salaries).rjust(6, '0')
            n_t_nbr_child = str(total_childrens).rjust(6, '0')
            n_t_af_a_payer_str = str(int(n_t_af_a_payer)).ljust(12, '0')
            n_t_af_a_deduire_str = str(
                int(n_t_af_a_deduire)).ljust(12, '0')
            n_t_af_net_a_payer_str = str(
                int(n_t_af_net_a_payer)).ljust(12, '0')
            n_t_num_assur_str = str(n_t_num_assur).rjust(15, '0')
            n_t_af_a_reverser_str = str(
                int(n_t_af_a_reverser)).ljust(12, '0')
            n_t_jours_dec_str = str(int(n_t_jours_dec)).rjust(6, '0')
            n_t_salaire_reel_str = str(
                int(n_t_salaire_reel)).rjust(15, '0')
            n_t_salaire_plaf_str = str(
                int(n_t_salaire_plaf)).rjust(13, '0')
            l_t_ctr_str = str(int(l_t_ctr)).rjust(19, '0')
            # TOT GLOBAL#####################################"

            n_gt_nbr_salaries += nbr_salaries
            n_gt_num_assur += n_t_num_assur
            n_gt_jours_dec += n_t_jours_dec
            n_gt_salaire_reel += n_t_salaire_reel
            n_gt_salaire_plaf += n_t_salaire_plaf
            l_gt_ctr += l_t_ctr

            # """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

            line3 = str(l_type_enreg)+str(n_num_affilie)+str(l_period) + str(n_t_nbr_salaries) + n_t_nbr_child + n_t_af_a_payer_str + n_t_af_a_deduire_str + \
                n_t_af_net_a_payer_str + n_t_num_assur_str + n_t_af_a_reverser_str+n_t_jours_dec_str + \
                n_t_salaire_reel_str+n_t_salaire_plaf_str + \
                l_t_ctr_str + ' '*dict_type_4['L_filler'] + '\n'
            file.write(line3)
            ##############################################################################
            bds_cnss = self.env['cnss.bds'].search(
                [('l_status', '=', 'TRAITE'), ('l_type_enreg', '=', 'B04'), ('l_annee', '=', bds_annee), ('l_mois', '=', bds_mois)])
            num_affilie = ''
            period = ''
            nbr_salaries = 0
            n_t_num_assur = 0
            n_t_salaire_reel = 0
            n_t_salaire_plaf = 0
            n_t_jours_dec = 0
            l_t_ctr = 0
            for bds in bds_cnss:

                mois = str(bds.l_mois).rjust(2, '0')
                n_cin = str(bds.l_num_cin).ljust(8)

                nbr_jour_dec = str(
                    int(bds.n_jour_declares)).rjust(2, '0')

                l_ctr = str(bds.n_ctr).rjust(19, '0')
                l_filler = str(bds.n_filler).rjust(104)

                n_salaire_reel_str = str(
                    int(bds.n_salaire_reel)).rjust(13, '0')
                n_salaire_plaf_str = str(
                    int(bds.n_salaire_plaf)).rjust(9, '0')

                full_name = str(bds.employee_ids.name).ljust(60)
                # l_last_name = ''
                # l_first_name = ''
                # if bds.employee_ids.name:
                #     full_name = bds.employee_ids.name
                #     x = full_name.split()

                #     if len(x) == 3:
                #         l_last_name = str(x[0])+" "+str(x[1])
                #         l_first_name = str(x[2])
                #     elif len(x) == 2:
                #         l_last_name = str(x[0])
                #         l_first_name = str(x[1])

                # l_last_name_str = str(l_last_name.ljust(30))
                # l_first_name_str = str(l_first_name.ljust(30))
                # l_full_name_str = l_last_name_str+l_first_name_str

                num_affilie = bds.n_num_affilie
                period = str(bds.l_annee) + str(mois)
                nbr_salaries += 1
                n_t_num_assur += int(bds.n_num_assure)
                n_t_jours_dec += bds.n_jour_declares
                n_t_salaire_reel += bds.n_salaire_reel
                n_t_salaire_plaf += bds.n_salaire_plaf
                l_t_ctr += bds.n_ctr

                line4 = str(bds.l_type_enreg) + str(bds.n_num_affilie[0:7]) + str(
                    bds.l_annee) + str(mois) + str(bds.n_num_assure) + full_name + n_cin + str(nbr_jour_dec) + n_salaire_reel_str + n_salaire_plaf_str + l_ctr + ' '*dict_type_5['L_filler'] + '\n'

                # + ' '*(dict_type_3['L_Nom_Prenom']-len(payslip.employee_id.name)) + str(
                #     children) + ' '*(dict_type_3['N_AF_A_Payer']-len(amount_af_str)) + amount_af_str + ' '*(dict_type_3['N_AF_A_Deduire']-len(amount_ded_str)) + amount_ded_str + ' '*(dict_type_3['N_AF_Net_A_Payer']-len(net_apy_str)) + net_apy_str + ' '*dict_type_3['L_filler'] + '\n'

                file.write(line4)
            l_type_enreg = "B05"
            n_num_affilie = num_affilie
            l_period = period
            n_t_nbr_salaries = str(nbr_salaries).rjust(6, '0')
            n_t_num_assur_str = str(n_t_num_assur).rjust(15, '0')
            n_t_jours_dec_str = str(int(n_t_jours_dec)).rjust(6, '0')
            n_t_salaire_reel_str = str(
                int(n_t_salaire_reel)).rjust(15, '0')
            n_t_salaire_plaf_str = str(
                int(n_t_salaire_plaf)).rjust(13, '0')
            l_t_ctr_str = str(int(l_t_ctr)).rjust(19, '0')

            line5 = str(l_type_enreg)+str(n_num_affilie)+str(l_period) + str(n_t_nbr_salaries) + n_t_num_assur_str + n_t_jours_dec_str + \
                n_t_salaire_reel_str+n_t_salaire_plaf_str + \
                l_t_ctr_str + ' '*dict_type_6['L_filler'] + '\n'
            n_gt_nbr_salaries += nbr_salaries
            n_gt_num_assur += n_t_num_assur
            n_gt_jours_dec += n_t_jours_dec
            n_gt_salaire_reel += n_t_salaire_reel
            n_gt_salaire_plaf += n_t_salaire_plaf
            l_gt_ctr += l_t_ctr
            file.write(line5)

            l_type_enreg = "B06"
            n_gt_nbr_salaries_str = str(n_gt_nbr_salaries).rjust(6, '0')
            n_gt_num_assur_str = str(n_gt_num_assur).rjust(15, '0')
            n_gt_jours_dec_str = str(int(n_gt_jours_dec)).rjust(6, '0')
            n_gt_salaire_reel_str = str(
                int(n_gt_salaire_reel)).rjust(15, '0')
            n_gt_salaire_plaf_str = str(
                int(n_gt_salaire_plaf)).rjust(13, '0')
            l_gt_ctr_str = str(int(l_gt_ctr)).rjust(19, '0')
            line6 = str(l_type_enreg)+str(n_num_affilie)+str(l_period) + str(n_gt_nbr_salaries_str) + n_gt_num_assur_str + n_gt_jours_dec_str + \
                n_gt_salaire_reel_str+n_gt_salaire_plaf_str + \
                l_gt_ctr_str + ' '*dict_type_6['L_filler'] + '\n'
            file.write(line6)

            file.close()

        data = open("/data/instances/test/extra/cnss_tst.txt", "rb").read()
        # data = open("./cnss_tst.txt", "rb").read()
        encoded = base64.b64encode(data)
        file_name = 'DS_' + \
            str(n_num_affilie) + '_' + bds_annee_str + \
            bds_mois_str + '.txt'
        # file_name = 'AFFEBDS'
        attach = self.env['ir.attachment'].create(
            {'name': file_name, 'type': 'binary', 'datas': encoded})
        download_url = '/web/content/' + str(attach.id) + '?download=true'

        return {
            'type': 'ir.actions.act_url',
            'url': str(download_url),
            'target': 'new'
        }
