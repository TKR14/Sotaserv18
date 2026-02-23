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

import itertools
from lxml import etree
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import datetime

class account_invoice(models.Model):
    
    _inherit = 'account.move'
    
    @api.depends('deposit_number', 'guaranty_number', 'assurance_number', 'invoice_line_ids.price_subtotal', 'invoice_line_ids.current_price_subtotal', 'invoice_line_ids.cumulative_price_subtotal', 'invoice_line_ids.previous_price_subtotal')
    def _compute_other_amount(self):
        for inv in self:
            if inv.order_id :
                invoice = self.search([('site_id', '=' , inv.site_id.id), ('order_id', '=' , inv.order_id.id), ('state', '!=', 'draft')], order='id desc', limit=1)
            if inv.subcontracting_id :
                invoice = self.search([('site_id' , '=' , inv.site_id.id), ('subcontracting_id', '=' , inv.subcontracting_id.id), ('id', '!=', inv.id)], order='id desc', limit=1)

            if inv.invoice_type == 'specific' and inv.invoice_attachment:
                inv.cumulative_amount_untaxed = sum(line.cumulative_price_subtotal for line in inv.invoice_line_ids)
                inv.amount_previous_untaxed = sum(line.previous_price_subtotal for line in inv.invoice_line_ids)
                inv.amount_current_untaxed = sum(line.current_price_subtotal for line in inv.invoice_line_ids)
                inv.amount_current = inv.amount_current_untaxed + inv.amount_tax
                inv.amount_guaranty = inv.amount_current*inv.guaranty_number
                inv.amount_deposit = inv.amount_current*inv.deposit_number
                inv.amount_to_paid = inv.amount_current - (inv.amount_guaranty+inv.amount_deposit)
                if inv.amount_previous_untaxed != 0 and invoice:
                    inv.amount_previous = invoice.cumulative_amount
                if inv.amount_previous_untaxed == 0  :
                    inv.amount_previous = 0
                inv.cumulative_amount = inv.cumulative_amount_untaxed + inv.amount_tax
                # inv.amount_total = inv.amount_to_paid
            else :
                inv.cumulative_amount_untaxed = 0
                inv.amount_previous_untaxed = 0
                inv.amount_current_untaxed = 0
                inv.cumulative_amount = 0
                inv.amount_previous = 0
                inv.amount_current = 0
                inv.amount_guaranty = 0
                inv.amount_deposit = 0
                inv.amount_assurance = 0
                inv.amount_to_paid = 0

    site_id = fields.Many2one('building.site','Affaire')
    order_id = fields.Many2one('building.order','BP')
    subcontracting_id = fields.Many2one('building.subcontracting', 'Contrat sous-traitance')
    attachment_id = fields.Many2one('building.attachment', 'Attachement')
    invoice_type = fields.Selection([('standard','Standard'),('specific','Specific')], string="Type", default='')
    categ_invoice = fields.Selection([('workforce','Main-d’œuvre'),('material','Fourniture'),('equipment','Matériel'),('service','Service'),('load','Charge')], string="Type de facture", default='')
    last_attachment = fields.Boolean('Dernier attachement')
    invoice_advance = fields.Boolean('Facture Acompte')
    invoice_attachment = fields.Boolean('Facture Attachement')
    invoice_caution = fields.Boolean('Facture Caution')
    invoice_workforce = fields.Boolean('Facture Main-d’œuvre')
    invoice_material = fields.Boolean('Facture Fourniture')
    invoice_equipment = fields.Boolean('Facture Matériel')
    invoice_load = fields.Boolean('Facture de Charge')
    invoice_service = fields.Boolean('Facture de Service')
    deposit_number = fields.Float('Restitution d\'accompte')
    guaranty_number = fields.Float('Rétention de garantie')
    assurance_number = fields.Float('Assurance')
    cumulative_amount = fields.Float(string='Total TTC MONTANT CUMULÉ',
        store=True, readonly=True, compute='_compute_other_amount')
    cumulative_amount_untaxed = fields.Float(string='Total HT MONTANT CUMULÉ',
        store=True, readonly=True, compute='_compute_other_amount')
    amount_previous = fields.Float(string='Total TTC MONTANT DEJA FACTURÉ',
        store=True, readonly=True, compute='_compute_other_amount')
    amount_previous_untaxed = fields.Float(string='MONTANT HT DEJA FACTURÉ',
        store=True, readonly=True, compute='_compute_other_amount')
    amount_current_untaxed = fields.Float(string='MONTANT HT Mois',
        store=True, readonly=True, compute='_compute_other_amount')
    amount_current = fields.Float(string='MONTANT TTC Mois',
        store=True, readonly=True, compute='_compute_other_amount')
    amount_guaranty = fields.Float(string='Restitution de Garantie',
        store=True, readonly=True, compute='_compute_other_amount')
    amount_deposit = fields.Float(string='Restitution d\'Accompte',
        store=True, readonly=True, compute='_compute_other_amount')
    amount_assurance = fields.Float(string='Restitution Assurance',
        store=True, readonly=True, compute='_compute_other_amount')
    amount_to_paid = fields.Float(string='Reste à payer',
        store=True, readonly=True, compute='_compute_other_amount')
    invoice_diesel = fields.Boolean('Facture Gasoil ?')


    def _move_invoice_lines_deposit_and_guaranty_create(self, inv):
        if inv.invoice_type == 'specific' and inv.invoice_attachment and inv.move_type == 'out_invoice':
            account_accompte_id = self.env['account.account'].search([('code' ,'=', 442100)])
            move_line_vals = {
                                    'name': 'Restitution d\'Accompte',
                                    'debit': inv.amount_deposit,
                                    'credit': 0,
                                    'account_id': account_accompte_id.id,
                                    'partner_id': inv.partner_id.id,
                                    'ref': inv.ref,
                                    'date': date,
                                    'currency_id': currency_id,
                                    'amount_currency': direction * (amount_currency or 0.0),
                                    'company_id': self.company_id.id,
                                    'move_id':inv.id,
                                    'move_type': 'entry'
                            }
            
            if inv.site_id:
                move_line_vals['site_id'] = inv.site_id.id
            if inv.order_id:
                move_line_vals['order_id'] = inv.order_id.id

            self.env['account.move.line'].create(move_line_vals)

            account_caution_id = self.env['account.account'].search([('code', '=' , 248640)])
            move_line_vals = {
                                    'name': 'Restitution de Garantie',
                                    'debit': inv.amount_guaranty,
                                    'credit': 0,
                                    'account_id': account_caution_id.id,
                                    'partner_id': inv.partner_id.id,
                                    'ref': inv.ref,
                                    'date': date,
                                    'currency_id': currency_id,
                                    'amount_currency': direction * (amount_currency or 0.0),
                                    'company_id': self.company_id.id,
                                    'move_id':inv.id,
                                    'move_type': 'entry'
                                    }
            if inv.site_id:
                move_line_vals['site_id'] = inv.site_id.id
            if inv.order_id:
                move_line_vals['order_id'] = inv.order_id.id
            self.env['account.move.line'].create(move_line_vals)
            # if inv.move_type == 'in_invoice' :
            #     SIGN = {'out_invoice': -1, 'in_invoice': 1, 'out_refund': 1, 'in_refund': -1}
            #     direction = SIGN[self.type]
            #     date = inv.date
            #     if self._context.get('amount_currency') and self._context.get('currency_id'):
            #         amount_currency = self._context['amount_currency']
            #         currency_id = self._context['currency_id']
            #     else:
            #         amount_currency = False
            #         currency_id = False

            #     if inv.invoice_type == 'specific' and inv.invoice_attachment:

            #         self._cr.execute(""" UPDATE account_move_line SET credit=%s WHERE move_id=%s AND account_id=%s""",(inv.amount_to_paid, inv.move_id.id, inv.account_id.id))
            #         account_accompte_id = self.env['account.account'].search([('code', '=' , 442100)])
            #         move_line_vals = {
            #                                 'name': 'Restitution de Garantie',
            #                                 'debit':0 ,
            #                                 'credit': inv.amount_deposit,
            #                                 'account_id': account_accompte_id.id,
            #                                 'partner_id': inv.partner_id.id,
            #                                 'ref': inv.number,
            #                                 'date': date,
            #                                 'currency_id': currency_id,
            #                                 'amount_currency': direction * (amount_currency or 0.0),
            #                                 'company_id': self.company_id.id,
            #                                 'move_id':inv.move_id.id,
            #                                 'period_id':inv.move_id.period_id.id,
            #                                 }
            #         self.env['account.move.line'].create(move_line_vals)

            #         account_caution_id = self.env['account.account'].search([('code', '=' , 248640)])
            #         move_line_vals = {
            #                                 'name': 'Restitution d\'Accompte',
            #                                 'debit': 0,
            #                                 'credit':inv.amount_guaranty,
            #                                 'account_id': account_caution_id.id,
            #                                 'partner_id': inv.partner_id.id,
            #                                 'ref': inv.number,
            #                                 'date': date,
            #                                 'currency_id': currency_id,
            #                                 'amount_currency': direction * (amount_currency or 0.0),
            #                                 'company_id': self.company_id.id,
            #                                 'move_id':inv.move_id.id,
            #                                 'period_id':inv.move_id.period_id.id,
            #                                 }
            #         self.env['account.move.line'].create(move_line_vals)
        return True
    
    # @api.model_create_multi
    # def create(self, vals):
    #     res = super(account_invoice, self).create(vals)
    #     #self._move_invoice_lines_deposit_and_guaranty_create(res)
    #     return res

    # @api.model_create_multi
    # def create(self, vals):
    #     for val in vals:
    #         if 'invoice' in val.get('move_type', False):
    #         # if val.get('move_type', False) == 'entry':
    #         #     val['invoice_type'] = 'standard'
    #         # else :
    #             # a fiabiliser
    #         # if val['move_type'] == 'out_invoice' and not val['invoice_advance'] and val['invoice_attachment']:
    #         #     move_vals['invoice_type'] = 'production'
    #         # if inv.type == 'in_invoice' :
    #         #     move_vals['invoice_type'] = inv.categ_invoice
    #         #     if inv.invoice_attachment :
    #         #        move_vals['invoice_type'] = 'subcontracting'

    #             # order = self.env['building.order'].search([('site_id','=', val.get('site_id', False)), ('amendment','=', False)], limit=1)
    #             # analytic = self.env['account.analytic.account'].search([('account_analytic_type', '=', val.get('categ_invoice', False)), ('site_id','=', order.site_id.id), ('order_id' ,'=', order.id)], limit=1)
    #             # if val.get('invoice_line_ids', []) and not val.get('invoice_attachment', False):
    #             #     for l in val.get('invoice_line_ids', []):
    #             #         if type(l[2]) == type({}) :
    #             #             l[2]['analytic_account_id'] = analytic.id
    #         elif 'entry' in val.get('move_type', False):
    #             val['site_id'] = self.site_id.id
    #             val['order_id'] = self.order_id.id
    #     res = super(account_invoice, self).create(vals)
    #     # self._move_invoice_lines_deposit_and_guaranty_create(res)
    #     return res

    # def write(self, vals):
    #     res = super(account_invoice, self).write(vals)
    #     for inv in self :
    #         if inv.site_id and not inv.invoice_attachment:
    #             order = self.env['building.order'].search([('site_id', '=', inv.site_id.id), ('amendment', '=', False)], limit=1)
    #             analytic = self.env['account.analytic.account'].search([('account_analytic_type', '=', inv.categ_invoice), ('site_id','=', inv.site_id.id), ('order_id','=', order.id)], limit=1)
    #             for line in inv.invoice_line_ids :
    #                 line.write({'analytic_account_id': analytic.id})
    #     return res

class account_invoice_line(models.Model):
     
    _inherit = 'account.move.line' 
     
    @api.depends('price_unit', 'current_price_unit', 'cumulative_price_unit', 'previous_price_unit', 'cumulative_quantity', 'quantity_counts_previous', 'current_count_quantity')
    def _compute_price_other(self):
        for line in self:
            line.current_price_subtotal = line.current_price_unit*line.current_count_quantity
            line.cumulative_price_subtotal = line.cumulative_price_unit*line.cumulative_quantity
            line.previous_price_subtotal = line.previous_price_unit*line.quantity_counts_previous

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

class account_caution(models.Model):

    _inherit = 'account.caution'

    site_id = fields.Many2one('building.site', string='Dossier', required=False, readonly=False)

    def write(self, vals):
        if 'caution_deposit_date' in vals:
            depoit_date = vals['caution_deposit_date']
            if depoit_date:
                depoit_date = datetime.strptime(depoit_date, "%Y-%m-%d").date()
                if self.type_caution in ['definitif_caution', 'rg_caution']:
                    if not (self.site_id.date_start <= depoit_date <= self.site_id.date_end):
                        raise UserError(_('La date de depot doit etre entre la date de début et la date de fin de l\'Affaire.'))
        res = super(account_caution, self).write(vals)
        return res
