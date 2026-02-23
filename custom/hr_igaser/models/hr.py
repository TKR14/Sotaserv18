
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


class hr_employee(models.Model):

    _inherit = "hr.employee"

    registration_number =  fields.Char(string='Matricule', required=True, default = None)
    address =  fields.Char(string='Adresse')
    bank =  fields.Char(string='Banque')
    rib =  fields.Char(string='RIB')
    contract_type = fields.Selection([
            ('cdd', 'CDD'),
            ('cdc', 'CDC'),
            ('cdi', 'CDI'),
            ], 'Type de Contrat', readonly=False, index=True, change_default=True, default='cdc')
    recruitment_date = fields.Date('Date d''Entrée', readonly=False, copy=False)

    _sql_constraints = [('registration_number_uniq', 'unique(registration_number)','Le Numéro de Matricule doit etre unique!'),]


class hr_attendance(models.Model):

    _inherit = "hr.attendance"

    site = fields.Char("Chantier")
