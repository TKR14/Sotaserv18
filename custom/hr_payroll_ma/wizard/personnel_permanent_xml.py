from odoo import fields, models
import xml.etree.ElementTree as ET 
import base64


class PersonnelPermanenetXML(models.TransientModel):
    _name = "personnel.permanent.xml"
    year = fields.Date("Année", required = True)

    def generateXML(self):
        company = self.env['res.company'].search([])[0]
        # employees = self.env['hr.employee'].get_employees()
        employees = self.env['hr.payslip'].get_employees(self.year.year)
        
        total_total_mt_revenu_brut_imposable_pp = 0
        total_total_mt_revenu_net_imposable_pp = 0
        total_total_mt_total_deduction_pp = 0
        total_total_mt_ir_preleve_pp = 0
        total_totalsommepayerts = 0

        v_tot_mt_abondement = 0
        v_montant_permanent = 0
        v_montant_occasionnel = 0
        v_montant_stagiaire = 0

        traitement_et_salaire = ET.Element('TraitementEtSalaire')

        identifiant_fiscal = ET.SubElement(traitement_et_salaire, 'identifiantFiscal')
        identifiant_fiscal.text = company.vat

        nom = ET.SubElement(traitement_et_salaire, 'nom')

        prenom = ET.SubElement(traitement_et_salaire, 'prenom')

        raison_sociale = ET.SubElement(traitement_et_salaire, 'raisonSociale')
        raison_sociale.text = company.name

        exercice_fiscal_du = ET.SubElement(traitement_et_salaire, 'exerciceFiscalDu')
        exercice_fiscal_du.text = f'{self.year.year}-01-01'

        exercice_fiscal_au = ET.SubElement(traitement_et_salaire, 'exerciceFiscalAu')
        exercice_fiscal_au.text = f'{self.year.year}-12-31'

        annee = ET.SubElement(traitement_et_salaire, 'annee')
        annee.text = f'{self.year.year}'

        commune = ET.SubElement(traitement_et_salaire, 'commune')

        code = ET.SubElement(commune, 'code')
        code.text = '141.01.73'

        adresse = ET.SubElement(traitement_et_salaire, 'adresse')
        adresse.text = company.street

        numero_cin = ET.SubElement(traitement_et_salaire, 'numeroCIN')

        numero_cnss = ET.SubElement(traitement_et_salaire, 'numeroCNSS')
        numero_cnss.text = '2703892'

        numero_ce = ET.SubElement(traitement_et_salaire, 'numeroCE')
        numero_ce = company.ice

        numero_rc = ET.SubElement(traitement_et_salaire, 'numeroRC')
        numero_rc.text = company.company_registry

        identifiant_tp = ET.SubElement(traitement_et_salaire, 'identifiantTP')
        identifiant_tp.text = '42104582'

        numero_fax = ET.SubElement(traitement_et_salaire, 'numeroFax')
        numero_fax.text = '0523352901'
        numero_telephone = ET.SubElement(traitement_et_salaire, 'numeroTelephone')
        numero_telephone.text = company.phone
        
        email = ET.SubElement(traitement_et_salaire, 'email')
        email.text = company.email

        effectif_total = ET.SubElement(traitement_et_salaire, 'effectifTotal')
        effectif_total.text = f'{len(employees)}'

        nbr_perso_permanent = ET.SubElement(traitement_et_salaire, 'nbrPersoPermanent')
        nbr_perso_permanent.text = f'{len(employees)}'

        nbr_perso_occasionnel = ET.SubElement(traitement_et_salaire, 'nbrPersoOccasionnel')
        nbr_perso_occasionnel.text = '0'

        nbr_stagiaires = ET.SubElement(traitement_et_salaire, 'nbrStagiaires')
        nbr_stagiaires.text = '0'

        total_mt_revenu_brut_imposable_pp = ET.SubElement(traitement_et_salaire, 'totalMtRevenuBrutImposablePP')

        total_mt_revenu_net_imposable_pp = ET.SubElement(traitement_et_salaire, 'totalMtRevenuNetImposablePP')

        total_mt_total_deduction_pp = ET.SubElement(traitement_et_salaire, 'totalMtTotalDeductionPP')

        total_mt_ir_preleve_pp = ET.SubElement(traitement_et_salaire, 'totalMtIrPrelevePP')

        total_mt_brut_sommes_po = ET.SubElement(traitement_et_salaire, 'totalMtBrutSommesPO')
        total_mt_brut_sommes_po.text = '0.00'

        total_ir_preleve_po = ET.SubElement(traitement_et_salaire, 'totalIrPrelevePO')
        total_ir_preleve_po.text = '0.00'

        total_mt_brut_trait_salaire_stg = ET.SubElement(traitement_et_salaire, 'totalMtBrutTraitSalaireSTG')
        total_mt_brut_trait_salaire_stg.text = '0.00'

        total_mt_brut_indemnites_stg = ET.SubElement(traitement_et_salaire, 'totalMtBrutIndemnitesSTG')
        total_mt_brut_indemnites_stg.text = '0.00'

        total_mt_retenues_stg = ET.SubElement(traitement_et_salaire, 'totalMtRetenuesSTG')
        total_mt_retenues_stg.text = '0.00'

        total_mt_revenu_net_imp_stg = ET.SubElement(traitement_et_salaire, 'totalMtRevenuNetImpSTG')
        total_mt_revenu_net_imp_stg.text = '0.00'

        # ?
        total_somme_paye_rts = ET.SubElement(traitement_et_salaire, 'totalSommePayeRTS')

        
        

        # ?
        total_mt_anuuel_revenu_salarial = ET.SubElement(traitement_et_salaire, 'totalmtAnuuelRevenuSalarial')
         

        total_mt_abondement = ET.SubElement(traitement_et_salaire, 'totalmtAbondement')
        total_mt_abondement.text = f'{v_tot_mt_abondement:.2f}'

        montant_permanent = ET.SubElement(traitement_et_salaire, 'montantPermanent')
       

        montant_occasionnel = ET.SubElement(traitement_et_salaire, 'montantOccasionnel')
        montant_occasionnel.text = f'{v_montant_occasionnel:.2f}'

        montant_stagiaire = ET.SubElement(traitement_et_salaire, 'montantStagiaire')
        montant_stagiaire.text = f'{v_montant_stagiaire:.2f}'

        list_personnel_permanent = ET.SubElement(traitement_et_salaire, 'listPersonnelPermanent')


        # def calc_rubrique_total(employee, rub_code):
        #     self.env['hr.payslip'].calc_rubrique_total(self.year, employee, rub_code)

        for employee in employees:
            # sal_base
            sal_base = self.env['hr.payslip'].calc_rubrique_total(self.year.year, employee, ['BASIC', '38'])

            # 1
            sal_base_anc_mnt = self.env['hr.payslip'].calc_rubrique_total(self.year.year, employee, ['SBG'])

            # 2
            tpimp = self.env['hr.payslip'].calc_rubrique_total(self.year.year, employee, [])

            # 3
            undefined = self.env['hr.payslip'].calc_rubrique_total(self.year.year, employee, [])

            # 4
            tnimp_gs_tot = self.env['hr.payslip'].calc_rubrique_total(self.year.year, employee, ['TPNI', 'GS_TOT'])

            # t
            taux_pro = self.env['hr.payslip'].calc_rubrique_total(self.year.year, employee, [])

            # 5
            rev_brut_impo_5 = (sal_base_anc_mnt  - tnimp_gs_tot)

            # 6
            fp = self.env['hr.payslip'].calc_rubrique_total(self.year.year, employee, ['ABT'])

            # 7
            ret_comp_tot = self.env['hr.payslip'].calc_rubrique_total(self.year.year, employee, [])

            # 8
            cot_tot_ps = self.env['hr.payslip'].calc_rubrique_total(self.year.year, employee, ['TRET'])

            # 9
            int_logement = self.env['hr.payslip'].calc_rubrique_total(self.year.year, employee, ['INT_LOGEMENT'])

            # 10
            rev_net_impo_10 = rev_brut_impo_5 - (fp + ret_comp_tot + cot_tot_ps + int_logement)

            mt_tot_ded = 0
            mt_tot_ded = fp + cot_tot_ps

            # chargfam

             
            if employee.marital != "married" or employee.gender == "female":
                chargfam = 0 
            elif (employee.children+1) < 6:
                chargfam=(employee.children+1)
            else: 
                chargfam = 6
                

            #chargfam = self.env['hr.payslip'].calc_rubrique_total(self.year.year, employee, ['CHRGFAM'])

            # worked_days
            worked_days = self.env['hr.payslip'].calc_rubrique_total(self.year.year, employee, ['WDAYS'])

            # ret_ir
            ret_ir = self.env['hr.payslip'].calc_rubrique_total(self.year.year, employee, ['69'])
        
            total_total_mt_revenu_brut_imposable_pp += rev_brut_impo_5
            total_total_mt_revenu_net_imposable_pp += rev_net_impo_10
            total_total_mt_total_deduction_pp += mt_tot_ded
            total_total_mt_ir_preleve_pp += ret_ir
            total_totalsommepayerts  += sal_base_anc_mnt
            v_montant_permanent      += sal_base_anc_mnt


            personnel_permanent = ET.SubElement(list_personnel_permanent, 'PersonnelPermanent')

            nom_pp = ET.SubElement(personnel_permanent, 'nom')
            nom_pp.text = employee.last_name

            prenom_pp = ET.SubElement(personnel_permanent, 'prenom')
            prenom_pp.text = employee.first_name

            adresse_personnelle = ET.SubElement(personnel_permanent, 'adressePersonnelle')
            adresse_personnelle.text = employee.address

            num_cni = ET.SubElement(personnel_permanent, 'numCNI')
            num_cni.text = employee.identification_id

            num_ce = ET.SubElement(personnel_permanent, 'numCE')

            num_ppr = ET.SubElement(personnel_permanent, 'numPPR')

            num_cnss = ET.SubElement(personnel_permanent, 'numCNSS')
            num_cnss.text = employee.ssnid

            ifu = ET.SubElement(personnel_permanent, 'ifu')

            # sal_base
            salaire_base_annuel = ET.SubElement(personnel_permanent, 'salaireBaseAnnuel')
            salaire_base_annuel.text = f'{sal_base:.2f}'

            # 1
            mt_brut_traitement_salaire = ET.SubElement(personnel_permanent, 'mtBrutTraitementSalaire')
            mt_brut_traitement_salaire.text = f'{sal_base_anc_mnt:.2f}'

            # worked_days
            periode = ET.SubElement(personnel_permanent, 'periode')
            periode.text = f'{worked_days}'

            # 4
            mt_exonere = ET.SubElement(personnel_permanent, 'mtExonere')
            mt_exonere.text = f'{tnimp_gs_tot:.2f}'

            # 9
            mt_echeances = ET.SubElement(personnel_permanent, 'mtEcheances')
            mt_echeances.text = f'{int_logement:.2f}'

            # chargfam
            nbr_reductions = ET.SubElement(personnel_permanent, 'nbrReductions')
            nbr_reductions.text = str(chargfam)

            # 3
            mt_indemnite = ET.SubElement(personnel_permanent, 'mtIndemnite')
            mt_indemnite.text = '0.00'

            # 2
            mt_avantages = ET.SubElement(personnel_permanent, 'mtAvantages')
            mt_avantages.text = f'{tpimp:.2f}'

            # 5
            mt_revenu_brut_imposable = ET.SubElement(personnel_permanent, 'mtRevenuBrutImposable')
            mt_revenu_brut_imposable.text = f'{rev_brut_impo_5:.2f}'

            # 6
            mt_frais_profess = ET.SubElement(personnel_permanent, 'mtFraisProfess')
            mt_frais_profess.text = f'{fp:.2f}'

            # 7
            mt_cotisation_assur = ET.SubElement(personnel_permanent, 'mtCotisationAssur')
            mt_cotisation_assur.text = f'{ret_comp_tot:.2f}'

            # 8
            mt_autres_retenues = ET.SubElement(personnel_permanent, 'mtAutresRetenues')
            mt_autres_retenues.text = f'{cot_tot_ps:.2f}'

            # rev_net_impo_10
            mt_revenu_net_imposable = ET.SubElement(personnel_permanent, 'mtRevenuNetImposable')
            mt_revenu_net_imposable.text = f'{rev_net_impo_10:.2f}'

            mt_total_deduction = ET.SubElement(personnel_permanent, 'mtTotalDeduction')
            mt_total_deduction.text = f'{mt_tot_ded:.2f}'

            # ret_ir
            ir_preleve = ET.SubElement(personnel_permanent, 'irPreleve')
            ir_preleve.text = f'{ret_ir:.2f}'

            cas_sportif = ET.SubElement(personnel_permanent, 'casSportif')
            cas_sportif.text = 'false'

            num_matricule = ET.SubElement(personnel_permanent, 'numMatricule')
            num_matricule.text = str(employee.registration_number).rjust(7, '0')

            date_permis = ET.SubElement(personnel_permanent, 'datePermis')
            date_permis.text = f'{self.year.year}-12-31'

            date_autorisation = ET.SubElement(personnel_permanent, 'dateAutorisation')
            date_autorisation.text = f'{self.year.year}-12-31'

            ref_situation_familiale = ET.SubElement(personnel_permanent, 'refSituationFamiliale')

            marital = ""
            if employee.marital == "single":
                marital = "C"
            elif employee.marital == "married":
                marital = "M"
            elif employee.marital == "divorced":
                marital = "D"
            elif employee.marital == "widower":
                marital = "V"

            code_sf = ET.SubElement(ref_situation_familiale, 'code')
            code_sf.text = marital

            ref_taux = ET.SubElement(personnel_permanent, 'refTaux')

            code_taux = ET.SubElement(ref_taux, 'code')
            code_taux.text = 'TPP.20.2009'

            list_elements_exonere = ET.SubElement(personnel_permanent, 'listElementsExonere')

            # LOOP
            for element_code in ['53', '54', '46', '56', '49', '45']:
                element_exonere_pp = ET.SubElement(list_elements_exonere, 'ElementExonerePP')

                mt = self.env['hr.payslip'].calc_rubrique_total(self.year.year, employee, [element_code])

                montant_exonere = ET.SubElement(element_exonere_pp, 'montantExonere')
                montant_exonere.text = f'{mt:.2f}'

                ref_nature_element_exonere = ET.SubElement(element_exonere_pp, 'refNatureElementExonere')
                
                code_nee = ET.SubElement(ref_nature_element_exonere, 'code')
                #code_nee.text = element_code
                if element_code == "53":
                    code_nee.text = "NAT_ELEM_EXO_2"
                elif element_code == "49":
                    code_nee.text = "NAT_ELEM_EXO_14"
                elif element_code == "46":
                    code_nee.text = "NAT_ELEM_EXO_7"
                elif element_code == "54":
                    code_nee.text = "NAT_ELEM_EXO_5"
                elif element_code == "56":
                    code_nee.text = "NAT_ELEM_EXO_9"
                elif element_code == "45":
                    code_nee.text = "NAT_ELEM_EXO_25"
        
        v_totalmtannurevsal = v_montant_stagiaire + v_montant_occasionnel + v_montant_permanent + v_tot_mt_abondement

        total_mt_revenu_brut_imposable_pp.text = f'{total_total_mt_revenu_brut_imposable_pp:.2f}'
        total_mt_revenu_net_imposable_pp.text = f'{total_total_mt_revenu_net_imposable_pp:.2f}'
        total_mt_total_deduction_pp.text = f'{total_total_mt_total_deduction_pp:.2f}'
        total_mt_ir_preleve_pp.text = f'{total_total_mt_ir_preleve_pp:.2f}'
        total_somme_paye_rts.text = f'{total_totalsommepayerts:.2f}'
        total_mt_anuuel_revenu_salarial.text = f'{v_totalmtannurevsal:.2f}'
        montant_permanent.text = f'{v_montant_permanent:.2f}'

        # list_personnel_exonere = ET.SubElement(traitement_et_salaire, 'listPersonnelExonere')

        # list_personnel_occasionnel = ET.SubElement(traitement_et_salaire, 'listPersonnelOccasionnel')

        # list_stagiaires = ET.SubElement(traitement_et_salaire, 'listStagiaires')

        # list_doctorants = ET.SubElement(traitement_et_salaire, 'listDoctorants')

        # list_beneficiaires = ET.SubElement(traitement_et_salaire, 'listBeneficiaires')

        # list_beneficiaires_plan_epargne = ET.SubElement(traitement_et_salaire, 'listBeneficiairesPlanEpargne')

        #list_versements = ET.SubElement(traitement_et_salaire, 'listVersements')

        b_xml = ET.tostring(traitement_et_salaire)
        encoded = base64.b64encode(b_xml)
        attach = self.env['ir.attachment'].create({'name': '9421.xml', 'type': 'binary', 'datas': encoded})
        download_url = '/web/content/' + str(attach.id) + '?download=true'
        
        return {
            'type': 'ir.actions.act_url',
            'url': str(download_url),
            'target': 'new'
        }
