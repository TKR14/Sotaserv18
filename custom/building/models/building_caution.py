
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

class building_caution(models.Model):

    _name = 'building.caution'
    
    site_id = fields.Many2one('building.site','Affaire', readonly=False)
    date_start = fields.Date('Date Début')
    date_end = fields.Date('Date Fin')
    partner_id = fields.Many2one('res.partner', 'Client', readonly=False, required=False, change_default=True, track_visibility='always', domain=[('customer_rank','&gt;', 0)])
    type_caution = fields.Selection([('tender_caution','Caution de soumission'),('definitif_caution','Caution définitive')], string='Type de caution', required=False,default='tender_caution')
    amount_caution = fields.Float(string='Montant de Caution')
    ref_tendering = fields.Char('Référence appel d\'offres',required=False)
    state = fields.Selection([('draft','Brouillon'),('caution_diposed','Caution diposée'),('released','Mainlevée déposé'),('retrieved_caution','Caution récupérée')], string='Status de caution', required=False,default='draft')
    origin_id = fields.Many2one('building.order', 'Réf Order')
    tax_id = fields.Many2one('account.tax', 'Taxe', domain=[('type_tax_use','=','sale')])
    invoice_id = fields.Many2one('account.move','Facture', domain=[('move_type','=','out_invoice')], readonly=False)
    # bail_application_id = fields.Many2one('administrative.bail.application', 'Demande de Caution', readonly=False)


    def action_diposed(self):
        self.write({'state':'caution_diposed'})
        return True

    def action_released(self):
        self.write({'state':'released'})
        return True

    def action_retrieved(self):
        self.write({'state':'retrieved_caution'})
        return True