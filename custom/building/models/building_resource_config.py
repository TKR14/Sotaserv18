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

class resource_profile(models.Model):

    _name = "resource.profile"
    _description = "Resource Profile"

    name = fields.Char("Nom du profil", required=True)
    cost = fields.Float(string='Coût unitaire')
    default_unit = fields.Many2one("uom.uom", string='Unité par défaut')
    description = fields.Text("Description")
    parent_id = fields.Many2one("resource.profile", string='Parent')
    resource_ids = fields.One2many('building.resource','profile_id', string='Ressources Humaines', readonly=True, copy=False)

class resource_category(models.Model):

    _name = "resource.category"
    _description = "Resource Category"

    name = fields.Char("Nom famille", required=True)
    cost = fields.Float(string='Coût unitaire')
    default_unit = fields.Many2one("uom.uom", string='Unité par défaut')
    description = fields.Text("Description")
    parent_id = fields.Many2one("resource.category", string='Parent')
    resource_ids = fields.One2many('building.resource', 'category_id', string='Ressources Matérielles', readonly=True, copy=False)

class resource_load(models.Model):

    _name = "resource.load"
    _description = "Charges"

    name = fields.Char("Description", required=True)
    cost = fields.Float(string='Coût')
    default_unit = fields.Many2one("uom.uom", string='Unité par défaut')
