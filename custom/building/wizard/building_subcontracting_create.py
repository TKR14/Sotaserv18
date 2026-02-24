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

class building_subcontracting_create(models.TransientModel):
    
    _name = 'building.subcontracting.create'
    
    site_id = fields.Many2one('building.site', 'Affaire')
    order_id = fields.Many2one('building.order', 'BP')
    subcontracting_ids = fields.One2many('building.subcontracting.create.line', 'line_id', 'Articles')
    partner_id = fields.Many2one('res.partner', 'Fournisseur', required=True,domain=[('supplier_rank','>',0)])
    deposit_number = fields.Float('Restitution d\'accompte',default=0.0)
    guaranty_number = fields.Float('Rétention de garantie',default=0.0)
    with_advance = fields.Boolean('Avec Acompte ?',default=False)
    tax_id = fields.Many2one('account.tax', 'Taxe',domain=[('type_tax_use','=','purchase')])



    @api.onchange('order_id')
    def onchange_order_id(self):
        subcontracting_lines = []
        if self.order_id :
            order = self.order_id
            for line in order.order_line:
                if not line.display_type:
                    subcontracting_line = {
                        'product_id': line.product_id.id if line.product_id else False,
                        'product_uom_id': line.product_uom.id,
                        'order_line_id':line.id,
                        'quantity' : line.quantity,
                        'price_unit':line.price_unit,
                        'name':line.name
                    }
                    subcontracting_lines.append((0, 0, subcontracting_line))
            # destination location for customer usage
            self.subcontracting_ids = subcontracting_lines


    def create_contract_outsourcing(self):

        subcontracting_obj = self.env['building.subcontracting']
        subcontracting_line_obj = self.env['building.subcontracting.line']
        fiscal_position_obj = self.env['account.fiscal.position']
        # analytic_account = self.env['account.analytic.account'].search([('account_analytic_type', '=' , 'subcontracting')])
        # site_id = self._context.get('active_id', [])
        # site = self.env['building.site'].browse(site_id)
        list_subcontracting = []
        for line in self.subcontracting_ids :
            product = line.product_id
            default_uom_po_id = product.uom_po_id.id
            taxes_ids = product.supplier_taxes_id
            taxes = fiscal_position_obj.map_tax(taxes_ids)
            date_created= datetime.today()
            chapter = line.order_line_id.price_number
            subcontracting_line_record ={
                                    # 'order_id': subcontracting_new.id,
                                    'name':line.name,
                                    'product_id':line.product_id.id if line.product_id else False,
                                    'quantity':line.quantity,
                                    'product_uom': line.product_uom_id.id,
                                    'price_unit': line.price_unit,
                                    # 'date_created': date_created,
                                    'tax_id': [(6, 0, [self.tax_id.id])],
                                    'order_line_id':line.order_line_id.id,
                                    # 'analytic_id':analytic_account.id,
                                    'chapter': line.order_line_id.price_number
                                 }
            list_subcontracting.append((0, 0, subcontracting_line_record))
            # subcontracting_line_obj.create(subcontracting_line_record)

        subcontracting_record = {
                'origin': self.order_id.name,
                'site_id':self.site_id.id,
                'origin_id':self.order_id.id,
                'partner_id':self.partner_id.id,
                # 'location_id': site.location_id.id,
                'company_id':self.order_id.company_id.id,
                # 'fiscal_position': self.partner_id.property_account_position and self.partner_id.property_account_position.id or False,
                'with_advance':self.with_advance,
                'deposit_number':self.deposit_number,
                'guaranty_number' :self.guaranty_number,
                'order_line':list_subcontracting
             }

        subcontracting_new = subcontracting_obj.create(subcontracting_record)

        domain = [('id', '=', subcontracting_new.id)]
        return {
                'name': _('Contrat de sous-traitance'),
                'domain': domain,
                'res_model': 'building.subcontracting',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'view_mode': 'list,form',
                'view_type': 'form',
                'limit': 80,
            }

class building_subcontracting_create_line(models.TransientModel):
    _name = 'building.subcontracting.create.line'

    name = fields.Char('Description',size=4096)
    line_id = fields.Many2one('building.subcontracting.create', 'Contrat')
    product_id = fields.Many2one('product.product', 'Product')
    price_unit = fields.Float('Prix', digits=(16,3))
    product_uom_id = fields.Many2one('uom.uom', 'Unité')
    quantity = fields.Float('Quantity', default = 1.0)
    order_line_id = fields.Many2one('building.order.line', 'Details BP')
