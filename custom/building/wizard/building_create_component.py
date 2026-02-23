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

import datetime
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import tools
from openerp.tools.translate import _
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp

class building_component(models.TransientModel):
    
    _name = "building.component"
    _description = "Composants"

    type = fields.Selection([('component','Composant'),('price','Prix')], string='Type de la ligne', default='price',required=False)
    component_line_ids = fields.One2many('building.component.line','component_id', 'Composants')
    component_line_2_ids = fields.One2many('building.component.line', 'component_id', 'Composants')

    @api.multi
    def create_component(self):
        
        parent_id = self._context.get('active_id', [])
        parent = self.env['building.price.calculation.line'].browse(parent_id)
        for line in self.component_line_ids :
                record_component = {
                                        'name': line.name,
                                        'price_calculation_id':parent.price_calculation_id.id,
                                        'type':self.type,
                                        'code':line.name,
                                        'parent_id':parent.id,
                                        }
                if self.type == 'price' and line.quantity != 0 :
                    record_component['product_uom'] = line.product_uom.id
                    record_component['quantity'] = line.quantity
                    record_component['price_number'] = line.price_number

                self.env['building.price.calculation.line'].create(record_component)
        return {'type': 'ir.actions.act_close_wizard_and_reload_view'}

    @api.multi
    def create_chapter(self):
        price_calculation_id = self._context.get('active_id', [])
        for line in self.component_line_ids:
            record_chapter = {
                'name': line.name,
                'price_calculation_id': price_calculation_id,
                'type': 'chapter',
                'code': line.name,
            }
            self.env['building.price.calculation.line'].create(record_chapter)
        return {'type': 'ir.actions.act_close_wizard_and_reload_view'}


class building_component_line(models.TransientModel):

    _name = "building.component.line"
    _description = "Composants"

    name = fields.Char('Designation', size=1024, readonly=False)
    price_number = fields.Char('N° de prix',required=False)
    parent_id = fields.Many2one('building.price.calculation.line', 'Parent')
    component_id = fields.Many2one('building.component', 'Composants')
    product_uom = fields.Many2one('product.uom', 'Unité de mésure ', required=False, readonly=False)
    quantity = fields.Float(string='Quantité', digits= dp.get_precision('Product Unit of Measure'),required=True, default=1)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: