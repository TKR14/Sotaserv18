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

class building_amendment_create(models.TransientModel):
    
    _name = 'building.amendment.create'
    
    site_id = fields.Many2one('building.site', 'Affaire')
    order_id = fields.Many2one('building.order', 'BP')
    commercial_id = fields.Many2one('res.users', 'Commercial')
    line_ids = fields.One2many('building.amendment.create.line', 'line_id', 'Articles')

    @api.model
    def default_get(self,fields):
        if self._context is None: self._context = {}
        res = super(building_amendment_create, self).default_get(fields)
        site_id = self._context.get('active_id', [])
        orders = self.env['building.order'].search([('site_id','=',site_id), ('state','=','approved')], order='id desc')
        lines = []
        if orders:
            border = None
            for order in orders :
                border = order
                for line in order.order_line:
                    record_line = {}
                    if not line.display_type:
                        record_line = {
                            'product_id': line.product_id.id if line.product_id else False,
                            'name': line.name,
                            'product_uom_id': line.product_uom.id,
                            'order_line_id':line.id,
                            'quantity' : 0,
                            'price_unit':line.price_unit,
                        }
                        lines.append((0, 0, record_line))
            res.update(line_ids=lines, site_id=site_id, order_id=border.id, commercial_id=border.commercial_id.id)
        return res

    def _get_information_partner(self, part):
        val = {}
        if not part:
            return val
        part = self.env['res.partner'].browse(part)
        dedicated_salesman = part.user_id and part.user_id.id or self.env.user.id
        if part.child_ids :
            for contact in part.child_ids :
                if contact.type == 'invoice' :
                    partner_invoice_id = contact.id
                    partner_invoice_address = contact.contact_address
                    val = {
                            'user_id': dedicated_salesman,
                            'partner_invoice_address': partner_invoice_address,
                            'partner_invoice_id':partner_invoice_id,
                            'customer_order_ref':part.ref,
                        }
                else :
                    partner_invoice_id = part.id
                    partner_invoice_address = part.contact_address
                    val = {
                                'user_id': dedicated_salesman,
                                'partner_invoice_address': partner_invoice_address,
                                'partner_invoice_id':partner_invoice_id,
                                'customer_order_ref':part.ref,
                            }
        else :
            partner_invoice_id = part.id
            partner_invoice_address = part.contact_address
            val = {
                    'user_id': dedicated_salesman,
                    'partner_invoice_address': partner_invoice_address,
                    'partner_invoice_id':partner_invoice_id,
                    'customer_order_ref':part.ref,
                    }
        return val

    def create_amendment(self):
        order_obj = self.env['building.order']
        order_line_obj = self.env['building.order.line']
        # site_id = self._context.get('active_id', [])
        sequ = self.env['ir.sequence'].get('building.order') or '/'
        record_order = {
                        'partner_id':self.order_id.partner_id.id,
                        'origin':self.site_id.number,
                        'commercial_id':self.commercial_id.id,
                        'ref_tendering':self.order_id.ref_tendering,
                        'amendment':True,
                        'site_id':self.site_id.id,
                        'customer_order_ref':self.order_id.partner_id.ref,
                        'name':sequ,
                        }
        vals = self._get_information_partner(self.order_id.partner_id.id)
        record_order['user_id'] = vals['user_id']
        record_order['partner_invoice_address'] = vals['partner_invoice_address']
        record_order['partner_invoice_id'] = vals['partner_invoice_id']

        
        lines = []
        for line in self.line_ids :
            record_order_line = {
                                 'product_id':line.product_id.id if line.product_id else False,
                                 'code':line.order_line_id.price_number,
                                 'price_number':line.price_number,
                                 'name':line.name,
                                 'calculated_sales_price':line.price_unit,
                                 'price_unit':line.price_unit,
                                 # 'type': 'product',
                                 'quantity':line.quantity,
                                 'tax_id':[(6, 0, [tax.id for tax in line.product_id.taxes_id])],
                                 'product_uom':line.product_uom_id.id,
                                 }
            if line.order_line_id.origin_id :
                record_order_line['origin_id'] = line.order_line_id.origin_id.id
            lines.append((0, 0, record_order_line))
            # order_line_obj.create(record_order_line)
        record_order['order_line'] = lines
        order = order_obj.create(record_order)
        order.action_gained()
        domain = [('id', '=', order.id)]
        return {
            'name': _('Avenant'),
            'domain': domain,
            'res_model': 'building.order',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'limit': 80,
            }


class building_amendment_create_line(models.TransientModel):
    _name = 'building.amendment.create.line'

    name = fields.Char('Description',size=4096)
    price_number = fields.Char('Description',size=4096)
    line_id = fields.Many2one('building.amendment.create', 'Contrat')
    product_id = fields.Many2one('product.product', 'Product')
    price_unit = fields.Float('Prix', digits=(16,3))
    product_uom_id = fields.Many2one('uom.uom', 'Unité')
    quantity = fields.Float('Quantity', default = 1.0)
    order_line_id = fields.Many2one('building.order.line', 'Details BP')

    @api.onchange('product_id')
    def onchange_current_quantity(self):
        if self.product_id :
            self.product_uom_id = self.product_id.uom_id.id
            self.name = self.product_id.name


