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

class building_product(models.TransientModel):
    
    _name = "building.product"
    _description = "Produits"
    
    product_line_ids = fields.One2many('building.product.line', 'building_product_id', 'Produits')
    resource_material_ids = fields.One2many('building.resource.material', 'building_product_id', 'Matériaux')
    expendable_ids = fields.One2many('building.expendable', 'building_product_id', 'Consommables')
    resource_human_ids = fields.One2many('building.resource.human', 'building_product_id', 'Mains d\'oeuvre')
    amount_products = fields.Float(string='Déboursé Matériaux', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_meterials = fields.Float(string='Déboursé Matériels', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_expendables = fields.Float(string='Déboursé Consommables', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_humans = fields.Float(string='Déboursé MO', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_total = fields.Float(string='Déboursé Total', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    perc_construction_costs = fields.Float('% Frais de Affaire')
    amount_production_cost = fields.Float(string='Coût de Production', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    perc_special_expenses = fields.Float('% Frais Spéciaux')
    amount_direct_cost = fields.Float(string='Coût Direct', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    perc_general_costs = fields.Float('% Frais Généraux')
    amount_standard_price = fields.Float(string='Coût de Revient', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    margin_benefit = fields.Float('% Bénifice et Aléas', digits=(16, 3))
    sale_price = fields.Float(string='Prix de Vente', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')

    @api.one
    @api.depends('product_line_ids','resource_material_ids','expendable_ids','resource_human_ids','perc_construction_costs','perc_special_expenses','perc_general_costs','margin_benefit')
    def _compute_amount(self):
        self.amount_products = 0
        self.amount_meterials = 0
        self.amount_expendables = 0
        self.amount_humans = 0
        if self.product_line_ids :
            for product in self.product_line_ids :
                self.amount_products += product.quantity*product.price_unit
        if self.resource_material_ids :
            for material in self.resource_material_ids :
                self.amount_meterials += material.quantity*material.price_unit
        if self.expendable_ids:
            for expendable in self.expendable_ids :
                self.amount_expendables += expendable.quantity*expendable.price_unit
        if self.resource_human_ids :
            for human in self.resource_human_ids :
                self.amount_humans += human.quantity*human.price_unit
        self.amount_total = self.amount_products+self.amount_meterials+self.amount_expendables+self.amount_humans
        amount_production_cost = (self.amount_total*self.perc_construction_costs)/100
        self.amount_production_cost = self.amount_total+amount_production_cost
        amount_direct_cost = (self.amount_total * self.perc_special_expenses) / 100
        self.amount_direct_cost = amount_direct_cost+self.amount_production_cost
        amount_standard_price = (self.amount_total * self.perc_general_costs) / 100
        self.amount_standard_price = amount_standard_price+self.amount_direct_cost
        self.sale_price = (100+self.margin_benefit)*(self.amount_standard_price/100)


    @api.multi
    def create_product(self):
        
        line_id = self._context.get("active_id",False)

        price_calculation_line = self.env['building.price.calculation.line'].browse(line_id)

        record_price_details = {
            'price_calculation_id': price_calculation_line.price_calculation_id.id,
            'price_calculation_line_id': price_calculation_line.id,
            'price_number': price_calculation_line.price_number,
            'amount_products': self.amount_products,
            'amount_meterials': self.amount_meterials,
            'amount_expendables': self.amount_expendables,
            'amount_humans': self.amount_humans,
            'amount_total': self.amount_total,
            'perc_construction_costs': self.perc_construction_costs,
            'amount_production_cost': self.amount_production_cost,
            'perc_special_expenses': self.perc_special_expenses,
            'amount_direct_cost': self.amount_direct_cost,
            'perc_general_costs': self.perc_general_costs,
            'amount_standard_price': self.amount_standard_price,
            'margin_benefit': self.margin_benefit,
            'sale_price': self.sale_price,
        }
        price_detail = self.env['building.price.details'].create(record_price_details)

        for line in self.product_line_ids :
            record_product = {
                                    'name': line.name,
                                    'building_price_detail_id':price_detail.id,
                                    'quantity':line.quantity,
                                    'price_unit':line.price_unit,
                                    }
            if line.product_id :
                record_product['product_id'] = line.product_id.id
            if line.product_uom :
                record_product['product_uom'] = line.product_uom.id
            self.env['building.price.product.line'].create(record_product)
        for meterial in self.resource_material_ids :
            record_resource_material = {
                                    'name': meterial.name,
                                    'building_price_detail_id':price_detail.id,
                                    'quantity':meterial.quantity,
                                    'price_unit':meterial.price_unit,
                                    }
            if meterial.product_uom :
                record_resource_material['product_uom'] = meterial.product_uom.id
            if meterial.resource_categ_id:
                record_resource_material['resource_categ_id'] = meterial.resource_categ_id.id
            if meterial.resource_id:
                record_resource_material['resource_id'] = meterial.resource_id.id
            self.env['building.price.resource.material'].create(record_resource_material)
        for expendable in self.expendable_ids :
            record_expendable = {
                                    'name': expendable.name,
                                    'building_price_detail_id':price_detail.id,
                                    'quantity':expendable.quantity,
                                    'price_unit':expendable.price_unit,
                                    }
            if expendable.product_id :
                record_resource_material['product_id'] = expendable.product_id.id
            if expendable.product_uom :
                record_resource_material['product_uom'] = expendable.product_uom.id
            self.env['building.price.expendable'].create(record_expendable)
        for human in self.resource_human_ids :
            record_resource_human = {
                                    'name': human.name,
                                    'building_price_detail_id':price_detail.id,
                                    'quantity':human.quantity,
                                    'price_unit':human.price_unit,
                                    }
            if human.product_uom :
                record_resource_human['product_uom'] = human.product_uom.id
            if human.profile_id:
                record_resource_human['resource_categ_id'] = human.profile_id.id
            if human.resource_id:
                record_resource_human['resource_id'] = human.resource_id.id
            self.env['building.price.resource.human'].create(record_resource_human)
        price_calculation_line.write({'calculated_sales_price':self.sale_price,'actual_selling_price':self.sale_price})
        return {'type': 'ir.actions.act_close_wizard_and_reload_view'}



class building_product_line(models.TransientModel):
    
    _name = "building.product.line"
    _description = "Composants"

    name = fields.Char('Nom', size=1024, readonly=False)
    product_id = fields.Many2one('product.product', 'Produit',domain=[('type','=','product')],required=False)
    product_uom = fields.Many2one('product.uom', 'Unité de mésure ', required=False, readonly=False)
    building_product_id = fields.Many2one('building.product', 'Wizard')
    margin_benefit = fields.Float('Marge', digits=(16,3))
    quantity = fields.Float(string='Quantité', digits= dp.get_precision('Product Unit of Measure'),required=True,default=0)
    price_unit = fields.Float('Prix Unitaire')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            max_price = self.product_id.standard_price
            self._cr.execute("select max(invl.price_unit) from account_invoice inv,account_invoice_line invl where invl.product_id=%s and inv.invoice_type='%s' and inv.id=invl.invoice_id"%(self.product_id.id,'in_invoice'))
            result = self._cr.fetchone()
            if result[0] != None :
                max_price = result[0]
            self.name = self.product_id.name
            self.product_uom = self.product_id.uom_id.id
            self.price_unit = max_price

class building_resource_material(models.TransientModel):

    _name = "building.resource.material"
    _description = "Ressources Matériels"

    name = fields.Char('Désignation', readonly=False)
    resource_categ_id = fields.Many2one('resource.category', 'Catégorie Matériel',required=False)
    resource_id = fields.Many2one('building.resource', 'Matériel', domain=[('type', '=', 'material')],required=False)
    product_uom = fields.Many2one('product.uom', 'Unité de mésure ', required=False, readonly=False)
    building_product_id = fields.Many2one('building.product', 'Wizard')
    quantity = fields.Float(string='Quantité', digits=dp.get_precision('Product Unit of Measure'),required=True, default=0)
    price_unit = fields.Float('Prix Unitaire')

    @api.onchange('resource_categ_id')
    def onchange_resource_categ_id(self):
        if self.resource_categ_id:
            self.name = self.resource_categ_id.name
            self.product_uom = self.resource_categ_id.default_unit.id
            if self.resource_categ_id.resource_ids :
                return {'domain': {'resource_id': [('id', 'in', list([self.resource_categ_id.resource_ids._ids]))]}}
            else :
                return {'domain': {'resource_id': [('id', 'in', list([]))]}}

    @api.onchange('resource_id')
    def onchange_resource_id(self):
        if self.resource_id:
            self.name = self.resource_id.name
            self.product_uom = self.resource_id.cost_unit.id
            self.price_unit = self.resource_id.schedule_cost

class building_expendable(models.TransientModel):

    _name = "building.expendable"
    _description = "Composants"

    name = fields.Char('Nom', size=1024, readonly=False)
    product_id = fields.Many2one('product.product', 'Produit', domain=[('type', '=', 'consu')],required=False)
    product_uom = fields.Many2one('product.uom', 'Unité de mésure ', required=False, readonly=False)
    building_product_id = fields.Many2one('building.product', 'Wizard')
    margin_benefit = fields.Float('Marge', digits=(16, 3))
    quantity = fields.Float(string='Quantité', digits=dp.get_precision('Product Unit of Measure'),required=True, default=0)
    price_unit = fields.Float('Prix Unitaire')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            max_price = self.product_id.standard_price
            self._cr.execute("select max(invl.price_unit) from account_invoice inv,account_invoice_line invl where invl.product_id=%s and inv.invoice_type='%s' and inv.id=invl.invoice_id" % (self.product_id.id, 'in_invoice'))
            result = self._cr.fetchone()
            if result[0] != None:
                max_price = result[0]
            self.name = self.product_id.name
            self.product_uom = self.product_id.uom_id.id
            self.price_unit = max_price

class building_resource_human(models.TransientModel):

    _name = "building.resource.human"
    _description = "Ressources Humaines"

    name = fields.Char('Désignation', readonly=False)
    profile_id = fields.Many2one('resource.profile', 'Profil', required=False)
    resource_id = fields.Many2one('building.resource', 'Main d\'oeuvre', domain=[('type', '=', 'human')],required=False)
    product_uom = fields.Many2one('product.uom', 'Unité de mésure ', required=False, readonly=False)
    building_product_id = fields.Many2one('building.product', 'Wizard')
    quantity = fields.Float(string='Quantité', digits=dp.get_precision('Product Unit of Measure'),required=True, default=0)
    price_unit = fields.Float('Prix Unitaire')

    @api.onchange('profile_id')
    def onchange_profile_id(self):
        if self.profile_id:
            self.name = self.profile_id.name
            self.product_uom = self.profile_id.default_unit.id
            if self.profile_id.resource_ids:
                return {'domain': {'resource_id': [('id', 'in', list([self.profile_id.resource_ids._ids]))]}}
            else:
                return {'domain': {'resource_id': [('id', 'in', list([]))]}}

    @api.onchange('resource_id')
    def onchange_resource_id(self):
        if self.resource_id:
            self.name = self.resource_id.name
            self.product_uom = self.resource_id.cost_unit.id
            self.price_unit = self.resource_id.schedule_cost

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: