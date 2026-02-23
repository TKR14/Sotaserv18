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

class validate_payday_advance(models.TransientModel):
    
    _name = "validate.payday.advance"
    _description = "Validation Avance"
        
    def acion_validate(self):
        payday_advance_obj = self.env['hr.payroll_ma.payday_advance']
        payday_advance_ids = self._context.get('active_ids', [])
        payday_advances = payday_advance_obj.browse(payday_advance_ids)

        for payday_advance in payday_advances:
            payday_advance.action_validate()
        return True

class payed_payday_advance(models.TransientModel):
    
    _name = "payed.payday.advance"
    _description = "Payer Avance"
        
    def acion_payed(self):
        payday_advance_obj = self.env['hr.payroll_ma.payday_advance']
        payday_advance_ids = self._context.get('active_ids', [])
        payday_advances = payday_advance_obj.browse(payday_advance_ids)

        for payday_advance in payday_advances:
            payday_advance.action_payed()
        return True