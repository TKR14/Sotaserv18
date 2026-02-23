# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


def _french_format(value):
    s = f"{value:.2f}"  
    integer, decimal = s.split(".")

    # insert spaces every 3 digits from the right
    integer = integer[::-1]
    integer = " ".join([integer[i:i+3] for i in range(0, len(integer), 3)])
    integer = integer[::-1]

    return f"{integer},{decimal}"


class account_move(models.Model):
    _inherit = "account.move"
    _description = "Journal Items"

    list_types_inv = [
        # ('inv_advance', 'Facture d\'Avance'),
        ('inv_attachment', 'Facture de Décompte'),
        # ('inv_rg', 'Facture de libération RG'),
        # ('inv_finish', 'Libération Autres Retenues'),
    ]

    site_id = fields.Many2one('building.site','Affaire')
    order_id = fields.Many2one('building.order','BP')
    type_op = fields.Selection([("stock", "Stock"), ("timesheet", "Temps de travail"), ('material','Fourniture'), ("subcontracting", "Sous-traitance"), ("workforce", "Main-d’œuvre"), ("equipment","Matériel"), ("load", "Charge"), ("production", "Production Entreprise"), ("purchase", "Achat"), ("service", "Service")], string="Type de lige",default='production')
    inv_type = fields.Selection(list_types_inv, string="Type de facture", help="Type de facture.")

    invoice_line_enter_ids = fields.One2many('account.move.line.enter', 'move_id', string='Lignes de facture',
        copy=False, readonly=False,
        states={'draft': [('readonly', False)]})

    amount_untaxed_before_deduction = fields.Monetary(string='Montant HT', store=True, readonly=True,
        compute='_compute_amount')

    amount_total_before_deduction = fields.Monetary(string='Total Travaux TTC', store=True, readonly=True,
        compute='_compute_amount')
    amount_tax_before_deduction = fields.Monetary(string='TVA', store=True, readonly=True,
        compute='_compute_amount')

    amount_deduction_gr = fields.Monetary(string='Déduction Retenue de Garantie')
    amount_advance_deduction = fields.Monetary(string='Déduction Avance')
    amount_all_risk_site_insurance_deduction = fields.Monetary(string='Déduction Assurance TRC')
    amount_prorata_account_deduction = fields.Monetary(string='Déduction Compte Prorata')
    amount_finish_deduction = fields.Monetary(string='Déduction Autres Retenue')
    amount_ten_year = fields.Monetary(string='Déduction Retenue Assurance décennale')


    is_caution_gr = fields.Boolean('Caution de Garantie ?', default=False)
    ref_caution_gr = fields.Char('Ref. Caution de Garantie')
    is_caution_advance = fields.Boolean('Caution Avance ?', default=False)
    ref_caution_advance = fields.Char('Ref. Caution Avance')
    is_caution_all_risk_site_insurance = fields.Boolean('Caution TRC ?', default=False)
    ref_caution_all_risk_site_insurance = fields.Char('Ref. Caution TRC')
    is_caution_prorata_account = fields.Boolean('Caution Compte Prorata ?', default=False)
    ref_caution_prorata_account = fields.Char('Ref. Caution Compte Prorata')
    is_caution_finish = fields.Boolean('Caution finition ?', default=False)
    ref_caution_finish = fields.Char('Ref. Caution finition')
    is_caution_ten_year = fields.Boolean('Caution Assurance décennale ?', default=False)
    ref_caution_ten_year = fields.Char('Ref. Caution Assurance décennale')

    prc_gr = fields.Float('Retenue de Garantie')
    prc_advance_deduction = fields.Float('Déduction Avance')
    prc_all_risk_site_insurance = fields.Float('Déduction TRC')
    prc_prorata_account = fields.Float('Déduction Compte Prorata')
    prc_ten_year = fields.Float('Assurance décennale')
    prc_finish = fields.Float('Déduction Autres Retenue')
    prc_malus_retention = fields.Float('Retenue de malfaçons')

    cumul_amount_untaxed = fields.Monetary('Montant HT', store=False, readonly=True, compute='_compute_cumul_amount')
    cumul_amount_untaxed_after_ded_ret = fields.Monetary('Montant HT Apres Retenues', store=False, readonly=True, compute='_compute_cumul_amount')
    # cumul_amount_previous_inv_attachment_deduction = fields.Monetary(string='Déduction décompte précedent')
    cumul_amount_untaxed_after_ded_prev_inv = fields.Monetary('Montant HT', store=False, readonly=True, compute='_compute_cumul_amount')
    cumul_amount_tax = fields.Monetary('Montant TVA', store=False, readonly=True, compute='_compute_cumul_amount')
    cumul_amount_total = fields.Monetary('Montant TTC', store=False, readonly=True, compute='_compute_cumul_amount')
    
    prev_amount_deduction_gr = fields.Monetary(string='Déduction Retenue de Garantie')
    prev_amount_advance_deduction = fields.Monetary(string='Déduction Amortissement Avance')
    prev_amount_all_risk_site_insurance_deduction = fields.Monetary(string='Déduction assurance TRC')
    prev_amount_prorata_account_deduction = fields.Monetary(string='Déduction Compte Prorata')
    prev_amount_previous_inv_attachment_deduction = fields.Monetary(string='Déduction décompte précedent')
    prev_amount_finish_deduction = fields.Monetary(string='Déduction Retenue Finition')
    prev_amount_ten_year = fields.Monetary(string='Déduction Retenue Assurance décennale')
    
    # current_amount_deduction_gr = fields.Monetary(string='Déduction Retenue de Garantie')
    # current_amount_advance_deduction = fields.Monetary(string='Déduction Amortissement Avance')
    # current_amount_all_risk_site_insurance_deduction = fields.Monetary(string='Déduction assurance TRC')
    # current_amount_prorata_account_deduction = fields.Monetary(string='Déduction Compte Prorata')
    # current_amount_previous_inv_attachment_deduction = fields.Monetary(string='Déduction décompte précedent')
    # current_amount_finish_deduction = fields.Monetary(string='Déduction Retenue Finition')
    # current_amount_ten_year = fields.Monetary(string='Déduction Retenue Assurance décennale')

    cumul_amount_deduction_gr = fields.Monetary(string='Déduction Retenue de Garantie', store=False, readonly=True, compute='_compute_cumul_amount')
    cumul_amount_advance_deduction = fields.Monetary(string='Déduction Amortissement Avance', store=False, readonly=True, compute='_compute_cumul_amount')
    cumul_amount_all_risk_site_insurance_deduction = fields.Monetary(string='Déduction assurance TRC', store=False, readonly=True, compute='_compute_cumul_amount')
    cumul_amount_prorata_account_deduction = fields.Monetary(string='Déduction Compte Prorata', store=False, readonly=True, compute='_compute_cumul_amount')
    cumul_amount_finish_deduction = fields.Monetary(string='Déduction Retenue Finition', store=False, readonly=True, compute='_compute_cumul_amount')
    cumul_amount_ten_year = fields.Monetary(string='Déduction Retenue Assurance décennale', store=False, readonly=True, compute='_compute_cumul_amount')

    contract_ref = fields.Char('Ref. Contrat')
    vehicle_id =  fields.Many2one('fleet.vehicle', string='IG')

    def confirm_delete_invoice(self):
        self.browse(self.env.context.get("to_delete")).unlink()

    def delete_invoice(self):
        deletable = all(
            (
                (move.move_type == "in_invoice" and move.move_type_type == "manual" and move.state == "draft")
                or
                (move.move_type == "out_invoice" and move.move_type_type == "manual" and move.out_state == "draft")
            )
            and not move.posted_before
            for move in self
        )
        if not deletable:
            raise ValidationError("Vous ne pouvez supprimer que les factures brouillons qui n'ont jamais été comptabilisées.")
        return {
            "name": "Confirmation",
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self[0].id,
            "view_mode": "form",
            "view_id": self.env.ref("building.account_move_view_form_confirm_invoice_delete").id,
            "target": "new",
            "context": {
                "to_delete": self.ids,
            },
        }

    @api.onchange('is_caution_gr')
    def _onchange_is_caution_gr(self):
        if self.is_caution_gr:
            self.prc_gr = 0
            self.amount_deduction_gr = 0
            self._onchange_invoice_line_enter_ids()

    @api.onchange('is_caution_advance')
    def _onchange_is_caution_advance(self):
        if self.is_caution_advance:
            self.prc_advance_deduction = 0
            self.amount_advance_deduction = 0
            self._onchange_invoice_line_enter_ids()

    @api.onchange('is_caution_all_risk_site_insurance')
    def _onchange_is_caution_all_risk_site_insurance(self):
        if self.is_caution_all_risk_site_insurance:
            self.prc_all_risk_site_insurance = 0
            self.amount_all_risk_site_insurance_deduction = 0
            self._onchange_invoice_line_enter_ids()

    @api.onchange('is_caution_prorata_account')
    def _onchange_is_caution_prorata_account(self):
        if self.is_caution_prorata_account:
            self.prc_prorata_account = 0
            self.amount_prorata_account_deduction = 0
            self._onchange_invoice_line_enter_ids()

    @api.onchange('is_caution_finish')
    def _onchange_is_caution_finish(self):
        if self.is_caution_finish:
            self.prc_finish = 0
            self.amount_finish_deduction = 0
            self._onchange_invoice_line_enter_ids()

    @api.onchange('is_caution_ten_year')
    def _onchange_is_caution_ten_year(self):
        if self.is_caution_ten_year:
            self.prc_ten_year = 0
            self.amount_ten_year = 0
            self._onchange_invoice_line_enter_ids()

    @api.depends(
        'invoice_line_enter_ids',
        'prev_amount_deduction_gr',
        'prev_amount_advance_deduction',
        'prev_amount_all_risk_site_insurance_deduction',
        'prev_amount_prorata_account_deduction',
        'prev_amount_previous_inv_attachment_deduction',
        'prev_amount_finish_deduction',
        'prev_amount_ten_year',
        'amount_deduction_gr',
        'amount_advance_deduction',
        'amount_all_risk_site_insurance_deduction',
        'amount_prorata_account_deduction',
        'amount_finish_deduction',
        'amount_ten_year',
        )
    def _compute_cumul_amount(self):
        for move in self:
            move.cumul_amount_untaxed = sum(line.cumulative_price_subtotal for line in move.invoice_line_enter_ids)
            last_inv = self.env['account.move'].search([('id', '!=', move._origin.id), ('id', '<', move._origin.id), ('inv_type', '=', 'inv_attachment'), ('site_id', '=', move.site_id.id), ('move_type', '=', 'out_invoice')], order='id DESC', limit=1)
            
            current_amount_deduction_gr = move.amount_deduction_gr/1.2
            current_amount_advance_deduction = move.amount_advance_deduction/1.2
            current_amount_all_risk_site_insurance_deduction = move.amount_all_risk_site_insurance_deduction/1.2
            current_amount_prorata_account_deduction = move.amount_prorata_account_deduction/1.2
            current_amount_finish_deduction = move.amount_finish_deduction/1.2
            current_amount_ten_year = move.amount_ten_year/1.2

            if last_inv:
                move.prev_amount_deduction_gr = last_inv.cumul_amount_deduction_gr
                move.prev_amount_advance_deduction = last_inv.cumul_amount_advance_deduction
                move.prev_amount_all_risk_site_insurance_deduction = last_inv.cumul_amount_all_risk_site_insurance_deduction
                move.prev_amount_prorata_account_deduction = last_inv.cumul_amount_prorata_account_deduction
                move.prev_amount_finish_deduction = last_inv.cumul_amount_finish_deduction
                move.prev_amount_ten_year = last_inv.cumul_amount_ten_year
                move.prev_amount_previous_inv_attachment_deduction = last_inv.cumul_amount_untaxed_after_ded_prev_inv + last_inv.prev_amount_previous_inv_attachment_deduction

            # current_amount_deduction_gr -= move.prev_amount_deduction_gr
            # current_amount_advance_deduction -= move.prev_amount_advance_deduction
            # current_amount_all_risk_site_insurance_deduction -= move.prev_amount_all_risk_site_insurance_deduction
            # current_amount_prorata_account_deduction -= move.prev_amount_prorata_account_deduction
            # current_amount_finish_deduction -= move.prev_amount_finish_deduction
            # current_amount_ten_year -= move.prev_amount_ten_year

            move.cumul_amount_deduction_gr = current_amount_deduction_gr + move.prev_amount_deduction_gr
            move.cumul_amount_advance_deduction = current_amount_advance_deduction + move.prev_amount_advance_deduction
            move.cumul_amount_all_risk_site_insurance_deduction = current_amount_all_risk_site_insurance_deduction + move.prev_amount_all_risk_site_insurance_deduction
            move.cumul_amount_prorata_account_deduction = current_amount_prorata_account_deduction + move.prev_amount_prorata_account_deduction
            move.cumul_amount_finish_deduction = current_amount_finish_deduction + move.prev_amount_finish_deduction
            move.cumul_amount_ten_year = current_amount_ten_year + move.prev_amount_ten_year

            move.cumul_amount_untaxed_after_ded_ret = move.cumul_amount_untaxed - (move.cumul_amount_deduction_gr + move.cumul_amount_advance_deduction + move.cumul_amount_all_risk_site_insurance_deduction + move.cumul_amount_prorata_account_deduction + move.cumul_amount_ten_year)
            move.cumul_amount_untaxed_after_ded_prev_inv = move.cumul_amount_untaxed_after_ded_ret - move.prev_amount_previous_inv_attachment_deduction
            move.cumul_amount_tax = sum((line.tax_line_id.amount*move.cumul_amount_untaxed_after_ded_prev_inv/100 for line in move.line_ids if line.tax_line_id), 0.0)
            move.cumul_amount_total = move.cumul_amount_untaxed_after_ded_prev_inv + move.cumul_amount_tax

    @api.onchange("site_id")
    def _onchange_site(self):
        if self.site_id and self.move_type == "out_invoice":
            pass
            # site = self.site_id
            # site._compute_sum_prc()
            # self.prc_gr = (site.expected_revenue * site.prc_gr / 100) - site.sum_prc_gr
            # self.prc_advance_deduction = site.prc_advance_deduction - site.sum_prc_advance_deduction
            # self.prc_ten_year = site.prc_ten_year - site.sum_prc_ten_year
            # self.prc_all_risk_site_insurance = self.site_id.prc_all_risk_site_insurance
            # self.prc_prorata_account = self.site_id.prc_prorata_account
            # self.prc_finish = self.site_id.prc_finish

    @api.constrains("prc_gr", "prc_advance_deduction", "prc_ten_year")
    def _check_prc(self):
        for move in self:
            if move.site_id and move.move_type == "out_invoice":
                site = move.site_id
                site._compute_sum_prc(exclude_me=move.id)
                remaining_prc_gr = (site.expected_revenue * site.prc_gr / 100) - site.sum_prc_gr
                remaining_prc_advance_deduction = site.prc_advance_deduction - site.sum_prc_advance_deduction
                remaining_prc_ten_year = site.prc_ten_year - site.sum_prc_ten_year

                if move.prc_gr > remaining_prc_gr:
                    raise ValidationError(f"La retenue de garantie ne peut pas être supérieure à {_french_format(remaining_prc_gr)}.")
                if move.prc_advance_deduction > remaining_prc_advance_deduction:
                    raise ValidationError(f"La déduction avance ne peut pas être supérieure à {_french_format(remaining_prc_advance_deduction)}.")
                if move.prc_ten_year > remaining_prc_ten_year:
                    raise ValidationError(f"La retenue assurance décennale ne peut pas être supérieure à {_french_format(remaining_prc_ten_year)}.")

    @api.onchange('invoice_line_enter_ids',
        'amount_deduction_gr',
        'amount_advance_deduction',
        'amount_all_risk_site_insurance_deduction',
        'amount_prorata_account_deduction',
        'amount_finish_deduction',
        'amount_ten_year',
        'invoice_date')
    def _onchange_invoice_line_enter_ids(self):
        if self.invoice_line_enter_ids:
            lines = []
            self.invoice_line_ids = [(6, 0, [])]
            self.invoice_line_enter_ids._onchange_quantity_price_unit()
            for line in self.invoice_line_enter_ids:
                if line.price_unit > 0:
                    lines.append((0,0,{
                            'product_id': line.product_id.id if line.product_id else False,
                            'name': line.name,
                            'account_id': line.account_id.id if line.account_id else False,
                            'quantity':line.quantity,
                            'price_unit':line.price_unit,
                            'tax_ids':line.tax_ids.ids if line.tax_ids else False,
                            'currency_id':self.currency_id.id,
                            'cumulative_quantity':line.cumulative_quantity,
                            'quantity_counts_previous':line.quantity_counts_previous,
                            'current_count_quantity':line.current_count_quantity,
                            'current_price_unit':line.price_unit,
                            'cumulative_price_unit': line.price_unit,
                            'previous_price_unit': line.price_unit,
                            # 'quantity': line.current_count_quantity
                        }))
            self.invoice_line_ids = lines
            self.invoice_line_ids._onchange_price_subtotal()
            self._onchange_invoice_line_ids()

    def _upsert_lines_accounting_customer(self, move_type):
        self.line_ids.filtered(lambda x: x.is_building_specific == True).unlink()

        account_advance = self.env['account.account'].search([('code', '=', '44210000')])
        line_adv = self.line_ids.filtered(lambda x: x.account_id.code == '44210000')
        prc_advance_deduction_amount = self.currency_id._convert(self.amount_advance_deduction, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if prc_advance_deduction_amount > 0:
            if line_adv:
                line_adv.is_building_specific = True
                line_adv.debit = prc_advance_deduction_amount if move_type == 'out_invoice' else 0
                line_adv.credit = prc_advance_deduction_amount if move_type == 'out_refund' else 0
            else:
                record_line = {
                    'account_id': account_advance.id,
                    'name':account_advance.name,
                    'quantity':1,
                    'price_unit':prc_advance_deduction_amount,
                    'debit':prc_advance_deduction_amount if move_type == 'out_invoice' else 0,
                    'credit':prc_advance_deduction_amount if move_type == 'out_refund' else 0,
                    'move_id': self.id,
                    'exclude_from_invoice_tab':True,
                    'is_building_specific':True,
                    'currency_id': self.currency_id.id
                }
                if isinstance(self.id, models.NewId):
                    self.env['account.move.line'].new(record_line)
                else:
                    self.env['account.move.line'].create(record_line)

        # account_advance_ded_tax = self.env['account.account'].search([('code', '=', '44555000')])
        # line_adv_ded_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44555000')
        # prc_advance_deduction = self.amount_advance_deduction/6 if self.amount_tax_before_deduction > 0 else 0
        # prc_advance_deduction = self.currency_id._convert(prc_advance_deduction, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        # if line_adv_ded_tax:
        #     line_adv_ded_tax.is_building_specific = True
        #     line_adv_ded_tax.credit = prc_advance_deduction if move_type == 'out_invoice' else 0
        #     line_adv_ded_tax.debit = prc_advance_deduction if move_type == 'out_refund' else 0
        # else:
        #     record_line = {
        #         'account_id': account_advance_ded_tax.id,
        #         'name':account_advance_ded_tax.name,
        #         'quantity':1,
        #         'price_unit':prc_advance_deduction,
        #         'debit':prc_advance_deduction if move_type == 'out_refund' else 0,
        #         'credit':prc_advance_deduction if move_type == 'out_invoice' else 0,
        #         'move_id': self.id,
        #         'exclude_from_invoice_tab':True,
        #         'is_building_specific':True,
        #         'currency_id': self.currency_id.id
        #     }
        #     if isinstance(self.id, models.NewId):
        #         self.env['account.move.line'].new(record_line)
        #     else:
        #         self.env['account.move.line'].create(record_line)


        account_gr_ded = self.env['account.account'].search([('code', '=', '34230000')])
        line_gr_ded = self.line_ids.filtered(lambda x: x.account_id.code == '34230000')
        # prc_gr_amount = line_product_credit*(self.prc_gr/100)*1.2
        prc_gr_amount = self.currency_id._convert(self.amount_deduction_gr, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if prc_gr_amount > 0:
            if line_gr_ded:
                line_gr_ded.is_building_specific = True
                line_gr_ded.debit = prc_gr_amount if move_type == 'out_invoice' else 0
                line_gr_ded.credit = prc_gr_amount if move_type == 'out_refund' else 0
            else:
                record_line = {
                    'account_id': account_gr_ded.id,
                    'name':account_gr_ded.name,
                    'quantity':1,
                    'price_unit':prc_gr_amount,
                    'debit':prc_gr_amount if move_type == 'out_invoice' else 0,
                    'credit':prc_gr_amount if move_type == 'out_refund' else 0,
                    'move_id': self.id,
                    'exclude_from_invoice_tab':True,
                    'is_building_specific':True,
                    'currency_id': self.currency_id.id
                }
                if isinstance(self.id, models.NewId):
                    self.env['account.move.line'].new(record_line)
                else:
                    self.env['account.move.line'].create(record_line)

        # account_gr_ded_tax = self.env['account.account'].search([('code', '=', '44553000')])
        # line_gr_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44553000')
        # prc_gr = self.amount_deduction_gr/6 if self.amount_tax_before_deduction > 0 else 0
        # prc_gr = self.currency_id._convert(prc_gr, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        # if line_gr_tax:
        #     line_gr_tax.is_building_specific = True
        #     line_gr_tax.credit = prc_gr if move_type == 'out_invoice' else 0
        #     line_gr_tax.debit = prc_gr if move_type == 'out_refund' else 0
        # else:
        #     record_line = {
        #         'account_id': account_gr_ded_tax.id,
        #         'name':account_gr_ded_tax.name,
        #         'quantity':1,
        #         'price_unit':prc_gr,
        #         'move_id': self.id,
        #         'debit':prc_gr if move_type == 'out_refund' else 0,
        #         'credit':prc_gr if move_type == 'out_invoice' else 0,
        #         'exclude_from_invoice_tab':True,
        #         'is_building_specific':True,
        #         'currency_id': self.currency_id.id
        #     }
        #     if isinstance(self.id, models.NewId):
        #         self.env['account.move.line'].new(record_line)
        #     else:
        #         self.env['account.move.line'].create(record_line)


        account_prorata_account_ded = self.env['account.account'].search([('code', '=', '34886000')])
        line_prorata_account_ded = self.line_ids.filtered(lambda x: x.account_id.code == '34886000')
        prc_prorata_account_amount = self.currency_id._convert(self.amount_prorata_account_deduction, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if prc_prorata_account_amount > 0:
            if line_prorata_account_ded:
                line_prorata_account_ded.is_building_specific = True
                line_prorata_account_ded.debit = prc_prorata_account_amount if move_type == 'out_invoice' else 0
                line_prorata_account_ded.credit = prc_prorata_account_amount if move_type == 'out_refund' else 0
            else:
                record_line = {
                    'account_id': account_prorata_account_ded.id,
                    'name':account_prorata_account_ded.name,
                    'quantity':1,
                    'price_unit':prc_prorata_account_amount,
                    'debit':prc_prorata_account_amount if move_type == 'out_invoice' else 0,
                    'credit':prc_prorata_account_amount if move_type == 'out_refund' else 0,
                    'move_id': self.id,
                    'exclude_from_invoice_tab':True,
                    'is_building_specific':True,
                    'currency_id': self.currency_id.id
                }
                if isinstance(self.id, models.NewId):
                    self.env['account.move.line'].new(record_line)
                else:
                    self.env['account.move.line'].create(record_line)

        # account_prorata_account_ded_tax = self.env['account.account'].search([('code', '=', '44554600')])
        # line_prorata_account_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44554600')
        # prc_prorata_account = self.amount_prorata_account_deduction/6 if self.amount_tax_before_deduction > 0 else 0
        # prc_prorata_account = self.currency_id._convert(prc_prorata_account, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        # if line_prorata_account_tax:
        #     line_prorata_account_tax.is_building_specific = True
        #     line_prorata_account_tax.credit = prc_prorata_account if move_type == 'out_invoice' else 0
        #     line_prorata_account_tax.debit = prc_prorata_account if move_type == 'out_refund' else 0
        # else:
        #     record_line = {
        #         'account_id': account_prorata_account_ded_tax.id,
        #         'name':account_prorata_account_ded_tax.name,
        #         'quantity':1,
        #         'price_unit':prc_prorata_account,
        #         'debit':prc_prorata_account if move_type == 'out_refund' else 0,
        #         'credit':prc_prorata_account if move_type == 'out_invoice' else 0,
        #         'move_id': self.id,
        #         'exclude_from_invoice_tab':True,
        #         'is_building_specific':True,
        #         'currency_id': self.currency_id.id
        #     }
        #     if isinstance(self.id, models.NewId):
        #         self.env['account.move.line'].new(record_line)
        #     else:
        #         self.env['account.move.line'].create(record_line)


        account_all_risk_site_insurance_ded = self.env['account.account'].search([('code', '=', '34887000')])
        line_all_risk_site_insurance_ded = self.line_ids.filtered(lambda x: x.account_id.code == '34887000')
        prc_all_risk_site_insurance_amount = self.currency_id._convert(self.amount_all_risk_site_insurance_deduction, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if prc_all_risk_site_insurance_amount > 0:
            if line_all_risk_site_insurance_ded:
                line_all_risk_site_insurance_ded.is_building_specific = True
                line_all_risk_site_insurance_ded.debit = prc_all_risk_site_insurance_amount if move_type == 'out_invoice' else 0
                line_all_risk_site_insurance_ded.credit = prc_all_risk_site_insurance_amount if move_type == 'out_refund' else 0
            else:
                record_line = {
                    'account_id': account_all_risk_site_insurance_ded.id,
                    'name':account_all_risk_site_insurance_ded.name,
                    'quantity':1,
                    'price_unit':prc_all_risk_site_insurance_amount,
                    'debit':prc_all_risk_site_insurance_amount if move_type == 'out_invoice' else 0,
                    'credit':prc_all_risk_site_insurance_amount if move_type == 'out_refund' else 0,
                    'move_id': self.id,
                    'exclude_from_invoice_tab':True,
                    'is_building_specific':True,
                    'currency_id': self.currency_id.id
                }
                if isinstance(self.id, models.NewId):
                    self.env['account.move.line'].new(record_line)
                else:
                    self.env['account.move.line'].create(record_line)

        # account_all_risk_site_insurance_ded_tax = self.env['account.account'].search([('code', '=', '44554700')])
        # line_all_risk_site_insurance_ded_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44554700')
        # prc_all_risk_site_insurance = self.amount_all_risk_site_insurance_deduction/6 if self.amount_tax_before_deduction > 0 else 0
        # prc_all_risk_site_insurance = self.currency_id._convert(prc_all_risk_site_insurance, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        # if line_all_risk_site_insurance_ded_tax:
        #     line_all_risk_site_insurance_ded_tax.is_building_specific = True
        #     line_all_risk_site_insurance_ded_tax.credit = prc_all_risk_site_insurance if move_type == 'out_invoice' else 0
        #     line_all_risk_site_insurance_ded_tax.debit = prc_all_risk_site_insurance if move_type == 'out_refund' else 0
        # else:
        #     record_line = {
        #         'account_id': account_all_risk_site_insurance_ded_tax.id,
        #         'name':account_all_risk_site_insurance_ded_tax.name,
        #         'quantity':1,
        #         'price_unit':prc_all_risk_site_insurance,
        #         'debit':prc_all_risk_site_insurance if move_type == 'out_refund' else 0,
        #         'credit':prc_all_risk_site_insurance if move_type == 'out_invoice' else 0,
        #         'move_id': self.id,
        #         'exclude_from_invoice_tab':True,
        #         'is_building_specific':True,
        #         'currency_id': self.currency_id.id
        #     }
        #     if isinstance(self.id, models.NewId):
        #         self.env['account.move.line'].new(record_line)
        #     else:
        #         self.env['account.move.line'].create(record_line)

        account_other_ded = self.env['account.account'].search([('code', '=', '34889000')])
        line_other_ded = self.line_ids.filtered(lambda x: x.account_id.code == '34889000')
        other_ded_amount = self.currency_id._convert(self.amount_finish_deduction, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if other_ded_amount > 0:
            if line_other_ded:
                line_other_ded.is_building_specific = True
                line_other_ded.debit = other_ded_amount if move_type == 'out_invoice' else 0
                line_other_ded.credit = other_ded_amount if move_type == 'out_refund' else 0
            else:
                record_line = {
                    'account_id': account_other_ded.id,
                    'name':account_other_ded.name,
                    'quantity':1,
                    'price_unit':other_ded_amount,
                    'debit':other_ded_amount if move_type == 'out_invoice' else 0,
                    'credit':other_ded_amount if move_type == 'out_refund' else 0,
                    'move_id': self.id,
                    'exclude_from_invoice_tab':True,
                    'is_building_specific':True,
                    'currency_id': self.currency_id.id
                }
                if isinstance(self.id, models.NewId):
                    self.env['account.move.line'].new(record_line)
                else:
                    self.env['account.move.line'].create(record_line)

        # account_other_ded_tax = self.env['account.account'].search([('code', '=', '44554900')])
        # line_other_ded_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44554900')
        # amount_other_dec = self.amount_finish_deduction/6 if self.amount_tax_before_deduction > 0 else 0
        # amount_other_dec = self.currency_id._convert(amount_other_dec, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        # if line_other_ded_tax:
        #     line_other_ded_tax.is_building_specific = True
        #     line_other_ded_tax.credit = amount_other_dec if move_type == 'out_invoice' else 0
        #     line_other_ded_tax.debit = amount_other_dec if move_type == 'out_refund' else 0
        # else:
        #     record_line = {
        #         'account_id': account_other_ded_tax.id,
        #         'name':account_other_ded_tax.name,
        #         'quantity':1,
        #         'price_unit':amount_other_dec,
        #         'debit':amount_other_dec if move_type == 'out_refund' else 0,
        #         'credit':amount_other_dec if move_type == 'out_invoice' else 0,
        #         'move_id': self.id,
        #         'exclude_from_invoice_tab':True,
        #         'is_building_specific':True,
        #         'currency_id': self.currency_id.id
        #     }
        #     if isinstance(self.id, models.NewId):
        #         self.env['account.move.line'].new(record_line)
        #     else:
        #         self.env['account.move.line'].create(record_line)


        account_ten_year_ded = self.env['account.account'].search([('code', '=', '34888000')])
        line_ten_year_ded = self.line_ids.filtered(lambda x: x.account_id.code == '34888000')
        ten_year_amount = self.currency_id._convert(self.amount_ten_year, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if ten_year_amount:
            if line_ten_year_ded:
                line_ten_year_ded.is_building_specific = True
                line_ten_year_ded.debit = ten_year_amount if move_type == 'out_invoice' else 0
                line_ten_year_ded.credit = ten_year_amount if move_type == 'out_refund' else 0
            else:
                record_line = {
                    'account_id': account_ten_year_ded.id,
                    'name':account_ten_year_ded.name,
                    'quantity':1,
                    'price_unit':ten_year_amount,
                    'debit':ten_year_amount if move_type == 'out_invoice' else 0,
                    'credit':ten_year_amount if move_type == 'out_refund' else 0,
                    'move_id': self.id,
                    'exclude_from_invoice_tab':True,
                    'is_building_specific':True,
                    'currency_id': self.currency_id.id
                }
                if isinstance(self.id, models.NewId):
                    self.env['account.move.line'].new(record_line)
                else:
                    self.env['account.move.line'].create(record_line)

        # account_ten_year_ded_tax = self.env['account.account'].search([('code', '=', '44554800')])
        # line_ten_year_ded_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44554800')
        # amount_ten_year_ded_tax = self.amount_ten_year/6 if self.amount_tax_before_deduction > 0 else 0
        # amount_ten_year_ded_tax = self.currency_id._convert(amount_ten_year_ded_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        # if line_ten_year_ded_tax:
        #     line_other_ded_tax.is_building_specific = True
        #     line_other_ded_tax.credit = amount_ten_year_ded_tax if move_type == 'out_invoice' else 0
        #     line_other_ded_tax.debit = amount_ten_year_ded_tax if move_type == 'out_refund' else 0
        # else:
        #     record_line = {
        #         'account_id': account_ten_year_ded_tax.id,
        #         'name':account_ten_year_ded_tax.name,
        #         'quantity':1,
        #         'price_unit':amount_ten_year_ded_tax,
        #         'debit':amount_ten_year_ded_tax if move_type == 'out_refund' else 0,
        #         'credit':amount_ten_year_ded_tax if move_type == 'out_invoice' else 0,
        #         'move_id': self.id,
        #         'exclude_from_invoice_tab':True,
        #         'is_building_specific':True,
        #         'currency_id': self.currency_id.id
        #     }
        #     if isinstance(self.id, models.NewId):
        #         self.env['account.move.line'].new(record_line)
        #     else:
        #         self.env['account.move.line'].create(record_line)
        
        # line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44552000')
        # if line_tax:
        #     line_tax.credit = self.currency_id._convert(self.amount_tax_before_deduction, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))- (prc_advance_deduction + prc_gr + prc_prorata_account + prc_all_risk_site_insurance + amount_other_dec + amount_ten_year_ded_tax) if move_type == 'out_invoice' else 0
        #     line_tax.debit = self.currency_id._convert(self.amount_tax_before_deduction, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))- (prc_advance_deduction + prc_gr + prc_prorata_account + prc_all_risk_site_insurance + amount_other_dec + amount_ten_year_ded_tax) if move_type == 'out_refund' else 0

        line_clt = self.line_ids.filtered(lambda x: x.account_id.code == '34211000')
        if line_clt:
            line_clt.debit = self.currency_id._convert(self.amount_total_before_deduction, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))- (prc_advance_deduction_amount + prc_gr_amount + prc_prorata_account_amount + prc_all_risk_site_insurance_amount + other_ded_amount + ten_year_amount) if move_type == 'out_invoice' else 0
            line_clt.credit = self.currency_id._convert(self.amount_total_before_deduction, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))- (prc_advance_deduction_amount + prc_gr_amount + prc_prorata_account_amount + prc_all_risk_site_insurance_amount + other_ded_amount + ten_year_amount) if move_type == 'out_refund' else 0


        # account_advance_ded_tax = self.env['account.account'].search([('code', '=', '44555000')])
        # record_line = {
        #     'account_id': account_advance_ded_tax.id,
        #     'name':account_advance_ded_tax.name,
        #     'quantity':1,
        #     'price_unit':prc_advance_deduction,
        #     'debit':prc_advance_deduction if move_type == 'out_invoice' else 0,
        #     'credit':prc_advance_deduction if move_type == 'out_refund' else 0,
        #     'move_id': self.id,
        #     'exclude_from_invoice_tab':True,
        #     'is_building_specific':True,
        #     'currency_id': self.currency_id.id
        # }
        # if isinstance(self.id, models.NewId):
        #     self.env['account.move.line'].new(record_line)
        # else:
        #     self.env['account.move.line'].create(record_line)

        # account_advance_regul_tax = self.env['account.account'].search([('code', '=', '34580000')])
        # record_line = {
        #     'account_id': account_advance_regul_tax.id,
        #     'name':account_advance_regul_tax.name,
        #     'quantity':1,
        #     'price_unit':prc_advance_deduction,
        #     'debit':prc_advance_deduction if move_type == 'out_refund' else 0,
        #     'credit':prc_advance_deduction if move_type == 'out_invoice' else 0,
        #     'move_id': self.id,
        #     'exclude_from_invoice_tab':True,
        #     'is_building_specific':True,
        #     'currency_id': self.currency_id.id
        # }
        # if isinstance(self.id, models.NewId):
        #     self.env['account.move.line'].new(record_line)
        # else:
        #     self.env['account.move.line'].create(record_line)

    def _upsert_lines_accounting_supplier(self, move_type):
        self.line_ids.filtered(lambda x: x.is_building_specific == True).unlink()
        record_lines = []
        move_lines = []
        account_advance = self.env['account.account'].search([('code', '=', '34110000')])
        line_adv = self.line_ids.filtered(lambda x: x.account_id.code == '34110000')
        amount_advance_deduction = self.currency_id._convert(self.amount_advance_deduction, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if amount_advance_deduction > 0:
            if line_adv:
                line_adv.is_building_specific = True
                line_adv.debit = amount_advance_deduction if move_type == 'in_refund' else 0
                line_adv.credit = amount_advance_deduction if move_type == 'in_invoice' else 0
            else:
                record_line = {
                    'account_id': account_advance.id,
                    'name':account_advance.name,
                    # 'quantity':1,
                    'price_unit':self.amount_advance_deduction,
                    'debit':amount_advance_deduction if move_type == 'in_refund' else 0,
                    'credit':amount_advance_deduction if move_type == 'in_invoice' else 0,
                    'move_id': self.id,
                    'exclude_from_invoice_tab':True,
                    'is_building_specific':True,
                    'currency_id': self.currency_id.id,
                }
                if isinstance(self.id, models.NewId):
                    self.env['account.move.line'].new(record_line)
                else:
                    self.env['account.move.line'].create(record_line)



        # account_advance_ded_tax = self.env['account.account'].search([('code', '=', '34552600')])
        # line_adv_ded_tax = self.line_ids.filtered(lambda x: x.account_id.code == '34552600')
        # amount_advance_ded_tax = self.amount_advance_deduction/6 if self.amount_tax_before_deduction > 0 else 0
        # amount_advance_ded_tax = self.currency_id._convert(amount_advance_ded_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        # if line_adv_ded_tax:
        #     line_adv_ded_tax.is_building_specific = True
        #     line_adv_ded_tax.credit = amount_advance_ded_tax if move_type == 'in_refund' else 0
        #     line_adv_ded_tax.debit = amount_advance_ded_tax if move_type == 'in_invoice' else 0
        # else:
        #     record_line = {
        #         'account_id': account_advance_ded_tax.id,
        #         'name':account_advance_ded_tax.name,
        #         'quantity':1,
        #         'price_unit':amount_advance_ded_tax,
        #         'debit':amount_advance_ded_tax if move_type == 'in_invoice' else 0,
        #         'credit':amount_advance_ded_tax if move_type == 'in_refund' else 0,
        #         'move_id': self.id,
        #         'exclude_from_invoice_tab':True,
        #         'is_building_specific':True,
        #         'currency_id': self.currency_id.id,
        #         'currency_id': self.currency_id.id
        #     }
        #     if isinstance(self.id, models.NewId):
        #         self.env['account.move.line'].new(record_line)
        #     else:
        #         self.env['account.move.line'].create(record_line)


        account_gr_ded = self.env['account.account'].search([('code', '=', '44130000')])
        line_gr_ded = self.line_ids.filtered(lambda x: x.account_id.code == '44130000')
        amount_deduction_gr = self.currency_id._convert(self.amount_deduction_gr, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if amount_deduction_gr > 0:
            if line_gr_ded:
                line_gr_ded.is_building_specific = True
                line_gr_ded.debit = amount_deduction_gr if move_type == 'in_refund' else 0
                line_gr_ded.credit = amount_deduction_gr if move_type == 'in_invoice' else 0
            else:
                record_line = {
                    'account_id': account_gr_ded.id,
                    'name':account_gr_ded.name,
                    'quantity':1,
                    'price_unit':amount_deduction_gr,
                    'debit':amount_deduction_gr if move_type == 'in_refund' else 0,
                    'credit':amount_deduction_gr if move_type == 'in_invoice' else 0,
                    'move_id': self.id,
                    'exclude_from_invoice_tab':True,
                    'is_building_specific':True,
                    'currency_id': self.currency_id.id,
                    'currency_id': self.currency_id.id
                }
                if isinstance(self.id, models.NewId):
                    self.env['account.move.line'].new(record_line)
                else:
                    self.env['account.move.line'].create(record_line)

        # account_gr_ded_tax = self.env['account.account'].search([('code', '=', '34552550')])
        # line_gr_tax = self.line_ids.filtered(lambda x: x.account_id.code == '34552550')
        # amount_gr_tax_ded = self.amount_deduction_gr/6 if self.amount_tax_before_deduction > 0 else 0
        # amount_gr_tax_ded = self.currency_id._convert(amount_gr_tax_ded, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        # if line_gr_tax:
        #     line_gr_tax.is_building_specific = True
        #     line_gr_tax.credit = amount_gr_tax_ded if move_type == 'in_refund' else 0
        #     line_gr_tax.debit = amount_gr_tax_ded if move_type == 'in_invoice' else 0
        # else:
        #     record_line = {
        #         'account_id': account_gr_ded_tax.id,
        #         'name':account_gr_ded_tax.name,
        #         'quantity':1,
        #         'price_unit':amount_gr_tax_ded,
        #         'move_id': self.id,
        #         'debit':amount_gr_tax_ded if move_type == 'in_invoice' else 0,
        #         'credit':amount_gr_tax_ded if move_type == 'in_refund' else 0,
        #         'exclude_from_invoice_tab':True,
        #         'is_building_specific':True,
        #         'currency_id': self.currency_id.id
        #     }
        #     if isinstance(self.id, models.NewId):
        #         self.env['account.move.line'].new(record_line)
        #     else:
        #         self.env['account.move.line'].create(record_line)

        account_prorata_account_ded = self.env['account.account'].search([('code', '=', '44886000')])
        line_prorata_account_ded = self.line_ids.filtered(lambda x: x.account_id.code == '44886000')
        amount_prorata_account_deduction = self.currency_id._convert(self.amount_prorata_account_deduction, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if amount_prorata_account_deduction > 0:
            if line_prorata_account_ded:
                line_prorata_account_ded.is_building_specific = True
                line_prorata_account_ded.debit = amount_prorata_account_deduction if move_type == 'in_refund' else 0
                line_prorata_account_ded.credit = amount_prorata_account_deduction if move_type == 'in_invoice' else 0
            else:
                record_line = {
                    'account_id': account_prorata_account_ded.id,
                    'name':account_prorata_account_ded.name,
                    'quantity':1,
                    'price_unit':amount_prorata_account_deduction,
                    'debit':amount_prorata_account_deduction if move_type == 'in_refund' else 0,
                    'credit':amount_prorata_account_deduction if move_type == 'in_invoice' else 0,
                    'move_id': self.id,
                    'exclude_from_invoice_tab':True,
                    'is_building_specific':True,
                    'currency_id': self.currency_id.id
                }
                if isinstance(self.id, models.NewId):
                    self.env['account.move.line'].new(record_line)
                else:
                    self.env['account.move.line'].create(record_line)

        # account_prorata_account_ded_tax = self.env['account.account'].search([('code', '=', '34552560')])
        # line_prorata_account_tax = self.line_ids.filtered(lambda x: x.account_id.code == '34552560')
        # amount_prorata_account = self.amount_prorata_account_deduction/6 if self.amount_tax_before_deduction > 0 else 0
        # amount_prorata_account = self.currency_id._convert(amount_prorata_account, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        # if line_prorata_account_tax:
        #     line_prorata_account_tax.is_building_specific = True
        #     line_prorata_account_tax.credit = amount_prorata_account if move_type == 'in_refund' else 0
        #     line_prorata_account_tax.debit = amount_prorata_account if move_type == 'in_invoice' else 0
        # else:
        #     record_line = {
        #         'account_id': account_prorata_account_ded_tax.id,
        #         'name':account_prorata_account_ded_tax.name,
        #         'quantity':1,
        #         'price_unit':amount_prorata_account,
        #         'debit':amount_prorata_account if move_type == 'in_invoice' else 0,
        #         'credit':amount_prorata_account if move_type == 'in_refund' else 0,
        #         'move_id': self.id,
        #         'exclude_from_invoice_tab':True,
        #         'is_building_specific':True,
        #         'currency_id': self.currency_id.id
        #     }
        #     if isinstance(self.id, models.NewId):
        #         self.env['account.move.line'].new(record_line)
        #     else:
        #         self.env['account.move.line'].create(record_line)


        account_all_risk_site_insurance_ded = self.env['account.account'].search([('code', '=', '44887000')])
        line_all_risk_site_insurance_ded = self.line_ids.filtered(lambda x: x.account_id.code == '44887000')
        amount_all_risk_site_insurance_deduction = self.currency_id._convert(self.amount_all_risk_site_insurance_deduction, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if amount_all_risk_site_insurance_deduction > 0:
            if line_all_risk_site_insurance_ded:
                line_all_risk_site_insurance_ded.is_building_specific = True
                line_all_risk_site_insurance_ded.debit = amount_all_risk_site_insurance_deduction if move_type == 'in_refund' else 0
                line_all_risk_site_insurance_ded.credit = amount_all_risk_site_insurance_deduction if move_type == 'in_invoice' else 0
            else:
                record_line = {
                    'account_id': account_all_risk_site_insurance_ded.id,
                    'name':account_all_risk_site_insurance_ded.name,
                    'quantity':1,
                    'price_unit':amount_all_risk_site_insurance_deduction,
                    'debit':amount_all_risk_site_insurance_deduction if move_type == 'in_refund' else 0,
                    'credit':amount_all_risk_site_insurance_deduction if move_type == 'in_invoice' else 0,
                    'move_id': self.id,
                    'exclude_from_invoice_tab':True,
                    'is_building_specific':True,
                    'currency_id': self.currency_id.id
                }
                if isinstance(self.id, models.NewId):
                    self.env['account.move.line'].new(record_line)
                else:
                    self.env['account.move.line'].create(record_line)

        # account_all_risk_site_insurance_ded_tax = self.env['account.account'].search([('code', '=', '34552570')])
        # line_all_risk_site_insurance_ded_tax = self.line_ids.filtered(lambda x: x.account_id.code == '34552570')
        # amount_all_risk_site_insurance = self.amount_all_risk_site_insurance_deduction/6 if self.amount_tax_before_deduction > 0 else 0
        # amount_all_risk_site_insurance = self.currency_id._convert(amount_all_risk_site_insurance, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        # if line_all_risk_site_insurance_ded_tax:
        #     line_all_risk_site_insurance_ded_tax.is_building_specific = True
        #     line_all_risk_site_insurance_ded_tax.credit = amount_all_risk_site_insurance if move_type == 'in_refund' else 0
        #     line_all_risk_site_insurance_ded_tax.debit = amount_all_risk_site_insurance if move_type == 'in_invoice' else 0
        # else:
        #     record_line = {
        #         'account_id': account_all_risk_site_insurance_ded_tax.id,
        #         'name':account_all_risk_site_insurance_ded_tax.name,
        #         'quantity':1,
        #         'price_unit':amount_all_risk_site_insurance,
        #         'debit':amount_all_risk_site_insurance if move_type == 'in_invoice' else 0,
        #         'credit':amount_all_risk_site_insurance if move_type == 'in_refund' else 0,
        #         'move_id': self.id,
        #         'exclude_from_invoice_tab':True,
        #         'is_building_specific':True,
        #         'currency_id': self.currency_id.id
        #     }
        #     if isinstance(self.id, models.NewId):
        #         self.env['account.move.line'].new(record_line)
        #     else:
        #         self.env['account.move.line'].create(record_line)

        account_other_ded = self.env['account.account'].search([('code', '=', '44889000')])
        line_other_ded = self.line_ids.filtered(lambda x: x.account_id.code == '44889000')
        amount_finish_deduction = self.currency_id._convert(self.amount_finish_deduction, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if amount_finish_deduction > 0:
            if line_other_ded:
                line_other_ded.is_building_specific = True
                line_other_ded.debit = amount_finish_deduction if move_type == 'in_refund' else 0
                line_other_ded.credit = amount_finish_deduction if move_type == 'in_invoice' else 0
            else:
                record_line = {
                    'account_id': account_other_ded.id,
                    'name':account_other_ded.name,
                    'quantity':1,
                    'price_unit':amount_finish_deduction,
                    'debit':amount_finish_deduction if move_type == 'in_refund' else 0,
                    'credit':amount_finish_deduction if move_type == 'in_invoice' else 0,
                    'move_id': self.id,
                    'exclude_from_invoice_tab':True,
                    'is_building_specific':True,
                    'currency_id': self.currency_id.id
                }
                if isinstance(self.id, models.NewId):
                    self.env['account.move.line'].new(record_line)
                else:
                    self.env['account.move.line'].create(record_line)

        # account_other_ded_tax = self.env['account.account'].search([('code', '=', '34552590')])
        # line_other_ded_tax = self.line_ids.filtered(lambda x: x.account_id.code == '34552590')
        # amount_other_dec = self.amount_finish_deduction/6 if self.amount_tax_before_deduction > 0 else 0
        # amount_other_dec = self.currency_id._convert(amount_other_dec, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        # if line_other_ded_tax:
        #     line_other_ded_tax.is_building_specific = True
        #     line_other_ded_tax.credit = amount_other_dec if move_type == 'in_refund' else 0
        #     line_other_ded_tax.debit = amount_other_dec if move_type == 'in_invoice' else 0
        # else:
        #     record_line = {
        #         'account_id': account_other_ded_tax.id,
        #         'name':account_other_ded_tax.name,
        #         'quantity':1,
        #         'price_unit':amount_other_dec,
        #         'debit':amount_other_dec if move_type == 'in_invoice' else 0,
        #         'credit':amount_other_dec if move_type == 'in_refund' else 0,
        #         'move_id': self.id,
        #         'exclude_from_invoice_tab':True,
        #         'is_building_specific':True,
        #         'currency_id': self.currency_id.id
        #     }
        #     if isinstance(self.id, models.NewId):
        #         self.env['account.move.line'].new(record_line)
        #     else:
        #         self.env['account.move.line'].create(record_line)

        # record_line = {
        #     'account_id': account_advance_ded_tax.id,
        #     'name':account_advance_ded_tax.name,
        #     'quantity':1,
        #     'price_unit':amount_advance_ded_tax,
        #     'debit':amount_advance_ded_tax if move_type == 'in_refund' else 0,
        #     'credit':amount_advance_ded_tax if move_type == 'in_invoice' else 0,
        #     'move_id': self.id,
        #     'exclude_from_invoice_tab':True,
        #     'is_building_specific':True,
        #     'currency_id': self.currency_id.id
        # }
        # if isinstance(self.id, models.NewId):
        #     self.env['account.move.line'].new(record_line)
        # else:
        #     self.env['account.move.line'].create(record_line)

        # account_advance_regul_tax = self.env['account.account'].search([('code', '=', '44580000')])
        # record_line = {
        #     'account_id': account_advance_regul_tax.id,
        #     'name':account_advance_regul_tax.name,
        #     'quantity':1,
        #     'price_unit':amount_advance_ded_tax,
        #     'debit':amount_advance_ded_tax if move_type == 'in_invoice' else 0,
        #     'credit':amount_advance_ded_tax if move_type == 'in_refund' else 0,
        #     'move_id': self.id,
        #     'exclude_from_invoice_tab':True,
        #     'is_building_specific':True,
        #     'currency_id': self.currency_id.id
        # }
        # if isinstance(self.id, models.NewId):
        #     self.env['account.move.line'].new(record_line)
        # else:
        #     self.env['account.move.line'].create(record_line)

        account_ten_year_ded = self.env['account.account'].search([('code', '=', '44888000')])
        line_ten_year_ded = self.line_ids.filtered(lambda x: x.account_id.code == '44888000')
        amount_ten_year = self.currency_id._convert(self.amount_ten_year, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if amount_ten_year > 0:
            if line_ten_year_ded:
                line_ten_year_ded.is_building_specific = True
                line_ten_year_ded.debit = amount_ten_year if move_type == 'in_refund' else 0
                line_ten_year_ded.credit = amount_ten_year if move_type == 'in_invoice' else 0
            else:
                record_line = {
                    'account_id': account_ten_year_ded.id,
                    'name':account_ten_year_ded.name,
                    'quantity':1,
                    'price_unit':amount_ten_year,
                    'debit':amount_ten_year if move_type == 'in_refund' else 0,
                    'credit':amount_ten_year if move_type == 'in_invoice' else 0,
                    'move_id': self.id,
                    'exclude_from_invoice_tab':True,
                    'is_building_specific':True,
                    'currency_id': self.currency_id.id
                }
                if isinstance(self.id, models.NewId):
                    self.env['account.move.line'].new(record_line)
                else:
                    self.env['account.move.line'].create(record_line)

        # account_ten_year_ded_tax = self.env['account.account'].search([('code', '=', '34552580')])
        # line_ten_year_ded_tax = self.line_ids.filtered(lambda x: x.account_id.code == '34552580')
        # amount_ten_year_dec = self.amount_ten_year/6 if self.amount_tax_before_deduction > 0 else 0
        # amount_ten_year_dec = self.currency_id._convert(amount_ten_year_dec, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        # if line_ten_year_ded_tax:
        #     line_ten_year_ded_tax.is_building_specific = True
        #     line_ten_year_ded_tax.credit = amount_ten_year_dec if move_type == 'in_refund' else 0
        #     line_ten_year_ded_tax.debit = amount_ten_year_dec if move_type == 'in_invoice' else 0
        # else:
        #     record_line = {
        #         'account_id': account_ten_year_ded_tax.id,
        #         'name':account_ten_year_ded_tax.name,
        #         'quantity':1,
        #         'price_unit':amount_ten_year_dec,
        #         'debit':amount_ten_year_dec if move_type == 'in_invoice' else 0,
        #         'credit':amount_ten_year_dec if move_type == 'in_refund' else 0,
        #         'move_id': self.id,
        #         'exclude_from_invoice_tab':True,
        #         'is_building_specific':True,
        #         'currency_id': self.currency_id.id
        #     }
        #     if isinstance(self.id, models.NewId):
        #         self.env['account.move.line'].new(record_line)
        #     else:
        #         self.env['account.move.line'].create(record_line)

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        if self.move_type in ['out_invoice', 'in_invoice', 'out_refund', 'in_refund'] and self.invoice_line_enter_ids:
            if recompute_tax_base_amount:
                recompute_tax_base_amount = False
            self.line_ids = self.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)
            res = super(account_move, self)._recompute_dynamic_lines(recompute_all_taxes, recompute_tax_base_amount)
            # self.line_ids.filtered(lambda line: line.debit == 0 and line.credit == 0).unlink()
            tot_diif_due_round = sum(line.balance for line in self.line_ids)

            # if self.inv_type_id.code == 'inv_advance' and self.move_type in ['out_invoice', 'in_invoice', 'out_refund', 'in_refund'] and self.invoice_line_ids:
            #     if self.move_type == 'out_invoice':
            #         line_clt = self.line_ids.filtered(lambda x: x.account_id.code == '34210000')
            #         line_clt.debit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_clt.credit = 0
            #         line_adv = self.line_ids.filtered(lambda x: x.account_id.code == '44210000')
            #         line_adv.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_adv.debit = 0
            #         line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44552000')
            #         line_tax.credit = self.currency_id._convert(self.amount_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax.debit = 0
            #     if self.move_type == 'out_refund':
            #         line_clt = self.line_ids.filtered(lambda x: x.account_id.code == '34210000')
            #         line_clt.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_clt.debit = 0
            #         line_adv = self.line_ids.filtered(lambda x: x.account_id.code == '44210000')
            #         line_adv.credit = 0
            #         line_adv.debit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44552000')
            #         line_tax.credit = 0
            #         line_tax.debit = self.currency_id._convert(self.amount_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #     if self.move_type == 'in_invoice':
            #         account_supplier = self.env['account.account'].search([('code', '=', '44111000')])
            #         line_supplier = self.line_ids.filtered(lambda x: x.account_id.code == '44111000')
            #         line_supplier.account_id = account_supplier.id
            #         line_supplier.credit = self.currency_id._convert(self.amount_untaxed, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_supplier.debit = 0
            #         line_adv = self.line_ids.filtered(lambda x: x.account_id.code == '34110000')
            #         line_adv.debit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_adv.credit = 0
            #         line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44552000')
            #         line_tax.debit = self.currency_id._convert(self.amount_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax.credit = 0
            #     if self.move_type == 'in_refund':
            #         account_supplier = self.env['account.account'].search([('code', '=', '44111000')])
            #         # line_supplier = self.line_ids.filtered(lambda x: x.account_id.code.startswith('4411'))
            #         line_supplier = self.line_ids.filtered(lambda x: x.account_id.code == '44111000')
            #         line_supplier.account_id = account_supplier.id
            #         line_supplier.debit = self.currency_id._convert(self.amount_untaxed, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_supplier.credit = 0
            #         line_adv = self.line_ids.filtered(lambda x: x.account_id.code == '34110000')
            #         line_adv.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_adv.debit = 0
            #         line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44552000')
            #         line_tax.credit = self.currency_id._convert(self.amount_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax.debit = 0
            #     self._add_line_tax_adjustment_advance(self.move_type)
            
            if self.inv_type == 'inv_attachment' and self.move_type in ['out_invoice', 'out_refund'] and self.invoice_line_ids:
                self._upsert_lines_accounting_customer(self.move_type)
            if self.inv_type in ['inv_attachment'] and self.move_type in ['in_invoice', 'in_refund'] and self.invoice_line_ids:
                account_supplier = self.env['account.account'].search([('code', '=', '44111000')])
                line_supplier = self.line_ids.filtered(lambda x: x.account_id.code == '44110000')
                line_supplier.account_id = account_supplier.id
                line_supplier.name = account_supplier.name
                if self.move_type == 'in_invoice':
                    line_supplier.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
                    line_supplier.debit = 0
                    # line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '34552400')
                    # line_tax.debit = self.currency_id._convert(self.amount_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
                    # line_tax.credit = 0
                if self.move_type == 'in_refund':
                    line_supplier.debit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
                    line_supplier.credit = 0
                    # line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '34552400')
                    # line_tax.credit = self.currency_id._convert(self.amount_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
                    # line_tax.debit = 0
                self._upsert_lines_accounting_supplier(self.move_type)

            # if self.inv_type_id.code == 'inv_rg' and self.move_type in ['out_invoice', 'in_invoice', 'out_refund', 'in_refund'] and self.invoice_line_ids:
            #     if self.move_type == 'in_invoice':
            #         account_supplier = self.env['account.account'].search([('code', '=', '44111000')])
            #         line_supplier = self.line_ids.filtered(lambda x: x.account_id.code == '44111000')
            #         line_supplier.account_id = account_supplier.id
            #         line_supplier.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_rg = self.line_ids.filtered(lambda x: x.account_id.code == '44130000')
            #         line_rg.debit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
                    
            #         line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '34552400')
            #         line_tax.credit = 0
            #         line_tax.debit = self.currency_id._convert(self.amount_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #     if self.move_type == 'out_invoice':
            #         line_clt = self.line_ids.filtered(lambda x: x.account_id.code == '34210000')
            #         line_clt.debit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_clt.credit = 0
            #         line_rg = self.line_ids.filtered(lambda x: x.account_id.code == '34230000')
            #         line_rg.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_rg.debit = 0
            #         line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44552000')
            #         line_tax.credit = self.currency_id._convert(self.amount_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax.debit = 0
            #     if self.move_type == 'in_refund':
            #         account_supplier = self.env['account.account'].search([('code', '=', '44111000')])
            #         line_supplier = self.line_ids.filtered(lambda x: x.account_id.code == '44111000')
            #         line_supplier.account_id = account_supplier.id
            #         line_supplier.debit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_rg = self.line_ids.filtered(lambda x: x.account_id.code == '44130000')
            #         line_rg.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '34552400')
            #         line_tax.credit = self.currency_id._convert(self.amount_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax.debit = 0
            #     if self.move_type == 'out_refund':
            #         line_clt = self.line_ids.filtered(lambda x: x.account_id.code == '34210000')
            #         line_clt.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_clt.debit = 0
            #         line_rg = self.line_ids.filtered(lambda x: x.account_id.code == '34230000')
            #         line_rg.debit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44552000')
            #         line_tax.debit = self.currency_id._convert(self.amount_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax.credit = 0
            #     self._add_line_tax_adjustment_rg(self.move_type)
            
            # if self.inv_type_id.code == 'inv_finish' and self.move_type in ['out_invoice', 'in_invoice', 'out_refund', 'in_refund'] and self.invoice_line_ids:
            #     if self.move_type == 'in_invoice':
            #         account_supplier = self.env['account.account'].search([('code', '=', '44111000')])
            #         line_supplier = self.line_ids.filtered(lambda x: x.account_id.code == '44111000')
            #         line_supplier.account_id = account_supplier.id
            #         line_supplier.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_supplier.debit = 0
            #         line_finish = self.line_ids.filtered(lambda x: x.account_id.code == '44889000')
            #         line_finish.debit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_finish.credit = 0
            #         line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '34552400')
            #         line_tax.debit = self.currency_id._convert(self.amount_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax.credit = 0
            #     if self.move_type == 'out_invoice':
            #         line_clt = self.line_ids.filtered(lambda x: x.account_id.code == '34210000')
            #         line_clt.debit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_clt.credit = 0
            #         line_finish = self.line_ids.filtered(lambda x: x.account_id.code == '34889000')
            #         line_finish.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44552000')
            #         line_tax.credit = self.currency_id._convert(self.amount_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax.debit = 0
            #     if self.move_type == 'in_refund':
            #         account_supplier = self.env['account.account'].search([('code', '=', '44111000')])
            #         line_supplier = self.line_ids.filtered(lambda x: x.account_id.code == '44111000')
            #         line_supplier.account_id = account_supplier.id
            #         line_supplier.debit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_finish = self.line_ids.filtered(lambda x: x.account_id.code == '44889000')
            #         line_finish.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '34552400')
            #         line_tax.credit = self.currency_id._convert(self.amount_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax.debit = 0
            #     if self.move_type == 'out_refund':
            #         line_clt = self.line_ids.filtered(lambda x: x.account_id.code == '34210000')
            #         line_clt.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_clt.debit = 0
            #         line_finish = self.line_ids.filtered(lambda x: x.account_id.code == '34889000')
            #         line_finish.debit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax = self.line_ids.filtered(lambda x: x.account_id.code == '44552000')
            #         line_tax.debit = self.currency_id._convert(self.amount_tax, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
            #         line_tax.credit = 0
            #     self._add_line_tax_adjustment_finish(self.move_type)
            return res
        else:
            res = super(account_move, self)._recompute_dynamic_lines(recompute_all_taxes, recompute_tax_base_amount)
            return res

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.origin_payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.origin_payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'invoice_line_enter_ids',
        'amount_deduction_gr',
        'amount_advance_deduction',
        'amount_all_risk_site_insurance_deduction',
        'amount_prorata_account_deduction',
        'amount_finish_deduction',
        'amount_ten_year',
        )
    def _compute_amount(self):
        res = super(account_move, self)._compute_amount()
        for move in self:
            move.amount_untaxed_before_deduction = sum(line.price_subtotal for line in move.invoice_line_enter_ids)
            if move.inv_type in ['inv_attachment']:
                #####################cas deduction a base de TTC#########################
                move.amount_untaxed_before_deduction = sum(line.price_subtotal for line in move.invoice_line_enter_ids)
                move.amount_tax_before_deduction = sum((line.tax_line_id.amount*move.amount_untaxed_before_deduction/100 for line in move.line_ids if line.tax_line_id), 0.0)
                move.amount_total_before_deduction = move.amount_untaxed_before_deduction + move.amount_tax_before_deduction
                # move.amount_deduction_gr = move.amount_total_before_deduction*move.prc_gr/100
                # move.amount_advance_deduction = move.amount_total_before_deduction*move.prc_advance_deduction/100
                # move.amount_all_risk_site_insurance_deduction = move.amount_total_before_deduction*move.prc_all_risk_site_insurance/100
                # move.amount_prorata_account_deduction = move.amount_total_before_deduction*move.prc_prorata_account/100
                # move.amount_finish_deduction = move.amount_total_before_deduction*move.prc_finish/100
                # move.amount_ten_year = move.amount_total_before_deduction*move.prc_ten_year/100
                move.amount_total = move.amount_total_before_deduction - (move.amount_deduction_gr + move.amount_advance_deduction + move.amount_all_risk_site_insurance_deduction + move.amount_prorata_account_deduction + move.amount_finish_deduction + move.amount_ten_year)                
                total_ded_tva = move.amount_deduction_gr/6 + move.amount_advance_deduction/6 + move.amount_all_risk_site_insurance_deduction/6 + move.amount_prorata_account_deduction/6 + move.amount_finish_deduction/6 + move.amount_ten_year/6
                move.amount_tax = move.amount_tax_before_deduction - total_ded_tva
                # move.amount_tax = move.amount_tax_before_deduction
                if move.amount_tax_before_deduction == 0:
                    move.amount_tax = 0
                move.amount_untaxed = move.amount_total - move.amount_tax
                move.amount_untaxed_signed = move.amount_untaxed
                move.amount_tax_signed = move.amount_tax
                move.amount_total_signed = move.amount_total
                
            # if move.inv_type_id.code in ['inv_advance', 'inv_rg', 'inv_finish']:
            #     move.amount_untaxed_before_deduction = sum(line.price_subtotal for line in move.invoice_line_enter_ids)
            #     move.amount_tax_before_deduction = sum((line.tax_line_id.amount*move.amount_untaxed_before_deduction/100 for line in move.line_ids if line.tax_line_id), 0.0)
            #     move.amount_total_before_deduction = move.amount_untaxed_before_deduction + move.amount_tax_before_deduction
            #     move.amount_tax = move.amount_tax_before_deduction
            #     move.amount_untaxed = move.amount_untaxed_before_deduction
            #     move.amount_total = move.amount_total_before_deduction
            #     move.amount_untaxed_signed = move.amount_untaxed
            #     move.amount_tax_signed = move.amount_tax
            #     move.amount_total_signed = move.amount_total

        return res

    def action_post(self):
        res = super(account_move, self).action_post()
        self.attachment_id.is_inv_posted = True
        return res

    def button_draft(self):
        res = super(account_move, self).button_draft()
        self.attachment_id.is_inv_posted = False
        return res

    def unlink(self):
        for move in self:
            if move.move_type == "out_invoice" and move.inv_type == "inv_attachment" and not move.can_be_returned:
                raise UserError("Vous n'avez pas le droit de supprimer une facture de type 'Facture de Décompte'.")
            if move.attachment_id.state == 'done':
                raise UserError(_("Vous ne pouvez pas supprimer une facture avec attachement validé par le client."))
            if move.move_type == "out_invoice" and move.site_id:
                move.site_id.is_invisible_advance = False
        res = super(account_move, self).unlink()
        return res

class AccountMoveLineEnter(models.Model):
    _name = "account.move.line.enter"

    @api.depends('price_unit', 'current_price_unit', 'cumulative_price_unit', 'previous_price_unit', 'cumulative_quantity', 'quantity_counts_previous', 'current_count_quantity')
    def _compute_price_other(self):
        for line in self:
            line.current_price_subtotal = line.current_price_unit*line.current_count_quantity
            line.cumulative_price_subtotal = line.cumulative_price_unit*line.cumulative_quantity
            line.previous_price_subtotal = line.previous_price_unit*line.quantity_counts_previous

    move_id = fields.Many2one('account.move', string='Journal Entry',
        index=True, required=True, readonly=True, auto_join=True, ondelete="cascade",
        check_company=True,
        help="The move of this entry line.")
    move_name = fields.Char(string='Number', related='move_id.name', store=True, index=True)
    date = fields.Date(related='move_id.date', store=True, readonly=True, index=True, copy=False, group_operator='min')
    ref = fields.Char(related='move_id.ref', store=True, copy=False, index=True, readonly=True)
    parent_state = fields.Selection(related='move_id.state', store=True, readonly=True)
    journal_id = fields.Many2one(related='move_id.journal_id', store=True, index=True, copy=False)
    company_id = fields.Many2one(related='move_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', string='Devise', required=False)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Devise Société',
        readonly=True, store=True,
        help='Utility field to express amount currency')
    account_id = fields.Many2one('account.account', string='Compte',
        index=True, ondelete="cascade",
        domain="[('deprecated', '=', False), ('company_id', '=', 'company_id'),('is_off_balance', '=', False)]",
        check_company=True,
        tracking=True)
    # account_internal_type = fields.Selection(related='account_id.user_type_id.type', string="Internal Type", readonly=True)
    account_internal_group = fields.Selection(related='account_id.internal_group', string="Internal Group", readonly=True)
    account_root_id = fields.Many2one(related='account_id.root_id', string="Account Root", store=True, readonly=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Libellé', tracking=True)
    quantity = fields.Float(string='Quantité',
        default=1.0, digits='Product Unit of Measure',
        help="The optional quantity expressed by this line, eg: number of product sold. "
             "The quantity is not a legal requirement but is very useful for some reports.")
    price_unit = fields.Float(string='Prix', digits='Product Price')
    discount = fields.Float(string='Remise (%)', digits='Discount', default=0.0)
    price_subtotal = fields.Monetary(string='Sous-total', store=True, readonly=True,
        currency_field='currency_id')
    price_total = fields.Monetary(string='Total', store=True, readonly=True,
        currency_field='currency_id')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]", ondelete="restrict")
    product_id = fields.Many2one('product.product', string='Article', ondelete='restrict')
    product_uom_category_id = fields.Many2one('uom.category', related='product_id.uom_id.category_id')

    # ==== Tax fields ====
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        context={'active_test': False},
        check_company=True,
        help="Taxes that apply on the base amount")
    
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], default=False, help="Technical field for UX purpose.")
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')

    cumulative_quantity = fields.Float('Quantité cumulé')
    quantity_counts_previous = fields.Float('Quantité décomptes précédents')
    current_count_quantity = fields.Float('Quantité décompte courant')
    current_price_unit = fields.Float('Prix Unitaire Courant', readonly=False)
    cumulative_price_unit = fields.Float('Prix Unitaire Cumulé', readonly=False)
    previous_price_unit = fields.Float('Prix Unitaire Précédent', readonly=False)
    current_price_subtotal = fields.Float(string='Montant Courant', store=True, readonly=True, compute='_compute_price_other')
    cumulative_price_subtotal = fields.Float(string='Montant Cumulé', store=True, readonly=True, compute='_compute_price_other')
    previous_price_subtotal = fields.Float(string='Montant Précedent', store=True, readonly=True, compute='_compute_price_other')
    attachment_line_id = fields.Many2one('building.attachment.line', 'Ligne Attachement')
    site_id = fields.Many2one('building.site','Affaire', related='move_id.site_id', store=True)


    def _get_computed_price_unit(self):
        ''' Helper to get the default price unit based on the product by taking care of the taxes
        set on the product and the fiscal position.
        :return: The price unit.
        '''
        self.ensure_one()

        if not self.product_id:
            return 0.0
        if self.move_id.is_sale_document(include_receipts=True):
            document_type = 'sale'
        elif self.move_id.is_purchase_document(include_receipts=True):
            document_type = 'purchase'
        else:
            document_type = 'other'

        return self.product_id._get_tax_included_unit_price(
            self.move_id.company_id,
            self.move_id.currency_id,
            self.move_id.date,
            document_type,
            fiscal_position=self.move_id.fiscal_position_id,
            product_uom=self.product_uom_id
        )

    def _get_computed_name(self):
        self.ensure_one()

        if not self.product_id:
            return ''

        if self.partner_id.lang:
            product = self.product_id.with_context(lang=self.partner_id.lang)
        else:
            product = self.product_id

        values = []
        if product.partner_ref:
            values.append(product.partner_ref)
        if self.journal_id.type == 'sale':
            if product.description_sale:
                values.append(product.description_sale)
        elif self.journal_id.type == 'purchase':
            if product.description_purchase:
                values.append(product.description_purchase)
        return '\n'.join(values)

    def _get_computed_account(self):
        self.ensure_one()
        self = self.with_company(self.move_id.journal_id.company_id)

        if not self.product_id:
            return

        fiscal_position = self.move_id.fiscal_position_id
        accounts = self.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
        if self.move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            return accounts['income'] or self.account_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            return accounts['expense'] or self.account_id

    def _get_computed_taxes(self):
        self.ensure_one()

        if self.move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            if self.product_id.taxes_id:
                tax_ids = self.product_id.taxes_id.filtered(lambda tax: tax.company_id == self.move_id.company_id)
            elif self.account_id.tax_ids:
                tax_ids = self.account_id.tax_ids
            else:
                tax_ids = self.env['account.tax']
            if not tax_ids:
                tax_ids = self.move_id.company_id.account_sale_tax_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            if self.product_id.supplier_taxes_id:
                tax_ids = self.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == self.move_id.company_id)
            elif self.account_id.tax_ids:
                tax_ids = self.account_id.tax_ids
            else:
                tax_ids = self.env['account.tax']
            if not tax_ids:
                tax_ids = self.move_id.company_id.account_purchase_tax_id
        else:
            # Miscellaneous operation.
            tax_ids = self.account_id.tax_ids

        if self.company_id and tax_ids:
            tax_ids = tax_ids.filtered(lambda tax: tax.company_id == self.company_id)

        return tax_ids

    def _get_computed_uom(self):
        self.ensure_one()
        if self.product_id:
            return self.product_id.uom_id
        return False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue

            line.name = line._get_computed_name()
            line.account_id = line._get_computed_account()
            taxes = line._get_computed_taxes()
            if taxes and line.move_id.fiscal_position_id:
                taxes = line.move_id.fiscal_position_id.map_tax(taxes)
            line.tax_ids = taxes
            line.product_uom_id = line._get_computed_uom()
            line.price_unit = line._get_computed_price_unit()

    @api.onchange('quantity', 'price_unit')
    def _onchange_quantity_price_unit(self):
        for line in self:
            if line.display_type in ('line_section', 'line_note'):
                continue
            line.price_subtotal = line.price_unit*line.quantity

    @api.onchange('product_uom_id')
    def _onchange_uom_id(self):
        ''' Recompute the 'price_unit' depending of the unit of measure. '''
        for line in self:
            if line.display_type in ('line_section', 'line_note'):
                return
            taxes = line._get_computed_taxes()
            if taxes and line.move_id.fiscal_position_id:
                taxes = line.move_id.fiscal_position_id.map_tax(taxes)
            line.tax_ids = taxes
            line.price_unit = line._get_computed_price_unit()

    @api.onchange('account_id')
    def _onchange_account_id(self):
        ''' Recompute 'tax_ids' based on 'account_id'.
        /!\ Don't remove existing taxes if there is no explicit taxes set on the account.
        '''
        for line in self:
            if not line.display_type and (line.account_id.tax_ids or not line.tax_ids):
                taxes = line._get_computed_taxes()

                if taxes and line.move_id.fiscal_position_id:
                    taxes = line.move_id.fiscal_position_id.map_tax(taxes)

                line.tax_ids = taxes

    def _get_price_total_and_subtotal(self, price_unit=None, quantity=None, discount=None, currency=None, product=None, partner=None, taxes=None, move_type=None):
        self.ensure_one()
        return self._get_price_total_and_subtotal_model(
            price_unit=self.price_unit if price_unit is None else price_unit,
            quantity=self.quantity if quantity is None else quantity,
            discount=self.discount if discount is None else discount,
            currency=self.currency_id if currency is None else currency,
            product=self.product_id if product is None else product,
            partner=self.partner_id if partner is None else partner,
            taxes=self.tax_ids if taxes is None else taxes,
            move_type=self.move_id.move_type if move_type is None else move_type,
        )

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}

        # Compute 'price_subtotal'.
        line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * line_discount_price_unit

        # Compute 'price_total'.
        if taxes:
            taxes_res = taxes._origin.with_context(force_sign=1).compute_all(line_discount_price_unit,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        #In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res

    def _get_fields_onchange_subtotal(self, price_subtotal=None, move_type=None, currency=None, company=None, date=None):
        self.ensure_one()
        return self._get_fields_onchange_subtotal_model(
            price_subtotal=self.price_subtotal if price_subtotal is None else price_subtotal,
            move_type=self.move_id.move_type if move_type is None else move_type,
            currency=self.currency_id if currency is None else currency,
            company=self.move_id.company_id if company is None else company,
            date=self.move_id.date if date is None else date,
        )

    @api.model
    def _get_fields_onchange_subtotal_model(self, price_subtotal, move_type, currency, company, date):
        if move_type in self.move_id.get_outbound_types():
            sign = 1
        elif move_type in self.move_id.get_inbound_types():
            sign = -1
        else:
            sign = 1

        amount_currency = price_subtotal * sign
        balance = currency._convert(amount_currency, company.currency_id, company, date or fields.Date.context_today(self))
        return {
            'amount_currency': amount_currency,
            'currency_id': currency.id,
            'debit': balance > 0.0 and balance or 0.0,
            'credit': balance < 0.0 and -balance or 0.0,
        }

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_building_specific = fields.Boolean(default=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
