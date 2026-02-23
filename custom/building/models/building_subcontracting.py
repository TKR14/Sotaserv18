
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2010 Tiny SPRL (http://tiny.be). All Rights Reserved
#    
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
import datetime
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')

class building_subcontracting(models.Model):
    
    _name = 'building.subcontracting'
    _description = "Contrat de sous traitance"
    _order = 'id desc'

    @api.depends('order_line.price_subtotal', 'order_line.tax_id.amount')
    def _compute_amount(self):
        self.amount_tax = 0
        self.amount_untaxed = sum(line.price_subtotal for line in self.order_line)
        for line in self.order_line :
            self.amount_tax += sum(tax.amount*line.price_subtotal for tax in line.tax_id)
        self.amount_total = self.amount_untaxed + self.amount_tax

    def _default_company(self):
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        return company_id
    
    def _default_currency(self):
        currency_id = self._context.get('currency_id', self.env.user.company_id.currency_id.id)
        return currency_id

    name = fields.Char('Référence', required=False, copy=False, readonly=True, states={'draft': [('readonly', False)]}, default='/')
    origin = fields.Char('Origine du Document')
    site_id = fields.Many2one('building.site', 'Affaire',track_visibility='onchange')
    origin_id = fields.Many2one('building.order', 'Origine du Document',track_visibility='onchange')
    supplier_order_ref = fields.Char('Référence Fournisseur', copy=False)
    state = fields.Selection([
            ('draft', 'Brouillon'),
            ('confirmed', 'Confirmée'),
            ('approved', 'Approuvée'),
            ('done', 'Terminée'),
            ], 'Statut', readonly=True, index=True, change_default=True,default='draft',track_visibility='always')
    create_date = fields.Datetime('Date de création', readonly=False, select=True)
    date_confirmed = fields.Date('Date de confirmation', readonly=False,copy=False)
    date_approved = fields.Date('Date d\'approbation', readonly=False,copy=False)
    responsible_id = fields.Many2one('res.users', 'Responsable Achat et Marché',track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', 'Fournisseur', readonly=False,required=True, change_default=True,track_visibility='always')
    partner_invoice_id = fields.Many2one('res.partner', 'Adresse de Facturation', readonly=False, required=False)
    partner_invoice_address = fields.Char('Adresse de Facturation', copy=False)
    order_line = fields.One2many('building.subcontracting.line', 'order_id', 'Articles', readonly=False, copy=True)
    invoiced = fields.Boolean(string='Facturé',readonly=True)
    shipped = fields.Boolean(string='Réceptioné',readonly=True)
    note = fields.Text('Description')
    amount_untaxed = fields.Float(string='Montant global Hors Taxes',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = fields.Float(string='Montant de la TVA',store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Float(string='Montant global TVA Comprise',store=True, readonly=True, compute='_compute_amount')
    company_id = fields.Many2one('res.company', 'Société',default=_default_company)
    currency_id = fields.Many2one('res.currency', string='Devise',required=True, readonly=True,default=_default_currency, track_visibility='always')
    product_id = fields.Many2one('product.product', string='Produit',related='order_line.product_id', store=True, readonly=True)
    user_id = fields.Many2one('res.users', string='Commercial', track_visibility='onchange',readonly=False,required=False)
    location_id = fields.Many2one('stock.location', 'Destination', required=False, domain=[('usage','<>','view')], states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]} ),
    is_first_attachment_purchase = fields.Boolean(string='Premier Attachment ?',readonly=True,default=True)
    deposit_number = fields.Float('Restitution d\'accompte',default=0.0)
    guaranty_number = fields.Float('Rétention de garantie',default=0.0)
    with_advance = fields.Boolean('Avec Acompte ?',default=False)
    advance_created = fields.Boolean('Acompte Crée',default=False)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'La référence du document doit etre unique par société!'),
    ]

    @api.onchange('part')
    def _onchange_partner_id(self):   
        if part:
            partner_invoice_address = False
            partner_invoice_id = ''
            customer_order_ref = ''
            part = self.env['res.partner'].browse(part)
            dedicated_salesman = part.user_id and part.user_id.id or self.env.user.id
            if part.child_ids :
                for contact in part.child_ids :
                    if contact.type == 'invoice' :
                        partner_invoice_id = contact.id
                        partner_invoice_address = contact.contact_address
                    else :
                        partner_invoice_id = part.id
                        partner_invoice_address = part.contact_address
            else :
                partner_invoice_id = part.id
                partner_invoice_address = part.contact_address

            self.user_id = dedicated_salesman
            self.partner_invoice_address = partner_invoice_address
            self.partner_invoice_id = partner_invoice_id
            self.supplier_order_ref = part.ref

    def button_dummy(self):
        return True

    def action_confirmed(self):
        date_confirmed = datetime.now().date()
        sequ = self.env['ir.sequence'].get('building.subcontracting') or '/'
        self.write({'state':'confirmed', 'date_confirmed':date_confirmed, 'name':sequ})
        return True

    def action_approved(self):
        date_approved = datetime.now().date()
        self.write({'state':'approved', 'date_approved':date_approved, 'responsible_id':self.env.user.id})
        return True

    def action_done(self):
        self.write({'state':'done'})
        return True

    # @api.model
    # def create(self,vals):
    #     if self._context is None:
    #         self._context = {}
    #     if vals.get('partner_id') and any(f not in vals for f in ['partner_invoice_id']):
    #         defaults = self.onchange_partner_id(vals['partner_id'])['value']
    #         vals = dict(defaults, **vals)
    #     new_id = super(building_subcontracting, self).create(vals)
    #     return new_id


class building_subcontracting_line(models.Model):
    
    _name = 'building.subcontracting.line'
    _description = 'Lignes de sous traitance'
    _order = 'id asc'

    @api.depends('price_unit', 'tax_id', 'quantity','product_id', 'order_id.partner_id')
    def _compute_price(self):
        for line in self:
            taxes = line.tax_id.compute_all(price_unit = line.price_unit, currency = line.company_id.currency_id, quantity = line.quantity, product = line.product_id, partner = line.order_id.partner_id)
            
            line.price_subtotal = taxes['total_included']

    order_id = fields.Many2one('building.subcontracting', 'Référence Contrat', required=True, ondelete='cascade', readonly=True)
    name = fields.Text('Description', required=False, readonly=False)
    product_id = fields.Many2one('product.product', 'Produit', domain=[('sale_ok', '=', True)], change_default=True, readonly=False, ondelete='restrict')
    price_unit = fields.Float(string='Prix Unitaire', required=True)
    price_subtotal = fields.Float(string='Montant', store=True, readonly=True, compute='_compute_price')    
    tax_id = fields.Many2many('account.tax', 'building_subcontracting_line_tax', 'subcontracting_line_id', 'tax_id', 'Taxes', readonly=False)
    quantity = fields.Float(string='Quantité', required=True, default=1)    
    product_uom = fields.Many2one('uom.uom', 'Unité de mésure ', required=False, readonly=False)
    salesman_id = fields.Many2one('res.users', string='Commercial',related='order_id.user_id', store=True, readonly=True)
    order_partner_id = fields.Many2one('res.partner', string='Client',related='order_id.partner_id', store=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Société',related='order_id.company_id', store=True, readonly=True)
    order_line_id = fields.Many2one('building.order.line', 'Details DQE')
    # analytic_id=fields.Many2one('account.analytic.account','Compte analytique')
    chapter = fields.Char('Code', size=2048, required=False, readonly=False)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        product_uom_obj = self.env['uom.uom']
        if self.product_id:
            product = self.env['product.product'].browse(self.product_id)
            self.tax_id = self.env['account.fiscal.position'].map_tax(product.taxes_id)
            self.product_uom = product.uom_id.id
            self.price_unit = product.list_price