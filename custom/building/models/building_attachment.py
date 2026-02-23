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
import datetime
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from re import search

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale_refund',
    'in_refund': 'purchase_refund',
}

# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Supplier Invoice
    'out_refund': 'out_invoice',        # Customer Refund
    'in_refund': 'in_invoice',          # Supplier Refund
}


MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')


class building_attachment(models.Model):
    
    _name="building.attachment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'gestion des attachements'

    def print_attachment_client(self):
        return self.env.ref('building.attachement_client_action').report_action(self)

    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self._context

        def get_view_id(xid, name):
            try:
                return self.env['ir.model.data'].xmlid_to_res_id('building.' + xid, raise_if_not_found=True)
            except ValueError:
                try:
                    return self.env['ir.ui.view'].search([('name', '=', name)], limit=1).id
                except Exception:
                    return False    # view not found

        res = super(building_attachment, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        type_attachment = context.get('type_attachment',False)
        if view_type == 'form' and not view_id:
            if type_attachment == 'sale' :
                view_id = get_view_id('building_attachment_form', 'building.order')
                res = super(building_attachment, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
            if type_attachment == 'purchase' :
                view_id = get_view_id('building_supplier_attachment_form', 'building.order')
                res = super(building_attachment, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        
        if view_type == 'form' and toolbar:
            res['toolbar'] = {}

        if toolbar:
            if self._context.get('hide_actions'):
                res['toolbar']['action'] = []
                res['toolbar']['print'] = []
            else:
                pass

        return res

    @api.depends('line_ids.price_subtotal','line_ids.current_price_subtotal','line_ids.cumulative_price_subtotal','line_ids.previous_price_subtotal')
    def _compute_amount(self):
        for attachment in self:
            amount_tax = 0
            amount_untaxed = 0
            amount_current_untaxed = 0
            amount_current_tax = 0
            amount_previous_untaxed = 0
            amount_previous_tax = 0
            cumulative_amount_untaxed = 0
            cumulative_amount_tax = 0

            currency = self.env.user.company_id.currency_id
            for line in self.line_ids :
                taxes = line.tax_id.compute_all(price_unit = line.price_unit, currency = currency, quantity = line.qty, product = line.product_id, partner = attachment.partner_id)
                amount_untaxed += taxes['total_excluded']
                amount_tax += sum(dtct_tax.get('amount') for dtct_tax in taxes['taxes'])

                taxes_current = line.tax_id.compute_all(price_unit = line.price_unit, currency = currency, quantity = line.current_quantity, product = line.product_id, partner = attachment.partner_id)
                amount_current_untaxed += taxes_current['total_excluded']
                amount_current_tax += sum(dtct_tax.get('amount') for dtct_tax in taxes_current['taxes'])

                taxes_previous = line.tax_id.compute_all(price_unit = line.price_unit, currency = currency, quantity = line.previous_quantity, product = line.product_id, partner = attachment.partner_id)
                amount_previous_untaxed += taxes_previous['total_excluded']
                amount_previous_tax += sum(dtct_tax.get('amount') for dtct_tax in taxes_previous['taxes'])

                taxes_cumulative = line.tax_id.compute_all(price_unit = line.price_unit, currency = currency, quantity = line.cumulative_quantity, product = line.product_id, partner = attachment.partner_id)
                cumulative_amount_untaxed += taxes_cumulative['total_excluded']
                cumulative_amount_tax += sum(dtct_tax.get('amount') for dtct_tax in taxes_cumulative['taxes'])


            attachment.amount_untaxed = amount_untaxed
            attachment.amount_tax = amount_tax
            attachment.amount_total = attachment.amount_untaxed + attachment.amount_tax
            
            attachment.cumulative_amount_untaxed = cumulative_amount_untaxed
            attachment.amount_previous_untaxed = amount_previous_untaxed
            attachment.amount_current_untaxed = amount_current_untaxed
            
            attachment.cumulative_amount_tax = cumulative_amount_tax
            attachment.cumulative_amount = attachment.cumulative_amount_untaxed + cumulative_amount_tax
            attachment.amount_previous_tax = amount_previous_tax
            attachment.amount_previous = attachment.amount_previous_untaxed + amount_previous_tax
            attachment.amount_current_tax = amount_current_tax
            attachment.amount_current = attachment.amount_current_untaxed + amount_current_tax

    @api.model
    def _default_company(self):
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        return company_id

    name = fields.Char('Nom de l\'Attachement', size=256, required=False, readonly=False)
    number = fields.Char('Numéro', size=256, required=False, readonly=False)
    site_id =  fields.Many2one('building.site', 'Affaire')
    partner_id = fields.Many2one('res.partner', 'Client/Fournisseur')
    customer_id = fields.Many2one('res.partner', 'Client', domain=[('customer_rank', '>' , 0)])
    supplier_id = fields.Many2one('res.partner', 'Fournisseur', domain=[('supplier_rank', '>', 0)])
    order_id = fields.Many2one('building.order','BP')
    subcontracting_id =  fields.Many2one('building.subcontracting', 'Contrat de sous-traitance')
    start_date = fields.Date('Date Début',required=False,readonly=False,index=True, copy=False,default=lambda *a: time.strftime('%Y-%m-%d'), tracking=True)
    end_date = fields.Date('Date Fin',required=False,readonly=False,index=True, copy=False,default=lambda *a: time.strftime('%Y-%m-%d'), tracking=True)
    date = fields.Date('Date de Création',required=False,readonly=False,index=True, copy=False,default=lambda *a: time.strftime('%Y-%m-%d'))
    state = fields.Selection([('draft','Brouillon'),('dz_validated','Validé DZ'),('customer_validated','Validé par le client'),('validated_accounting','Validé comptabilité'),('supplier_validated','Validé par le sous-traitant'),('done','Terminé'),],'Statut',select=True, readonly=True,default='draft')
    open_attachment_state = fields.Selection([('draft','Brouillon'),('internal_validated','Validé CP/CT'), ('validated_accounting','Validé comptabilité')],'Statut',select=True, readonly=True,default='draft')
    not_open_attachment_state = fields.Selection([('draft','Brouillon'),('internal_validated','Validé CP/CT'), ('count_established','Décompte établi'),],'Statut',select=True, readonly=True,default='draft')
    final_state = fields.Selection([
        ('draft','Brouillon'),
        ('internal_validated','Validé CP/CT'), 
        ('validated_accounting','Validé comptabilité'), 
        ('count_established','Décompte établi'), 
    ],'Statut', compute="_compute_final_state", store=True)
    line_ids = fields.One2many('building.attachment.line','attachment_id', 'Détails Attachement', required=False)
    definitive_ok = fields.Boolean('Définitif',default=False,tracking=True)
    is_readonly_last_attachment = fields.Boolean(default=False)
    delay_attachment = fields.Float('Durée de l\'attachement', required=False)
    type_attachment = fields.Selection([('sale','Attachement client'),('purchase','Attachement fournisseur'),],'Type', readonly=True, select=True,change_default=True, track_visibility='always')
    location_src_id = fields.Many2one('stock.location', 'Depot Source',required=True)
    location_dest_id = fields.Many2one('stock.location', 'Depot Destination',required=True,domain=[('usage','=','customer')])
    cumulative_amount = fields.Float(string='Total Cumulé (TTC)',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    cumulative_amount_untaxed = fields.Float(string='Mnt Total HT',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    cumulative_amount_tax = fields.Float(string='Total Cumulé (TVA)',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_previous = fields.Float(string='Total TTC MONTANT DEJA FACTURÉ',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_previous_untaxed = fields.Float(string='MONTANT HT DEJA FACTURÉ',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_previous_tax = fields.Float(string='MONTANT TVA DEJA FACTURÉ',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_current_untaxed = fields.Float(string='MONTANT HT Mois',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_current_tax = fields.Float(string='MONTANT TVA Mois',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_current = fields.Float(string='MONTANT TTC Mois',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_untaxed = fields.Float(string='Montant global Hors Taxes',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = fields.Float(string='Montant de la TVA',store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Float(string='Montant global TVA Comprise',store=True, readonly=True, compute='_compute_amount')
    company_id = fields.Many2one('res.company', 'Société',default=_default_company)
    type_marche  = fields.Selection([('forfait','Au Forfait'), ('metre','Au métré')], string="Type de marché", default='metre')
    is_inv_posted = fields.Boolean('Facture Comptabilisé ?', required=False, default=False, readonly=False)
    ref_inv_count = fields.Char('Ref. décompte')
    opening_attachment = fields.Boolean("Attachement d'Ouverture")

    prc_advance_deduction = fields.Float(string="Amortissement du Pourcentage d'Avance")

    amount_order = fields.Float(string="Montant HT", related="order_id.amount_untaxed", store=True)
    currency_id = fields.Many2one("res.currency", string="Devise", related="order_id.currency_id", store=True)
    represent = fields.Char(string='Représentant')

    accumulations_work =  fields.Float(string="Cumul travaux réalisés actuel (HT)", compute="_compute_accumulations_work")
    accumulation_previous_amounts =  fields.Float(string="Cumul travaux précèdent (HT)", compute="_compute_accumulation_previous_amounts")
    amount_invoiced =  fields.Float(string=" Montant Brut de la situation (HT)", compute="_compute_amount_invoiced")
    amount_invoiced_ttc =  fields.Float(string="Montant Brut (TTC)", compute="_compute_amount_invoiced_ttc")

    deduction_prc_gr = fields.Float(string="Retenu de Garantie", compute="_compute_deduction_prc_gr")
    deduction_all_risk_insurance = fields.Float(string="Assurance TRC")
    deduction_ten_year = fields.Float(string="Assurance Décennale")
    deduction_advance = fields.Float(string="Amortissement du Pourcentage d'Avance")
    deduction_malus_retention = fields.Float(string="Retenue de malfaçons")

    deduction_advance_ttc  =  fields.Float(string="Déduction Avance (TTC)", compute="_compute_deduction_advance_ttc")
    deduction_rg_ttc = fields.Float(string="Déduction RG (TTC)", compute="_compute_deduction_rg_ttc")
    deduction_all_risk_insurance_ttc = fields.Float(string="Déduction Assurance TRC (HT)", compute="_compute_deduction_all_risk_insurance_ttc")
    deduction_ten_year_ttc = fields.Float(string="Déduction Assurance Décennale (TTC)", compute="_compute_deduction_ten_year_ttc")
    deduction_malus_retention_ht = fields.Float(string="Déduction Retenue de malfaçons (HT)", compute="_compute_deduction_malus_retention_ht")

    cumulative_advance_ttc = fields.Float(string="Déduction Avance (TTC)", compute="_compute_cumulative_avance")
    cumulative_rg_ttc = fields.Float(string="Déduction RG (TTC)", compute="_compute_cumulative_avance")
    cumulative_all_risk_insurance_ttc = fields.Float(string="Déduction Assurance TRC (TTC)", compute="_compute_cumulative_avance")
    cumulative_ten_year_ttc = fields.Float(string="Déduction Assurance Décennale (TTC)", compute="_compute_cumulative_avance")
    cumulative_malus_retention_ht = fields.Float(string="Déduction Assurance Décennale (TTC)", compute="_compute_cumulative_avance")

    amount_advance_ttc = fields.Float(string="Montant Avance (TTC)", compute="_compute_amount_avance")
    prc_rg = fields.Float(string="RG (%)", compute="_compute_amount_avance")
    amount_all_risk_insurance_ttc = fields.Float(string="Montant Assurance TRC (TTC)", compute="_compute_amount_avance")
    amount_ten_year_ttc = fields.Float(string="Montant Assurance Décennale (TTC)", compute="_compute_amount_avance")

    gross_amount_ht = fields.Float(string="Montant Brut (HT)", compute="_compute_gross_amount_ht")

    account_move_id = fields.Many2one('account.move', string="Facture")
    sequence = fields.Integer(string='Sequence', default=10)
    display_type = fields.Selection([
        ('line_chapter', "Chapitre"),
        ('line_sub_chapter', "Sous Chapitre"),
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    product_uom_id = fields.Many2one('uom.uom','UDM')
    price_quantity = fields.Float('Qté BDP')
    previous_quantity = fields.Float('Qté préc')
    cumulative_quantity = fields.Float('Qté Cum.')
    percentage_completion = fields.Float('% Avance', compute="_compute_percentage_completion")

    @api.depends('cumulative_quantity', 'price_quantity')
    def _compute_percentage_completion(self):
        for rec in self:
            if rec.price_quantity:
                rec.percentage_completion = (rec.cumulative_quantity / rec.price_quantity) * 100
            else:
                rec.percentage_completion = 0

    def print_decompte_provisional_report(self):
        return super(building_attachment, self).print_decompte_provisional_report()
    
    def print_decompte(self):
        return super(building_attachment, self).print_decompte()

    @api.depends('amount_invoiced', 'deduction_malus_retention_ht', 'deduction_all_risk_insurance_ttc')
    def _compute_gross_amount_ht(self):
        for record in self:
            record.gross_amount_ht = (record.amount_invoiced - record.deduction_malus_retention_ht - record.deduction_all_risk_insurance_ttc)

    @api.depends('amount_invoiced_ttc', 'prc_rg')
    def _compute_deduction_prc_gr(self):
        for rec in self:
            rec.deduction_prc_gr = rec.amount_invoiced_ttc * (rec.prc_rg / 100)

    @api.depends('amount_ten_year_ttc', 'cumulative_ten_year_ttc')
    def _compute_is_readonly_deduction_ten_year(self):
        for record in self:
            record.is_readonly_deduction_ten_year = record.amount_ten_year_ttc == record.cumulative_ten_year_ttc

    @api.constrains('deduction_prc_gr', 'deduction_all_risk_insurance', 'deduction_ten_year', 'deduction_advance', 'deduction_malus_retention')
    def _check_deduction_values(self):
        for record in self:
            if record.deduction_prc_gr < 0:
                raise ValidationError(_("La valeur de la déduction RG (TTC) ne peut pas être négative."))
            if record.deduction_all_risk_insurance < 0:
                raise ValidationError(_("La valeur de la déduction Assurance TRC (TTC) ne peut pas être négative."))
            if record.deduction_ten_year < 0:
                raise ValidationError(_("La valeur de la déduction Assurance Décennale (TTC) ne peut pas être négative."))
            if record.deduction_advance < 0:
                raise ValidationError(_("La valeur de la déduction Avance (TTC) ne peut pas être négative."))
            if record.deduction_malus_retention < 0:
                raise ValidationError(_("La valeur de la déduction Retenue de malfaçons (HT) ne peut pas être négative."))

            if record.deduction_all_risk_insurance > record.amount_all_risk_insurance_ttc:
                raise ValidationError(_("La déduction Assurance TRC (TTC) ne peut pas dépasser le montant total de l’assurance tous risques.\nVeuillez vérifier l’onglet 'Info.Facturation'."))
            if record.deduction_ten_year > record.amount_ten_year_ttc:
                raise ValidationError(_("La déduction Assurance Décennale (TTC) ne peut pas dépasser le montant total de la garantie décennale.\nVeuillez vérifier l’onglet 'Info.Facturation'."))
            if record.deduction_advance > record.amount_advance_ttc:
                raise ValidationError(_("La déduction Avance (TTC) ne peut pas dépasser le montant total de l’avance.\nVeuillez vérifier l’onglet 'Info.Facturation'."))

            if record.cumulative_advance_ttc > record.amount_advance_ttc:
                raise ValidationError(_("Le cumul des déductions Avance (TTC) dépasse le montant total disponible.\nVeuillez vérifier l’onglet 'Info.Facturation'."))
            if record.cumulative_all_risk_insurance_ttc > record.amount_all_risk_insurance_ttc:
                raise ValidationError(_("Le cumul des déductions Assurance TRC (TTC) dépasse le montant prévu.\nVeuillez vérifier l’onglet 'Info.Facturation'."))
            if record.cumulative_ten_year_ttc > record.amount_ten_year_ttc:
                raise ValidationError(_("Le cumul des déductions Assurance Décennale (TTC) dépasse le montant autorisé.\nVeuillez vérifier l’onglet 'Info.Facturation'."))
            
    @api.depends('site_id')
    def _compute_amount_avance(self):
        for rec in self:
            if rec.site_id:
                rec.amount_advance_ttc = rec.site_id.prc_advance_deduction
                rec.prc_rg = rec.site_id.prc_gr
                rec.amount_all_risk_insurance_ttc = rec.site_id.prc_all_risk_site_insurance
                rec.amount_ten_year_ttc = rec.site_id.prc_ten_year

    def _compute_cumulative_avance(self):
        for record in self:
            sum_avance = 0
            sum_rg = 0
            sum_ten_year = 0
            sum_deduction_all_risk_insurance = 0
            sum_malus_retention = 0
            
            if record.id:
                order_ids = self.search([
                    ('site_id', '=', record.site_id.id), 
                    ('order_id', '=', record.order_id.id),
                    ('opening_attachment', '=', False),
                    ('id', '<=', record.id)
                ])

                sum_avance = sum(rec.deduction_advance for rec in order_ids) + (record.site_id.advance_opening_amount or 0.0)
                sum_rg = sum(rec.deduction_prc_gr for rec in order_ids) + (record.site_id.rg_opening_prc or 0.0)
                sum_ten_year = sum(rec.deduction_ten_year for rec in order_ids) + (record.site_id.ten_year__opening_amount or 0.0)
                sum_deduction_all_risk_insurance = sum(rec.deduction_all_risk_insurance for rec in order_ids) + (record.site_id.all_risk_site_insurance__opening_amount or 0.0)
                sum_malus_retention = sum(rec.deduction_malus_retention for rec in order_ids) + (record.site_id.malus_retention_opening_amount or 0.0)

            record.cumulative_advance_ttc = round(sum_avance)
            record.cumulative_rg_ttc = round(sum_rg)
            record.cumulative_ten_year_ttc = round(sum_ten_year)
            record.cumulative_all_risk_insurance_ttc = round(sum_deduction_all_risk_insurance)
            record.cumulative_malus_retention_ht = round(sum_malus_retention)

    net_amount_to_be_invoiced = fields.Float(string="Net à facturer en TTC", compute="_compute_net_amount_to_be_invoiced")
    executed =  fields.Float(string="Pourcentage éxécuté", compute="_comput_executed")

    is_prc_gr_readonly = fields.Boolean(compute="_compute_is_readonly_field", store=True)
    is_prc_all_risk_site_insurance_readonly = fields.Boolean(compute="_compute_is_readonly_field", store=True)
    is_prc_ten_year_readonly = fields.Boolean(compute="_compute_is_readonly_field", store=True)
    is_prc_advance_deduction_readonly = fields.Boolean(compute="_compute_is_readonly_field", store=True)

    is_open_back_cp_ct_visible = fields.Boolean(compute="_compute_is_open_back_cp_ct_visible")

    def _compute_is_open_back_cp_ct_visible(self):
        for rec in self:
            records = self.env['building.attachment'].search([
                ('site_id', '=', rec.site_id.id),
                ('order_id', '=', rec.order_id.id),
                ('opening_attachment', '=', False),
            ])

            if records:
                self.is_open_back_cp_ct_visible = True
            else:
                self.is_open_back_cp_ct_visible = False

    @api.depends('opening_attachment', 'open_attachment_state', 'not_open_attachment_state')
    def _compute_final_state(self):
        for rec in self:
            open_state = getattr(rec, 'open_attachment_state', False)
            not_open_state = getattr(rec, 'not_open_attachment_state', False)
            rec.final_state = open_state if rec.opening_attachment else not_open_state

    def back_to_dz_validated(self, reason=None):
        self.write({'state': 'dz_validated'})

        body = f"""
            <ul>
                <li>Motif de Retour: {reason}</li>
            <ul/>
            """
        self.message_post(body=body)

    def action_dz_validated(self):
        self.write({'state': 'dz_validated'})

    @api.constrains('start_date', 'end_date')
    def _check_start_end_date(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError(_("La date de début d'attachement doit être postérieure à la date de fin d'attachement."))
            
            last_entry = self.env['building.attachment'].search([('site_id', '=', record.site_id.id), ('id', '!=', record.id)], order='id desc', limit=1)
            if last_entry and last_entry.end_date:
                if record.start_date <= last_entry.end_date:
                    last_date_formatted = last_entry.end_date.strftime('%d-%m-%Y')
                    raise ValidationError(_(
                        "La date de début d'attachement doit être postérieure à la date du dernier attachement ({last_date})."
                    ).format(last_date=last_date_formatted))

            building_order = self.env['building.order'].search([('site_id', '=', record.site_id.id)], order='id desc', limit=1)
            if building_order and building_order.create_date:
                if record.start_date < building_order.create_date.date():
                    raise ValidationError(_("La date de début d'attachement doit être postérieure à la date du BDP."))

    @api.onchange('line_ids')
    def onchange_line_ids(self):
        for rec in self:
            if all((line.cumulative_quantity + line.previous_quantity) == line.price_quantity for line in rec.line_ids):
                rec.definitive_ok = True
                rec.is_readonly_last_attachment = True
            else:
                rec.definitive_ok = False
                rec.is_readonly_last_attachment = False

    def open_back_to_draft_reason_wizard(self):
        return {
            "name": "Assistant de retour",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cancellation.reason',
            'target': 'new',
        }
        
    def action_draft_attachment(self, reason=None):
        self.write({'open_attachment_state': 'draft'})
        self.write({'not_open_attachment_state': 'draft'})

        body = f"""
            <ul>
                <li>Motif de Retour: {reason}</li>
            <ul/>
            """
        self.message_post(body=body)

    def action_back_to_attachment_draft(self, reason=None):
        self.write({'not_open_attachment_state': 'internal_validated'})

        body = f"""
            <ul>
                <li>Motif de Retour: {reason}</li>
            <ul/>
            """
        self.message_post(body=body)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'building.attachment',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(self.env.ref('building.building_attachment_form').id, 'form')],
            'target': 'current',
        }

    @api.depends('site_id')
    def _compute_is_readonly_field(self):
        for rec in self:
            rec.is_prc_gr_readonly = bool(rec.site_id.prc_gr)
            rec.is_prc_all_risk_site_insurance_readonly = bool(rec.site_id.prc_all_risk_site_insurance)
            rec.is_prc_ten_year_readonly = bool(rec.site_id.prc_ten_year)
            rec.is_prc_advance_deduction_readonly = bool(rec.site_id.prc_advance_deduction)

    @api.depends('accumulations_work', 'amount_order')
    def _comput_executed(self):
        for record in self:
            if record.amount_order != 0:
                record.executed = (record.accumulations_work / record.amount_order) * 100
            else:
                record.executed = 0

    @api.depends('line_ids')
    def _compute_accumulations_work(self):
        for record in self:
            total_cumulative_amount = sum(line.cumulative_price_subtotal for line in record.line_ids)
            record.accumulations_work = total_cumulative_amount

    @api.depends('order_id', 'site_id')
    def _compute_accumulation_previous_amounts(self):
        for record in self:
            if record.order_id:
                entries = self.env['building.attachment'].search([
                    ('order_id', '=', record.order_id.id),
                    ('site_id', '=', record.site_id.id),
                    ('opening_attachment', '=', False),
                    ('id', '<', record.id)
                ])
                total_cumulative_amount = 0
                if entries:
                    for entry in entries:
                        for line in entry.line_ids:
                            total_cumulative_amount += line.cumulative_price_subtotal
                    record.accumulation_previous_amounts = total_cumulative_amount + record.site_id.amount_billed
                else:
                    record.accumulation_previous_amounts = record.site_id.amount_billed or 0.0
            else:
                record.accumulation_previous_amounts = 0.0

    @api.depends('accumulations_work', 'accumulation_previous_amounts')
    def _compute_amount_invoiced(self):
        for record in self:
            record.amount_invoiced = record.accumulations_work - record.accumulation_previous_amounts

    @api.depends('line_ids')
    def _compute_amount_invoiced_ttc(self):
        for record in self:
            record.amount_invoiced_ttc = record.gross_amount_ht * (1 + (record.site_id.tax_id.amount / 100))

    @api.depends('deduction_advance')
    def _compute_deduction_advance_ttc(self):
        self.deduction_advance_ttc  = self.deduction_advance

    @api.depends('deduction_prc_gr')
    def _compute_deduction_rg_ttc(self):
        self.deduction_rg_ttc = self.deduction_prc_gr

    @api.depends('deduction_all_risk_insurance')
    def _compute_deduction_all_risk_insurance_ttc(self):
        for rec in self:
            rec.deduction_all_risk_insurance_ttc = rec.deduction_all_risk_insurance
            
    @api.depends('deduction_ten_year')
    def _compute_deduction_ten_year_ttc(self):
        for rec in self:
            rec.deduction_ten_year_ttc = rec.deduction_ten_year

    @api.depends('deduction_malus_retention')
    def _compute_deduction_malus_retention_ht(self):
        for rec in self:
            rec.deduction_malus_retention_ht = rec.deduction_malus_retention

    @api.depends('amount_invoiced_ttc', 'deduction_advance_ttc', 'deduction_rg_ttc', 'deduction_ten_year_ttc')
    def _compute_net_amount_to_be_invoiced(self):
        for record in self:
            total_invoiced = record.amount_invoiced_ttc or 0.0
            total_deductions = (record.deduction_advance_ttc or 0.0) + (record.deduction_rg_ttc or 0.0) + (record.deduction_ten_year_ttc or 0.0)
            record.net_amount_to_be_invoiced = total_invoiced - total_deductions

    def _interpolation_dict(self):
        t = time.localtime() # Actually, the server is always in UTC.
        return {
            'year': time.strftime('%Y', t),
            'month': time.strftime('%m', t),
            'day': time.strftime('%d', t),
            'y': time.strftime('%y', t),
            'doy': time.strftime('%j', t),
            'woy': time.strftime('%W', t),
            'weekday': time.strftime('%w', t),
            'h24': time.strftime('%H', t),
            'h12': time.strftime('%I', t),
            'min': time.strftime('%M', t),
            'sec': time.strftime('%S', t),
        }

    def _interpolate(self, s, d):
        if s:
            return s % d
        return  ''

    def opning_action_back_cp_ct(self, reason=None):
        self.write({'open_attachment_state': 'validated_accounting'})

        body = f"""
            <ul>
                <li>Motif de Retour: {reason}</li>
            <ul/>
            """
        self.message_post(body=body)
    
    def action_internal_validated(self):
        self.write({'open_attachment_state': 'internal_validated'})
        self.write({'not_open_attachment_state': 'internal_validated'})

    def action_validation_accounting(self):
        self.write({'open_attachment_state': 'validated_accounting'})

    def action_validation_accounting_decompte(self):
        self.write({'state': 'validated_accounting'})
    
    def back_to_draft_decompte(self, reason=None):
        self.write({'state': 'draft'})

        body = f"""
            <ul>
                <li>Motif de Retour: {reason}</li>
            <ul/>
            """
        self.message_post(body=body)

    def back_to_customer_validated_decompte(self, reason=None):
        self.write({'state': 'customer_validated'})

        body = f"""
            <ul>
                <li>Motif de Retour: {reason}</li>
            <ul/>
            """
        self.message_post(body=body)

    def action_count_established(self):
        self.write({'not_open_attachment_state': 'count_established'})
        self.write({'state': 'draft'})
        if self.type_attachment == 'sale' :
            # sequence_id = self.env['ir.sequence'].search([('code', '=','building.attachment')])
            d = self._interpolation_dict()
            prefix = "/%(year)s/"
            interpolated_prefix = self._interpolate(prefix, d)
            attachments = self.search([('site_id', '=' , self.site_id.id), ('type_attachment', '=' , 'sale'), ('id', '!=' , self.id)])
            count_attachment = len(attachments.ids) + 1
            site_number = str(self.site_id.number)
            sequ = site_number + interpolated_prefix + '%%0%sd' % 3 % count_attachment
            # self.write({'number':sequ})
        if self.type_attachment =='purchase' :
            # sequence_id = self.env['ir.sequence'].search([('code', '=', 'building.attachment.supplier')])
            d = self._interpolation_dict()
            prefix = "/%(year)s/"
            interpolated_prefix = self._interpolate(prefix, d)
            attachments = self.search([('site_id', '=' , self.site_id.id), ('type_attachment', '=' , 'purchase'), ('id', '!=' , self.id)])
            count_attachment = len(attachments.ids) + 1
            site_number = str(self.site_id.number)
            sequ = site_number + interpolated_prefix + '%%0%sd' % 3 % count_attachment
            # self.write({'number':sequ})
        if self.type_attachment =='purchase' and self.definitive_ok:
            self.subcontracting_id.write({'shipped': True})
        return True
    
    def action_customer_validated(self):
        self.write({'state': 'customer_validated'})

    # def action_customer_validated(self):
    #     order = False
    #     attachments_draft = False
    #     attachments_validate = False
    #     if self.type_attachment == 'sale' :
    #         self.write({'state': 'customer_validated'})
    #         order = self.order_id
    #         attachments_draft = self.search([('type_attachment', '=' , 'sale'), ('site_id', '=' , self.site_id.id), ('order_id', '=' , self.order_id.id), ('id', '<' , self.id), ('state', '=' , 'draft')])
    #         attachments_validate = self.search([('type_attachment', '=' , 'sale'), ('site_id', '=' , self.site_id.id), ('order_id', '=' , self.order_id.id), ('id', '<' , self.id), ('state', '=' , 'done')])
    #         if self.definitive_ok :
    #             self.order_id.write({'shipped': True})
    #     if self.type_attachment == 'purchase' :
    #         self.write({'state': 'supplier_validated'})
    #         order = self.subcontracting_id
    #         attachments_draft = self.search([('type_attachment', '=', 'purchase'), ('site_id', '=' , self.site_id.id), ('subcontracting_id', '=' , self.subcontracting_id.id), ('id', '<' , self.id), ('state', '=' , 'draft')])
    #         attachments_validate = self.search([('type_attachment', '=' , 'purchase'), ('site_id', '=' , self.site_id.id), ('subcontracting_id', '=' , self.subcontracting_id.id), ('id', '<' , self.id), ('state', '=' , 'done')])
    #     delay = 0

    #     if attachments_draft :
    #         raise UserError(_('Attention!: Il y a un Bon d\'attachement précédent pas encore confirmé! : Merci de le confirmer.'))

    #     if attachments_validate :
    #         for attachment in attachments_validate:
    #             delay = delay +  attachment.delay_attachment

    #     if self.site_id.type_marche == 'metre' and self.delay_attachment+delay > self.site_id.duration and not self.env.user.valid_exceeding_site_delay_ok :
    #         raise UserError(_('Attention dépassement durée: Durée %s dépasse la durée global %s de l\'Affaire %s !!!!')%(self.delay_attachment+delay,self.site_id.duration,self.site_id.name))

    #         # A remettre apres presentation
    #     # if (self.cumulative_amount/order.amount_total)*100 > 90 and self.cumulative_amount/order.amount_total*100 <= 100 :
    #     #         record = {
    #     #                  'message':"Montant %s de l\'Attachement %s dépasse %s %s le montant %s du bon du commande %s!!!!"%(self.cumulative_amount,self.name,90,'%',order.amount_total,order.name)
    #     #                  }
    #     #         wizard_id = self.env['building.attachment.control'].create(record)
    #     #         view_ref = self.env['ir.model.data'].get_object_reference('building', 'building_attachment_control_form')
    #     #         view_id = view_ref and view_ref[1] or False
    #     #         return {
    #     #             'name':_("Information"),
    #     #             'view_mode': 'form',
    #     #             'view_id': False,
    #     #             'view_type': 'form',
    #     #             'res_model': 'building.attachment.control',
    #     #             'res_id':wizard_id,
    #     #             'type': 'ir.actions.act_window',
    #     #             'nodestroy': True,
    #     #             'target': 'new',
    #     #             'domain': '[]'
    #     #         }

    #     # if (self.cumulative_amount/order.amount_total)*100 > 100 and not self.env.user.valid_attach_ok:
    #     #     raise UserError(_('Attention!: Montant %s de l\'Attachement %s dépasse %s %s le montant %s du bon du commande %s!,Contacter votre supperieur pour approbation !!!')%(self.cumulative_amount,self.name,100,'%',order.amount_total,order.name))

    #     return True

    def _get_journal_invoice(self, type_inv):
        if self._context is None:
            self._context = {}
        user = self.env.user
        company_id = self._context.get('company_id', user.company_id.id)
        type2journal = {'out_invoice': 'sale', 'in_invoice': 'purchase', 'out_refund': 'sale_refund', 'in_refund': 'purchase_refund'}
        journal_obj = self.env['account.journal']
        domain = [('company_id', '=', company_id)]
        if isinstance(type_inv, list):
            domain.append(('type', 'in', [type2journal.get(type) for type in type_inv if type2journal.get(type)]))
        else:
            domain.append(('type', '=', type2journal.get(type_inv, 'sale')))
        res = journal_obj.search(domain, limit=1)
        return res and res.id or False

    # def action_done(self):
    #     date_inv = datetime.now().date()
    #     invoice_obj = self.env['account.move']
    #     invoice_line_obj = self.env['account.move.line']
    #     fp_obj = self.env['account.fiscal.position']
    #     account_obj = self.env['account.account']
    #     attach = self
    #     invoice_lines = []
    #     if attach.type_attachment =='sale' :
    #         account_line_id = account_obj.search([('code', '=' , 71240000)])
            
    #         ##################################Preparation section a creer################################
    #         dict_line_with_child = {}
    #         last_section = False
    #         id_first = attach.line_ids.ids[0]
    #         current_line = False
    #         new_section = False
    #         for line in attach.line_ids:
    #             if line.display_type in ['line_section', 'line_note']:
    #                 if current_line:
    #                     last_section = current_line
    #                     new_section = True
    #                 if id_first == line.id:
    #                     new_section = True
    #                 if last_section:
    #                     dict_line_with_child[line.id] = {'is_section':True, 'to_create': False, 'parent':last_section, 'childs':[]}
    #                     dict_line_with_child[last_section]['childs'].append(line.id)
    #                 if new_section:
    #                     dict_line_with_child[line.id] = {'is_section':True, 'to_create': False, 'parent':None, 'childs':[]}
    #                 last_section = line.id
    #             else:
    #                 if line.cumulative_quantity > 0:
    #                     if last_section:
    #                         dict_line_with_child[last_section]['childs'].append(line.id)
    #                         current_line = line.id + 1
    #                 else:
    #                     current_line = line.id + 1
            
    #         sections_to_create = {}
    #         childs = {}
    #         if bool(dict_line_with_child):
    #             for line_id, row in dict_line_with_child.items():
    #                 if row['childs']:
    #                     for child in row['childs']:
    #                         if child not in dict_line_with_child:
    #                             sections_to_create[line_id] = True
    #                         else:
    #                             childs[line_id] = child
    #         if bool(childs):
    #             for k, v in childs.items():
    #                 while v not in sections_to_create and v in childs:
    #                     v = childs[v]
    #                     childs[k] = v
            
    #         if bool(childs):
    #             for k, v in childs.items():
    #                 if v in sections_to_create:
    #                     sections_to_create[k] = True
    #         ##################################Fin Preparation section a creer################################
            
    #         for line in attach.line_ids:
    #             if not line.display_type:
    #                 if line.cumulative_quantity > 0:
    #                     invoice_line_vals ={
    #                             'name':line.name,
    #                             'product_id': line.product_id.id if line.product_id else False,
    #                             'account_id':account_line_id.id,
    #                             'price_unit': line.price_unit,
    #                             'cumulative_quantity':line.cumulative_quantity,
    #                             'quantity_counts_previous':line.previous_quantity,
    #                             'current_count_quantity':line.current_quantity,
    #                             'current_price_unit':line.price_unit,
    #                             'cumulative_price_unit': line.price_unit,
    #                             'previous_price_unit': line.price_unit,
    #                             'quantity': line.current_quantity,
    #                             'tax_ids' : [(6, 0, line.line_dqe_id.tax_id.ids)],
    #                             'attachment_line_id':line.id,
    #                             'product_uom_id':line.product_uom_id.id,
    #                             'currency_id':self.env.user.company_id.currency_id.id
    #                         }
    #                     invoice_lines.append((0, 0, invoice_line_vals))
    #             elif line.display_type in ['line_section', 'line_note'] and line.id in sections_to_create:
    #                 invoice_lines.append((0, 0, {'name': line.name, 'display_type':line.display_type}))
    #         journal_id = self._get_journal_invoice('out_invoice')
    #         invoice_vals = {
    #                 'name': attach.name,
    #                 'invoice_origin': (attach.name or ''),
    #                 'invoice_date': date_inv,
    #                 'partner_id': attach.customer_id.id,
    #                 'attachment_id': attach.id,
    #                 'site_id':attach.site_id.id,
    #                 'invoice_attachment': True,
    #                 'inv_type': 'inv_attachment',
    #                 'invoice_user_id': self._uid,
    #                 'deposit_number': attach.site_id.deposit_number,
    #                 'guaranty_number': attach.site_id.guaranty_number,
    #                 'prc_advance_deduction': attach.deduction_advance,
    #                 'prc_gr': attach.deduction_prc_gr,
    #                 'prc_all_risk_site_insurance': attach.deduction_all_risk_insurance,
    #                 'prc_ten_year': attach.deduction_ten_year,
    #                 'prc_malus_retention': attach.deduction_malus_retention,
    #                 'move_type':'out_invoice',
    #                 'journal_id':journal_id,
    #                 'reference': attach.number,
    #                 'currency_id':self.env.user.company_id.currency_id.id,
    #                 'order_id':attach.order_id.id,
    #                 'invoice_line_enter_ids':invoice_lines
    #             }
            
    #         if self.definitive_ok :
    #             invoice_vals['last_attachment'] = True

    #         invoice = invoice_obj.create(invoice_vals)
    #         attach.account_move_id = invoice.id

    #         lines = []
    #         for line in invoice.invoice_line_enter_ids:
    #             if not line.display_type:
    #                 lines.append((0,0,{
    #                         'product_id': line.product_id.id if line.product_id else False,
    #                         'name': line.name,
    #                         'account_id': line.account_id.id if line.account_id else False,
    #                         'price_unit':line.price_unit,
    #                         'cumulative_quantity':line.cumulative_quantity,
    #                         'quantity_counts_previous':line.quantity_counts_previous,
    #                         'current_count_quantity':line.current_count_quantity,
    #                         'current_price_unit':line.price_unit,
    #                         'cumulative_price_unit': line.price_unit,
    #                         'previous_price_unit': line.price_unit,
    #                         'quantity': line.current_count_quantity,
    #                         'tax_ids':line.attachment_line_id.line_dqe_id.tax_id.ids if line.attachment_line_id.line_dqe_id.tax_id else False,
    #                         'attachment_line_id':line.attachment_line_id.id,
    #                         'product_uom_id':line.product_uom_id.id,
    #                     }))
    #         invoice.invoice_line_ids = lines

    def action_done(self):
        self.write({'state': 'done'})
        for rec in self:
            date_inv = datetime.now().date()
            journal_id = self._get_journal_invoice('out_invoice')
            account_line_id = self.env['account.account'].search([('code', '=', '7051000')], limit=1)
            move_type = self.env['account.move.type'].search([('code', '=', 'inv_entry')], limit=1)

            invoice_vals = {
                'name': '/',
                'move_type': 'out_invoice',
                'partner_id': rec.customer_id.id,
                "invoice_payment_term_id": rec.customer_id.property_payment_term_id.id,
                'invoice_origin': rec.name or '',
                'invoice_date': date_inv,
                'site_id': rec.site_id.id,
                'decompte': rec.number,
                'prc_advance_deduction': rec.deduction_advance,
                'prc_gr': rec.deduction_prc_gr,
                'prc_ten_year': rec.deduction_ten_year,
                'prc_malus_retention': rec.deduction_malus_retention,
                'move_type_id': move_type.id if move_type else False,
                'journal_id': journal_id,
                'ref': rec.number,
                'currency_id': self.env.user.company_id.currency_id.id,
                'order_id': rec.order_id.id,
                'invoice_line_ids': [],
            }

            invoice_line = {
                'name': f'Montant des travaux réalisés suivant décompte {rec.number}',
                'account_id': account_line_id.id,
                'price_unit': rec.gross_amount_ht,
                'quantity': 1,
                'product_uom_id': rec.line_ids[0].product_uom_id.id if rec.line_ids else False,
                'currency_id': self.env.user.company_id.currency_id.id,
                'tax_ids' : [(6, 0, rec.line_ids.line_dqe_id.tax_id.ids)],
                'exclude_from_invoice_tab': False,
            }

            invoice_vals['invoice_line_ids'].append((0, 0, invoice_line))
            invoice = self.env['account.move'].create(invoice_vals)
            rec.account_move_id = invoice.id

    def action_draft(self, reason=None):
        self.write({'state':'validated_accounting'})
        body = f"""
            <ul>
                <li>Motif de Retour: {reason}</li>
            <ul/>
            """
        self.message_post(body=body)
        inv = self.env['account.move'].search([('attachment_id', '=', self.id), ('site_id', '=', self.site_id.id), ('invoice_attachment', '=', True), ('state', '=', 'draft')])
        if inv:
            if inv.name != '/' and inv.state == 'draft':
                inv.button_cancel()
            inv.unlink()
        return True
        
    def unlink(self):
        for attach in self:
            if attach.state != 'draft':
                raise UserError(_("Vous ne pouvez supprimer que les attachements en brouillon."))
        res = super(building_attachment, self).unlink()
        return res

    def action_get_dz_users_client(self, readonly=False, nocreate=False):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
        ])

        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'default_type_attachment':'sale',
            'group_by': ['site_id'],
            'hide_actions':True,
        }

        domain = [('opening_attachment', '=', False), ('type_attachment', '=', 'sale'), ('not_open_attachment_state', '=', 'count_established'), ('site_id', 'in', site_ids)]

        return {
            'name': 'Décompte Client',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'building.attachment',
            'views': [
                (self.env.ref('building.building_attachment_inv_tree').id, 'tree'),
                (self.env.ref('building.building_attachment_inv_form').id, 'form'),
            ],
            'domain': domain,
            'context': context,
        }

    def action_get_user_attachments_clinet(self, readonly=False, nocreate=False):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
        ])

        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'default_type_attachment':'sale',
            'group_by': ['site_id'],
            'hide_actions':True,
        }

        group_purchase = self.env.user.has_group('account.group_account_invoice')
        group_project_manager = self.env.user.has_group('building_plus.sotaserv_chef_projet')
        group_works_manager = self.env.user.has_group('building_plus.sotaserv_conduct_trv')
        
        if group_purchase and not (group_project_manager or group_works_manager):
            domain = [
                ('type_attachment','=','sale'),
                ('opening_attachment', '=', True),
                ('open_attachment_state', 'in', ['internal_validated', 'validated_accounting']),
            ]
        else:
            domain = [
                ('type_attachment','=','sale'),
                ('site_id', 'in', site_ids)
            ]

        return {
            'name': 'Attachements Client',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'building.attachment',
            'views': [
                (self.env.ref('building.building_attachment_tree').id, 'tree'),
                (self.env.ref('building.building_attachment_form').id, 'form')
            ],
            'domain': domain,
            'context': context,
        }
    
    def _get_flattened_lines(self):
        lines = []
        for section in self._get_printable_lines():
            if isinstance(section, dict) and section.get('lines'):
                lines.append({'is_section': True, 'name': section['name']})
                for l in section['lines']:
                    l.update({'is_section': False})
                    lines.append(l)
            elif isinstance(section, dict) and 'cumulative_quantity' in section:
                section.update({'is_section': False})
                lines.append(section)
        return lines

    def _get_printable_lines(self):
        grouped_lines = []
        current_section = None
        has_section = any(line.display_type == 'line_section' for line in self.line_ids)

        for line in self.line_ids.sorted('sequence'):
            if line.display_type == 'line_section':
                current_section = {
                    'id': line.id,
                    'name': line.name,
                    'sequence': line.sequence,
                    'display_type': line.display_type,
                    'lines': []
                }
                grouped_lines.append(current_section)
            elif not line.display_type:
                line_data = {
                    'id': line.id,
                    'sequence': line.sequence,
                    'name': line.name,
                    'product_uom_id': line.product_uom_id.name,
                    'price_quantity': line.price_quantity,
                    'previous_quantity': line.previous_quantity,
                    'cumulative_quantity': line.cumulative_quantity,
                    'percentage_completion': line.percentage_completion,
                    'price_unit': line.price_unit,
                    'cumulative_price_subtotal': line.cumulative_price_subtotal,
                }

                if has_section:
                    if current_section:
                        current_section['lines'].append(line_data)
                else:
                    grouped_lines.append(line_data)

        if has_section:
            for section in grouped_lines:
                section['sum_cumulative_quantity'] = sum(
                    l.get('cumulative_quantity', 0) for l in section.get('lines', [])
                )

        return grouped_lines

    def fix_order_line_id(self):
        for attachment in self.env["building.attachment"].search([]):
            for line in attachment.line_ids:
                line._compute_percentage_completion()
            # site_id = attachment.site_id
            # building_order = self.env['building.order'].search([('site_id', '=', site_id.id)])
            # for line in attachment.line_ids:
            #     if line.name and not line.order_line_id:
            #         prefix = line.name[:40]
            #         line.order_line_id = self.env['building.order.line'].search([
            #             ('name', '=like', prefix + '%'),   # exact start with prefix
            #             ('order_id', '=', building_order.id)
            #         ], limit=1)

                # order_lines = self.env['building.order.line'].search([
                #     ('name', '=', line.name),
                #     ('order_id', '=', building_order.id)
                # ], order='id asc')

                # order_lines_attachment = attachment.line_ids.filtered(lambda l: l.name == line.name)
                # order_lines_attachment = order_lines_attachment.sorted('id')

                # find index of the current line in the sorted attachment lines
                # ids_list = order_lines_attachment.ids
                # if line.id in ids_list:
                #     index = ids_list.index(line.id)  # index starts from 0
                #     if index < len(order_lines):
                #         line.order_line_id = order_lines[index].id
                #     else:
                #         line.order_line_id = False
                # else:
                #     line.order_line_id = False


class building_attachment_line(models.Model):
    
    _name="building.attachment.line"

    @api.depends('price_unit', 'tax_id', 'qty', 'cumulative_quantity', 'current_quantity', 'previous_quantity', 'product_id', 'attachment_id.partner_id')
    def _compute_price(self):
        currency = self.env.user.company_id.currency_id
        for line in self:
            price = line.price_unit
            taxes1 = line.tax_id.compute_all(price_unit=price, currency=currency, quantity=line.qty, product=line.product_id, partner=line.attachment_id.partner_id)
            taxes2 = line.tax_id.compute_all(price_unit=price, currency=currency, quantity=line.current_quantity, product=line.product_id, partner=line.attachment_id.partner_id)
            taxes3 = line.tax_id.compute_all(price_unit=price, currency=currency, quantity=line.previous_quantity, product=line.product_id, partner=line.attachment_id.partner_id)
            taxes4 = line.tax_id.compute_all(price_unit=price, currency=currency, quantity=line.cumulative_quantity, product=line.product_id, partner=line.attachment_id.partner_id)

            line.price_subtotal = taxes1['total_excluded']
            line.current_price_subtotal = taxes2['total_excluded']
            line.previous_price_subtotal = taxes3['total_excluded']
            line.cumulative_price_subtotal = taxes4['total_excluded']

    name = fields.Char('Nom', size=256, required=False, readonly=False)
    attachment_id = fields.Many2one('building.attachment','Attachement')
    product_id = fields.Many2one('product.product','Produit')
    price_unit = fields.Float(string='PU', required=True)
    price_subtotal = fields.Float(string='Montant',store=True, readonly=True, compute='_compute_price')
    tax_id = fields.Many2many('account.tax', 'building_attachment_line_tax', 'attachment_line_id', 'tax_id', 'Taxes', readonly=False)
    product_uom_id = fields.Many2one('uom.uom','UDM')
    qty = fields.Float('Qantité', digits=(16,3))
    line_dqe_id = fields.Many2one('building.order.line','Lignes de BP')
    line_subcontracting_id = fields.Many2one('building.subcontracting.line','Lignes sous traitance')
    # price_quantity = fields.Float('Qté BDP')
    price_quantity = fields.Float('Qté BDP', related="order_line_id.quantity")
    percentage_completion = fields.Float('% Avance', compute="_compute_percentage_completion")
    cumulative_quantity = fields.Float('Qté Cum.')
    current_quantity = fields.Float('Qté courant')
    previous_quantity = fields.Float('Qté préc')
    current_price_subtotal = fields.Float(string='Montant Courant',store=True, readonly=True, compute='_compute_price')
    cumulative_price_subtotal = fields.Float(string='Mnt Cumulé',store=True, readonly=True, compute='_compute_price')
    previous_price_subtotal = fields.Float(string='Montant Précedent',store=True, readonly=True, compute='_compute_price')
    chapter = fields.Char('Code', size=2048, required=False, readonly=False)
    display_type = fields.Selection([
        ('line_chapter', "Chapitre"),
        ('line_sub_chapter', "Sous Chapitre"),
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    sequence = fields.Integer(string='Sequence', default=10)
    order_line_id = fields.Many2one('building.order.line', 'Details BP')
    amount_invoiced_tva = fields.Float(compute='_compute_amount_invoiced_tva')
            
    @api.onchange('cumulative_quantity')
    def _onchange_cumulative_quantity(self):
        for rec in self:
            if rec.cumulative_quantity < rec.previous_quantity:
                raise ValidationError(f"La quantité cumulée saisie est inférieure à la quantité décomptes précédents.")

            if rec.cumulative_quantity > rec.price_quantity and rec.attachment_id.site_id.type_marche == "forfait":
                raise ValidationError(f"Produit: {rec.name}\nLa quantité cumulée saisie {rec.cumulative_quantity:.2f} dépasse celle définie sur le BP {rec.price_quantity:.2f}.")

    @api.depends('cumulative_quantity', 'price_quantity')
    def _compute_percentage_completion(self):
        for rec in self:
            if rec.price_quantity:
                rec.percentage_completion = (rec.cumulative_quantity / rec.price_quantity) * 100
            else:
                rec.percentage_completion = 0

    @api.depends('cumulative_price_subtotal')
    def _compute_amount_invoiced_tva(self):
        for line in self:
            tax_rate = line.tax_id.amount or 0.0
            line.amount_invoiced_tva = (line.cumulative_price_subtotal * tax_rate) / 100
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        product_uom_obj = self.env['uom.uom']
        if self.product_id:
            self.tax_id = self.env['account.fiscal.position'].map_tax(self.product_id.taxes_id)
            self.product_uom_id = self.product_id.uom_id.id

    @api.onchange('previous_quantity', 'current_quantity')
    def _onchange_current_quantity(self):
        if self.current_quantity:
            cumulative_quantity = self.current_quantity + self.previous_quantity
            self.cumulative_quantity = cumulative_quantity

    @api.onchange('previous_quantity', 'cumulative_quantity')
    def onchange_cumulative_quantity(self):
        self.current_quantity = self.cumulative_quantity - self.previous_quantity
