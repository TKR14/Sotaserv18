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

class building_caution_create(models.TransientModel):
    
    _name = "building.caution.create"
    _description = "Import document"

    file = fields.Binary("Fichier à importer",filters='*.*')
    name = fields.Char('Nom du document', size=256, readonly=False)
    amount_caution = fields.Float(string='Montant de Caution')
    tax_id = fields.Many2one('account.tax', 'Taxe',domain=[('type_tax_use','=','sale')])
    start_date = fields.Date(string='Date de création',required=False,readonly=False,index=True, copy=False,default=lambda *a: time.strftime('%Y-%m-%d'))

    @api.multi
    def create_document(self):
        attach_obj = self.env['ir.attachment']
        caution_obj = self.env['building.caution']
        order_obj = self.env['building.order']
        bail_application_obj = self.env['administrative.bail.application']
        order_id = self._context.get('active_id',False)
        order = order_obj.browse(order_id)
        if order.state == 'draft' :
            attachment_record = {
                                   'name': self.name,
                                   'datas': self.file,
                                   'datas_fname': self.name,
                                   'res_model': self._context.get('active_model'),
                                   'res_id': order_id  ,
                                   'partner_id':order.partner_id.id,
                                }
            attach_obj.create(attachment_record)
            caution_record = {
                                   'type':'tender_caution',
                                   'partner_id':order.partner_id.id,
                                   'ref_tendering': order.ref_tendering,
                                   'amount_caution':self.amount_caution,
                                   'state':'draft',
                                   'origin_id':order.id,
                                   'date_start':self.start_date,
                                   #'tax_id':self.tax_id.id,
                                }
            bail_application = bail_application_obj.search([('price_id', '=', order.origin_id.id)])
            if bail_application :
                caution_record['bail_application_id'] = bail_application.id
            caution_obj.create(caution_record)
            order.action_sent()
        else :
            attachment_record = {
                                   'name': self.name,
                                   'datas': self.file,
                                   'datas_fname': self.name,
                                   'res_model': self._context.get('active_model'),
                                   'res_id': order_id  ,
                                   'partner_id':order.partner_id.id,
                                }
            attach_obj.create(attachment_record)
            caution_record = {
                                   'type':'definitif_caution',
                                   'partner_id':order.partner_id.id,
                                   'ref_tendering': order.ref_tendering,
                                   'amount_caution':self.amount_caution,
                                   'state':'draft',
                                   'origin_id':order.id,
                                   'date_start':self.start_date,
                                   #'tax_id':self.tax_id.id,
                                }
            bail_application = bail_application_obj.search([('price_id', '=', order.origin_id.id)])
            if bail_application :
                caution_record['bail_application_id'] = bail_application.id
            caution_obj.create(caution_record)
            order.action_gained()
        return {}
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
