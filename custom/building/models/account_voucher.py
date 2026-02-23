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

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools import float_compare
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
import datetime
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

class account_voucher(models.Model):
    _inherit = "account.voucher"
    _description = "voucher"

    site_id = fields.Many2one('building.site','Affaire')
    order_id = fields.Many2one('building.order','DQE')
    voucher_type = fields.Selection([("stock", "Stock"),("timesheet", "Temps de travail"),("subcontracting", "Sous-traitance"),("workforce", "Main-d’œuvre"),("rental_materials","Location matériaux"),("load", "Charge"),("production", "Réalisation par Entreprise"),("purchase", "Achats"),("none", "Not Applicable")], string="Type de lige",default='none')

    @api.multi
    def button_proforma_voucher(self):
        res = super(account_voucher,self).button_proforma_voucher()
        if self.site_id:
            invoice_id = self._context.get('invoice_id',False)
            inv = self.env['account.invoice'].browse(invoice_id)
            record_voucher ={
                'site_id':inv.site_id.id,
                'order_id':inv.order_id.id
            }
            if inv.type == 'out_invoice' and inv.invoice_type == 'specific' and  inv.invoice_attachment :
                record_voucher['voucher_type'] = 'production'
            if inv.type == 'in_invoice' and inv.invoice_type == 'specific' and inv.invoice_attachment :
                record_voucher['voucher_type'] = 'subcontracting'
            if inv.type == 'in_invoice' and inv.invoice_type == 'specific' and inv.invoice_workforce :
                record_voucher['voucher_type'] = 'workforce'
            if inv.type == 'in_invoice' and inv.invoice_type == 'specific' and inv.invoice_material :
                record_voucher['voucher_type'] = 'rental_materials'
            if inv.type == 'in_invoice' and inv.invoice_type == 'specific' and inv.invoice_load :
                record_voucher['voucher_type'] = 'load'
            if inv.type == 'in_invoice' and inv.invoice_type == 'specific' and not inv.invoice_load and not inv.invoice_material and not inv.invoice_workforce and not inv.invoice_attachment:
                record_voucher['voucher_type'] = 'purchase'
            self.write(record_voucher)
            #move_pool = self.pool.get('account.move')
            self.move_id.write({'site_id':self.site_id.id,'order_id':self.order_id.id,'type':self.voucher_type})
        return res

    # def action_move_line_create(self, cr, uid, ids, context=None):
    #     '''
    #     Confirm the vouchers given in ids and create the journal entries for each of them
    #     '''
    #     res = super(account_voucher,self).action_move_line_create(cr, uid, ids, context=context)
    #     move_pool = self.pool.get('account.move')
    #     for voucher in self.browse(cr, uid, ids, context=context):
    #         #update move with site ,dqe and type de transaction
    #         print "'site_id':voucher.site_id.id,'order_id':voucher.order_id.id,'type':voucher.voucher_type",voucher.site_id.id,voucher.order_id.id,voucher.voucher_type
    #         raise except_orm(_('Attention!'), _('OSD pas encore disponible! : Merci de fournir ODS.'))
    #         move_pool.write(cr,uid,[voucher.move_id.id],{'site_id':voucher.site_id.id,'order_id':voucher.order_id.id,'type':voucher.voucher_type})
    #     return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
