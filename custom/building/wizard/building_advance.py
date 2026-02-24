
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

import datetime
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError

class building_advance_inv(models.TransientModel):
    
    _name = "building.advance.inv"
    _description = "Acompte"
    
    def _get_percentage_amount(self):
        site_id = self._context.get('active_id', [])
        site = self.env['building.site'].browse(site_id)
        return site.deposit_number

    advance_payment_method = fields.Selection(
            [('percentage','Pourcentage'), ('fixed','Prix fixe (depot)')],'Méthode Acompte', required=True,
            help="""
                Utilisez Pourcentage pour facturer un pourcentage du montant total.
                Utilisez Prix fixe pour facturer en avance un montant spécifique.
                """,default='percentage')
    qtty = fields.Float('Quantité', digits=(16, 2), required=True, default=1.0)
    amount = fields.Float('Montant Acompte', help="le montant à facturer dans l'acompte.")
    site_id = fields.Many2one('building.site','Affaire')
    tax_id = fields.Many2one('account.tax', 'Taxe', domain=[('type_tax_use', '=', 'sale')])

    @api.model
    def default_get(self, fields):
        if self._context is None: self._context = {}
        res = super(building_advance_inv, self).default_get(fields)
        site_id = self._context.get('active_id', [])
        res.update(site_id = site_id)
        return res

    @api.onchange('advance_payment_method', 'site_id')
    def _onchange_advance_payment_method(self):
        self.amount = 0
        if self.advance_payment_method == 'percentage' :
            if self.site_id :
                amount = self.site_id.deposit_number
                self.amount = amount

    def _prepare_advance_invoice_vals(self):
        if self._context is None:
            self._context = {}
        site_obj = self.env['building.site']
        ir_property_obj = self.env['ir.property']
        fiscal_obj = self.env['account.fiscal.position']
        inv_line_obj = self.env['account.move.line']
        site_id = self._context.get('active_id', [])
        result = []
        site = site_obj.browse(site_id)
        order = self.env['building.order'].search([('site_id','=',site_id), ('state','=','approved')], order='id desc', limit=1)

        if not order :
            raise UserError(_("Erreur:BP n\'existe pas!: Pas de Bordereau des prix définit pour le Affaire"))

        res = {}
        # determine and check income account
        account_accompte_id = self.env['account.account'].search([('code', '=', 442100)])
        res['account_id'] = account_accompte_id.id
        if not res.get('account_id'):
            raise UserError(_("Erreur de Configuration!: Pas de compte définit pour l'Acompte"))

        # determine invoice amount
        if self.amount <= 0.00:
            raise UserError(_("Donnée n\'est pas correct: Montant Acompte doit etre positif."))

        if self.advance_payment_method == 'percentage':
            inv_amount = order.amount_total * self.amount
            if not res.get('name'):
                res['name'] = _("Acompte %s %%") % (self.amount*100)
        else:
            inv_amount = self.amount
            if not res.get('name'):
                symbol = self.env.user.company_id.currency_id.symbol
                if self.env.user.company_id.currency_id.currency_id.position == 'after':
                    res['name'] = _("Acompte  %s %s") % (inv_amount, symbol)
                else:
                    res['name'] = _("Acompte  %s %s") % (symbol, inv_amount)

        # create the invoice
        inv_line_values = {
            'name': res.get('name'),
            'account_id': res['account_id'],
            'price_unit': inv_amount,
            'quantity': self.qtty or 1.0,
            'discount': False,
            'tax_ids': False,
        }
        inv_values = {
            'name': order.customer_order_ref or order.name,
            'invoice_origin': order.name,
            'move_type': 'out_invoice',
            'ref': order.customer_order_ref,
            'invoice_type':'specific',
            'narration': order.note,
            'partner_id': order.partner_id.id,
            'currency_id': self.env.user.company_id.currency_id.id,
            'payment_reference': '',
            'invoice_line_ids': [(0, 0, inv_line_values)],
            'invoice_advance':True,
            'site_id':site_id,
            'order_id':order.id,
        }
        result.append((order.id, inv_values))
        return result

    def _create_invoices(self, inv_values, order_id):
        inv_obj = self.env['account.move']
        order_obj = self.env['building.order']
        inv_id = inv_obj.create(inv_values)
        order = order_obj.search([('id', '=', order_id)])
        return inv_id.id

    
    def create_invoices(self):
        """ create invoices for the active sales orders """
        order_obj = self.env['building.order']
        act_window = self.env['ir.actions.act_window']
        site_id = self._context.get('active_id', [])
        site = self.env['building.site'].search([('id', '=', site_id)])
        order = order_obj.search([('site_id','=',site_id),('state', '=' , 'approved')], order='id desc', limit=1)
        site.write({'advance_invoiced': True})
        assert self.advance_payment_method in ('fixed', 'percentage')

        inv_ids = []
        for order_id, inv_values in self._prepare_advance_invoice_vals() :
            inv_ids.append(self._create_invoices(inv_values, order_id))

        if self._context.get('open_invoices', False):
            return self.open_invoices(inv_ids)
        return {}

    def open_invoices(self,invoice_ids):
        
        def get_view_id(xid, name):
            try:
                return self.env['ir.model.data'].xmlid_to_res_id('account.' + xid, raise_if_not_found=True)
            except ValueError:
                try:
                    return self.env['ir.ui.view'].search([('name', '=', name)], limit=1).id
                except Exception:
                    return False    # view not found

        """ open a view on one of the given invoice_ids """
        form_id = get_view_id('invoice_form', 'account.move.form')
        tree_id = get_view_id('invoice_tree', 'account.move.tree')

        return {
            'name': _('Facture Acompte'),
            'view_type': 'form',
            'view_mode': 'form,list',
            'res_model': 'account.move',
            'res_id': invoice_ids[0],
            'view_id': False,
            'views': [(form_id, 'form'), (tree_id, 'list')],
            'context': "{'type': 'out_invoice'}",
            'type': 'ir.actions.act_window'
        }


class building_advance_inv_supplier(models.TransientModel):

    _name = "building.advance.inv.supplier"
    _description = "Acompte Sous Traitant"

    def _get_percentage_amount(self):
        subcontracting_id = self._context.get('active_id', [])
        subcontracting_id = self.env['building.subcontracting'].browse(subcontracting_id)
        return subcontracting_id.deposit_number



    qtty = fields.Float('Quantité', digits=(16, 2), required=True,default=1.0)
    amount = fields.Float('Montant Acompte', help="le montant à facturer dans l'acompte.")
    subcontracting_id = fields.Many2one('building.subcontracting','Contrat')
    tax_id = fields.Many2one('account.tax', 'Taxe',domain=[('type_tax_use','=','purchase')])

    @api.model
    def default_get(self,fields):
        if self._context is None: self._context = {}
        res = super(building_advance_inv_supplier, self).default_get(fields)
        subcontracting_id = self._context.get('active_id', [])
        res.update(subcontracting_id=subcontracting_id)
        return res

    def _prepare_advance_invoice_vals(self):
        if self._context is None:
            self._context = {}
        subcontracting_id = self._context.get('active_id', [])
        order = self.env['building.subcontracting'].browse(subcontracting_id)

        inv_amount = order.amount_total * self.amount
        account_accompte_id = self.env['account.account'].search([('code','=',442100)])
        # create the invoice
        inv_line_values = {
            'name': _("Acompte %s %%") % (self.amount*100),
            'origin': order.name,
            'account_id': account_accompte_id.id,
            'price_unit': inv_amount,
            'quantity': self.qtty or 1.0,
            'discount': False,
            'uos_id': False,
            'product_id': False,
            'invoice_line_tax_id': False,
        }
        inv_values = {
            'name': order.name,
            'origin': order.name,
            'type': 'in_invoice',
            'reference': False,
            'invoice_type':'specific',
            'account_id': order.partner_id.property_account_payable.id,
            'partner_id': order.partner_id.id,
            'invoice_line': [(0, 0, inv_line_values)],
            'currency_id': order.currency_id.id,
            'comment': '',
            'fiscal_position': order.partner_id.property_account_position.id,
            'invoice_advance':True,
            'site_id':order.site_id.id,
            'order_id':order.origin_id.id,
        }
        return inv_values

    def create_invoices(self):
        """ create invoices for the active purchase orders """
        invoice_obj = self.env['account.move']
        order_obj = self.env['building.subcontracting']
        subcontracting_id = self._context.get('active_id', [])
        order = order_obj.browse(subcontracting_id)
        order.write({'advance_created':True})
        invoice_obj.create(self._prepare_advance_invoice_vals())
        return {}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
