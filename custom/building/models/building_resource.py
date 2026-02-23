# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP SA (http://www.openerp.com)
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
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError

STATES=[('available','Disponible'),('site','En Affaire'),('maintenance','En réparation'),('broken','En panne')]


class building_resource(models.Model):
    
    _name = "building.resource"
    _description = "Resource"
    _order = "id desc"


    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        model_obj = self.env['ir.model.data']
        if ('type_resource' in self._context) and (self._context['type_resource'] == 'material'):
            model_data_ids_form = model_obj.search(c[('model','=','ir.ui.view'), ('name', 'in', ['building_resource_material_form', 'building_resource_material_tree','building_resource_search_material_form'])])
            resource_id_form = model_obj.read(model_data_ids_form.ids, fields=['res_id', 'name'])
            dict_model = {}
            for i in resource_id_form:
                dict_model[i['name']] = i['res_id']
            if view_type == 'form':
                view_id = dict_model['building_resource_material_form']
            elif view_type == 'tree':
                view_id = dict_model['building_resource_material_tree']
            else :
               view_id = dict_model['building_resource_search_material_form']

        if ('type_resource' in self._context) and (self._context['type_resource']=='human'):
            model_data_ids_form = model_obj.search([('model','=','ir.ui.view'), ('name', 'in', ['building_resource_form', 'building_resource_human_tree','building_resource_search_human_form'])])
            resource_id_form = model_obj.read(model_data_ids_form.ids, fields=['res_id', 'name'])
            dict_model = {}
            for i in resource_id_form:
                dict_model[i['name']] = i['res_id']
            if view_type == 'form':
                view_id = dict_model['building_resource_form']
            elif view_type == 'tree':
                view_id = dict_model['building_resource_human_tree']
            else:
                view_id = dict_model['building_resource_search_human_form']

        return super(building_resource, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    
    
    # def name_search(self, name, args=None, operator='ilike', limit=100):
    #     resources = self.search(['|','|',('name', operator, name),('registration_number', operator, name),('serial_number', operator, name)] + args, limit=limit)
    #     print(resources)
    #     return resources.name_get()


    # def name_get(self):
    #     result = []
    #     for resource in self:
    #         if resource.type_resource == 'human' :
    #             result.append((resource.id, "%s %s" % ('['+resource.registration_number+']', resource.name)))
    #         if resource.type_resource == 'material' :
    #             result.append((resource.id, "%s %s" % ('['+resource.serial_number+']', resource.name)))
    #     return result


    def _default_type(self):
        resource_type = self._context.get('type_resource', False)
        return resource_type


    def _default_cost_unit(self):
        product_unit = []
        if self._context.get('type_resource', False) == 'human':
            name = 'Hour(s)'
        if self._context.get('type_resource', False) == 'material':
            name = 'Day(s)'
            product_unit= self.env['uom.uom'].search([('name','=', name)])
        if product_unit :
            return product_unit[0]
        return {}

    name = fields.Char("Nom", required=True)
    type_resource = fields.Selection([('human','Ressource humaine'), ('material','Ressource matérielle')], string='Type de la ressource', required=True, default=_default_type)
    schedule_cost = fields.Float(string='Coût unitaire')
    cost_unit = fields.Many2one("uom.uom", string='Unité', default=_default_cost_unit)
    employee_id =  fields.Many2one('hr.employee', string='Employé')
    registration_number = fields.Char("Matricule", required=False)
    serial_number = fields.Char("Numéro de série", required=False)
    profile_id = fields.Many2one('resource.profile', string='Profil')
    category_id = fields.Many2one('resource.category', string='Categorie')
    state = fields.Selection(STATES, string="Statut", default='available')
    is_employe = fields.Boolean('Est un Employé ?')

    _sql_constraints = [('matricule_emp_uniq', 'unique(registration_number)','Le Numéro de Matricule doit etre unique!'),
                        ('serial_number_uniq', 'unique(serial_number)','Le Numéro de série doit etre unique!'),
                        ]
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.registration_number = self.employee_id.registration_number,
            self.name = self.employee_id.name

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id :
            self.schedule_cost = self.category_id.cost
            self.cost_unit = self.category_id.default_unit.id

    @api.onchange('profile_id')
    def _onchange_profile_id(self):
        if self.profile_id :
            self.schedule_cost = self.profile_id.cost
            self.cost_unit = self.profile_id.default_unit.id
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name