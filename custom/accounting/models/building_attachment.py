from odoo import models
from num2words import num2words


class building_attachment(models.Model):
    _inherit = 'building.attachment'


    def amount_in_word(self, amount):

        word_num = str(self.env['res.company'].search([])[0].currency_id.amount_to_text(amount))
        return word_num
    
    def amount_remaining_in_word(self, amount):
        currency = self.env['res.company'].search([], limit=1).currency_id

        amount_main = int(amount)
        amount_cents = int(round((amount - amount_main) * 100))

        amount_main_word = currency.amount_to_text(amount_main)

        if self.site_id.tax_id.tax_group_id.name == 'TVA 0%':
            tax_indicator = "Hors Taxes"
        else:
            tax_indicator = "Toutes Taxes Comprises"

        if amount_cents > 0:
            cents_word = currency.amount_to_text(amount_cents)
            return f"{amount_main_word} et {cents_word} Centimes CFA {tax_indicator}"
        else:
            return f"{amount_main_word} et Zéro Centimes CFA {tax_indicator}"

    def print_decompte(self):
        return self.env.ref('building.decompte_client_action').report_action(self)

    def print_decompte_provisional_report(self):
        data = self.generate_data()
        # raise Exception(data)
        return self.env.ref('accounting.decompte_provisional_report_action').report_action(self, data={'data': data})
    
    def test(self):
        self.write({'state': 'draft'})
    
    def generate_data(self):
        data = []
        for rec in self:
            # prc_advance = round((rec.amount_advance_ttc / rec.accumulations_work) * 100, 4) if rec.accumulations_work else 0
            # prc_deduction_malus_retention = round((rec.deduction_malus_retention / rec.accumulations_work) * 100, 4) if rec.accumulations_work else 0
            # prc_amount_ten_year_ttc = round((rec.amount_ten_year_ttc / rec.accumulations_work) * 100, 4) if rec.accumulations_work else 0

            deduction_prc_gr = round(rec.deduction_prc_gr, 2)
            deduction_advance = round(rec.deduction_advance, 2)
            deduction_ten_year_ttc = round(rec.deduction_ten_year_ttc, 2)
            # deduction_malus_retention = round(rec.deduction_malus_retention, 2)
            # deduction_all_risk_insurance = round(rec.deduction_all_risk_insurance, 2)

            total_to_deduct = round(
                deduction_prc_gr + deduction_advance + deduction_ten_year_ttc,
                # + deduction_malus_retention + deduction_all_risk_insurance,
                2
            )

            # amount_remaining_fcfa_excl_tax = round(rec.accumulations_work - total_to_deduct, 2)
            amount = rec.net_amount_to_be_invoiced
            amount_expected_revenue = 0

            if rec.site_id.tax_id.tax_group_id.name != 'TVA 0%':
                amount_expected_revenue = rec.site_id.expected_revenue * (1 + rec.site_id.tax_id.amount / 100)

            data.append({
                'site_id': rec.site_id.name,
                'opp_id': rec.site_id.opp_id.name,
                'expected_revenue': amount_expected_revenue,
                'number': rec.number,
                'nature_service': rec.site_id.nature_service if rec.site_id.nature_service else "BORDEREAU DE PRIX",
                'end_date': rec.end_date.strftime('%d/%m/%y') if rec.end_date else False,
                'currency': rec.currency_id.name,
                'tax_group_id': rec.site_id.tax_id.tax_group_id.name,
                'accumulations_work': round(rec.amount_invoiced_ttc, 2),
                'deductions': {
                    'prc_rg': round(rec.prc_rg, 4),
                    'deduction_prc_gr': deduction_prc_gr,
                    # 'prc_advance': prc_advance,
                    'deduction_advance': deduction_advance,
                    # 'prc_deduction_malus_retention': prc_deduction_malus_retention,
                    # 'deduction_malus_retention': deduction_malus_retention,
                    # 'prc_amount_ten_year_ttc': prc_amount_ten_year_ttc,
                    'deduction_ten_year_ttc': deduction_ten_year_ttc,
                    # 'deduction_all_risk_insurance': deduction_all_risk_insurance,
                    'accumulation_previous_amounts': rec.accumulation_previous_amounts,
                },
                'total_to_deduct': total_to_deduct,
                'amount_remaining_fcfa_excl_tax': amount,
                'amount_in_word': rec.amount_remaining_in_word(amount),
                'company_id': {
                    'capital': rec.company_id.capital or 0,
                    'rccm': rec.company_id.rccm or '',
                    'niu_nemuro': rec.company_id.niu_nemuro or '',
                    'cnps': rec.company_id.cnps or '',
                    'street': rec.company_id.street or '',
                    'street2': rec.company_id.street2 or '',
                    'city': rec.company_id.city or '',
                    'country': rec.company_id.country_id.display_name if rec.company_id.country_id else '',
                    'phone': rec.company_id.phone or '',
                    'mobile': rec.company_id.mobile or '',
                    'email': rec.company_id.email or '',
                    'website': rec.company_id.website or '',
                    'bank_account': rec.company_id.bank_account or '',
                }
            })
        return data
