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
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import time

class building_request_purchase(models.TransientModel):
    
    _name = 'building.request_purchase'

    def _get_domain_order(self):
        site_id = self._context.get('active_id', [])
        domain = [('site_id','=',site_id)]
        return domain

    site_id = fields.Many2one('building.site', 'Affaire')
    order_id = fields.Many2one('building.order', 'BP',domain=_get_domain_order)
    request_purchase_ids = fields.One2many('building.request_purchase.line', 'line_id', 'Articles')
    partner_id = fields.Many2one('res.partner', 'Fournisseur', required=False,domain=[('supplier','=',True)])

    @api.model
    def default_get(self,fields):
        if self._context is None: self._context = {}
        res = super(building_request_purchase, self).default_get(fields)
        site_id = self._context.get('active_id', [])
        request_purchase_lines = []
        if self.site_id:
            building_needs = self.env['building.purchase.need.line'].search([('site_id', '=', self.site_id.id)])
            # analytic_account = self.env['account.analytic.account'].search([('account_analytic_type', '=' , 'material')])
            if building_needs:
                for need in building_needs:
                    request_purchase_line = {
                        'product_id': need.product_id.id,
                        'product_uom_id': need.uom_id.id,
                        'quantity' : need.quantity,
                        'price_unit' : need.product_id.standard_price,
                        # 'analytic_id':analytic_account.id
                    }
                    request_purchase_lines.append((0, 0, request_purchase_line))
        res.update(request_purchase_ids=request_purchase_lines, site_id=site_id)
        return res

    @api.onchange('site_id')
    def onchange_site_id(self):
        request_purchase_lines = []
        if self.site_id:
            building_needs = self.env['building.purchase.need.line'].search([('site_id', '=', self.site_id.id)])
            # analytic_account = self.env['account.analytic.account'].search([('account_analytic_type', '=' , 'material')])
            if building_needs:
                for need in building_needs:
                    request_purchase_line = {
                        'product_id': need.product_id.id,
                        'product_uom_id': need.uom_id.id,
                        'quantity' : need.quantity,
                        'price_unit' : need.product_id.standard_price,
                        # 'analytic_id':analytic_account.id
                    }
                    request_purchase_lines.append((0, 0, request_purchase_line))
        self.request_purchase_ids = request_purchase_lines

    def create_request_purchase(self):

        request_purchase_obj = self.env['purchase.request']
        request_purchase_line_obj = self.env['purchase.request.line']
        fiscal_position_obj = self.env['account.fiscal.position']
        picking_type_id = request_purchase_obj.default_get(['picking_type_id'])['picking_type_id']
        lines = []
        for request_purchase_line in self.request_purchase_ids :
            product = request_purchase_line.product_id
            default_uom_po_id = product.uom_po_id.id
            taxes_ids = product.supplier_taxes_id
            taxes = fiscal_position_obj.map_tax(taxes_ids)
            date_planned = datetime.today()
            request_purchase_line_record ={
                                     'name': product.name,
                                     'product_id': product.id,
                                     'product_uom_id':request_purchase_line.product_id.uom_po_id.id,
                                     'product_qty': request_purchase_line.quantity,
                                     'estimated_cost': product.standard_price,
                                     'date_required': date_planned,
                                     # 'analytic_account_id': request_purchase_line.analytic_id.id or False,
                                     'purchase_state': 'draft'
                                 }
            lines.append((0, 0, request_purchase_line_record))
        request_purchase_record = {
             'origin': self.order_id.name,
             'site_id': self.site_id.id,
             'order_id': self.order_id.id,
             'requested_by': self.env.user.id,
             'line_ids': lines
            }
        request_purchase_new = request_purchase_obj.create(request_purchase_record)

        domain = [('id', '=', request_purchase_new.id)]
        return {
            'name': _('Demande d''Achat'),
            'domain': domain,
            'res_model': 'purchase.request',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'list,form',
            'limit': 80,
            }


class building_request_purchase_line(models.TransientModel):
    _name = 'building.request_purchase.line'

    line_id = fields.Many2one('building.request_purchase', 'Achat')
    product_id = fields.Many2one('product.product', 'Product')
    price_unit = fields.Float('Prix', digits=(16,3))
    product_uom_id = fields.Many2one('uom.uom', 'Unité')
    quantity = fields.Float('Quantity', default = 1.0)
    # analytic_id = fields.Many2one('account.analytic.account','Compte analytique')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_po_id.id,

class building_request_price(models.TransientModel):
    
    _name = 'building.request_price'

    def _get_domain_order(self):
        site_id = self._context.get('active_id', [])
        domain = [('site_id','=',site_id)]
        return domain

    
    site_id = fields.Many2one('building.site', 'Affaire')
    order_id = fields.Many2one('building.order', 'BP',domain=_get_domain_order)
    request_price_ids = fields.One2many('building.request_price.line', 'line_id', 'Articles')
    partner_id = fields.Many2one('res.partner', 'Fournisseur', required=False,domain=[('supplier','=',True)])

    @api.model
    def default_get(self,fields):
        if self._context is None: self._context = {}
        res = super(building_request_price, self).default_get(fields)
        site_id = self._context.get('active_id', [])
        request_price_lines = []
        # analytic_account = self.env['account.analytic.account'].search([('account_analytic_type', '=' , 'material')])
        if self.site_id:
            building_needs = self.env['building.purchase.need.line'].search([('site_id', '=', self.site_id.id)])
            if building_needs:
                for need in building_needs:
                    request_price_line = {
                        'product_id': need.product_id.id,
                        'product_uom_id': need.uom_id.id,
                        'quantity' : need.quantity,
                        'price_unit' : need.product_id.standard_price,
                        # 'analytic_id': analytic_account.id
                    }
                    request_price_lines.append((0, 0, request_price_line))
        if self._context['active_model'] == 'product.template' and self._context.get('active_ids', []):
                products = self._context.get('active_ids', [])
                for product_id in products:
                    product_tmpl = self.env['product.template'].search([('id', '=', product_id)])
                    product = self.env['product.product'].search([('product_tmpl_id', '=', product_id)])
                    request_price_line = {
                        'product_id': product.id,
                        'product_uom_id': product_tmpl.uom_id.id,
                        'quantity' : 0,
                        'price_unit' : product_tmpl.standard_price,
                        # 'analytic_id': analytic_account.id
                    }
                    request_price_lines.append((0, 0, request_price_line))

        res.update(request_price_ids=request_price_lines, site_id=site_id)
        return res

    @api.onchange('site_id')
    def onchange_site_id(self):
        request_price_lines = []
        if self.site_id:
            building_needs = self.env['building.purchase.need.line'].search([('site_id', '=', self.site_id.id)])
            # analytic_account = self.env['account.analytic.account'].search([('account_analytic_type', '=' , 'material')])
            if building_needs:
                for need in building_needs:
                    request_price_line = {
                        'product_id': need.product_id.id,
                        'product_uom_id': need.uom_id.id,
                        'quantity' : need.quantity,
                        'price_unit' : need.product_id.standard_price,
                        # 'analytic_id':analytic_account.id
                    }
                    request_price_lines.append((0, 0, request_price_line))
        self.request_price_ids = request_price_lines

    def create_request_price(self):

        purchase_obj = self.env['purchase.order']
        fiscal_position_obj = self.env['account.fiscal.position']
        dict_request_price_by_partner = {}
        dict_request_price_line_by_partner = {}
        for request_price_line in self.request_price_ids :
            product = request_price_line.product_id
            default_uom_po_id = product.uom_po_id.id
            taxes_ids = product.supplier_taxes_id
            taxes = fiscal_position_obj.map_tax(taxes_ids)
            date_planned = datetime.today()
            print (product.name)
            print (product.seller_ids)
            for partner in product.seller_ids :
                # supplier_pricelist = partner.name.property_product_pricelist_purchase or False
                if partner.name.id not in dict_request_price_by_partner:
                    dict_request_price_by_partner[partner.name.id] = []
                    request_price_record = {
                        'partner_id': partner.name.id,
                        'origin': self.order_id.name,
                        'site_id': self.site_id.id,
                        'dqe_id': self.order_id.id,
                        'date_planned': date_planned,
                        # 'pricelist_id': supplier_pricelist.id,
                        'purchase_type': 'material',
                    }
                    dict_request_price_by_partner[partner.name.id].append(request_price_record)

                if partner.name.id not in dict_request_price_line_by_partner:
                    dict_request_price_line_by_partner[partner.name.id] = []

                request_price_line_record = {
                                        'name': product.name,
                                        'product_id': product.id,
                                        'product_uom': request_price_line.product_id.uom_po_id.id,
                                        'product_qty': request_price_line.quantity,
                                        'price_unit': product.standard_price,
                                        'date_planned': date_planned,
                                        'taxes_id': [(6, 0, [tax.id for tax in taxes])],
                                        # 'account_analytic_id': request_price_line.analytic_id.id or False,
                                     }
                dict_request_price_line_by_partner[partner.name.id].append((0, 0, request_price_line_record))
        
        request_price_ids = []
        print (dict_request_price_by_partner)
        for partner_id, list_row in dict_request_price_by_partner.items():
            for row in list_row:
                row['order_line'] = dict_request_price_line_by_partner[partner_id]
                print (row)
                purchase_new = purchase_obj.create(row)
                request_price_ids.append(purchase_new.id)

        domain = [('id', 'in', request_price_ids)]
        return {
            'name': _('Demande de prix'),
            'domain': domain,
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'list,form',
            'limit': 80,
            }


class building_request_price_line(models.TransientModel):
    _name = 'building.request_price.line'

    line_id = fields.Many2one('building.request_price', 'Achat')
    product_id = fields.Many2one('product.product', 'Product')
    price_unit = fields.Float('Prix', digits=(16,3))
    product_uom_id = fields.Many2one('uom.uom', 'Unité')
    quantity = fields.Float('Quantity', default = 1.0)
    # analytic_id = fields.Many2one('account.analytic.account','Compte analytique')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_po_id.id,
