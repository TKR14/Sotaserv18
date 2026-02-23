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
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp

class stock_invoice_onshipping(models.TransientModel):

    _inherit = "stock.invoice.onshipping"

    @api.multi
    def open_invoice(self):
        if self._context is None:
            self._context = {}
        picking_obj=self.env['stock.picking']
        invoice_obj=self.env['account.invoice']

        picking_id = picking_obj.browse(self._context.get('active_ids')[0])
        invoice_ids = self.create_invoice()
        invoice_value={}
        if picking_id.site_id.id :
            invoice_value['site_id']=picking_id.site_id.id
            invoice_value['order_id']=picking_id.order_id.id
            invoice_value['invoice_type']='specific'

        if picking_id.origin_id :
            invoice_value['categ_invoice'] = picking_id.origin_id.purchase_type
            # if picking_id.origin_id.purchase_workforce :
            #     invoice_value['invoice_workforce']= True
            # elif picking_id.origin_id.purchase_material :
            #     invoice_value['invoice_material']= True
            # elif picking_id.origin_id.purchase_equipment :
            #     invoice_value['invoice_equipment']= True
            # elif picking_id.origin_id.purchase_service :
            #     invoice_value['invoice_service']= True
            # else :
            #    invoice_value['invoice_load']= True

        if not invoice_ids:
            raise except_orm(_('Error!'), _("No invoice created!"))

        invoice = invoice_obj.browse(invoice_ids[0])
        invoice.write(invoice_value)

        action_model = False
        action = {}

        journal2type = {'sale':'out_invoice', 'purchase':'in_invoice' , 'sale_refund':'out_refund', 'purchase_refund':'in_refund'}
        inv_type = journal2type.get(self.journal_type) or 'out_invoice'
        data_pool = self.env['ir.model.data']
        if inv_type == "out_invoice":
            action_id = data_pool.xmlid_to_res_id('account.action_invoice_tree1')
        elif inv_type == "in_invoice" and invoice.invoice_type == 'standard':
            action_id = data_pool.xmlid_to_res_id('account.action_invoice_tree2')
        elif inv_type == "in_invoice" and invoice.invoice_type == 'specific':
            action_id = data_pool.xmlid_to_res_id('building.action_building_invoice_supplier_other_tree')
        elif inv_type == "out_refund":
            action_id = data_pool.xmlid_to_res_id('account.action_invoice_tree3')
        elif inv_type == "in_refund":
            action_id = data_pool.xmlid_to_res_id('account.action_invoice_tree4')
        if action_id:
            action_pool = self.pool['ir.actions.act_window']
            action = action_pool.read(self._cr,self._uid,action_id)
            action['domain'] = "[('id','in', ["+','.join(map(str,invoice_ids))+"])]"
            return action
        return True
