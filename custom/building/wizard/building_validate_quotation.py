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
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################
from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import datetime
import time

class building_validate_quotation(models.TransientModel):
    
    _name = 'building.validate.quotation'


    @api.multi
    def validate_quotation(self):

        purchase_obj = self.env['purchase.order']
        purchase_line_ids = self._context.get('active_ids')
        self._cr.execute('SELECT DISTINCT order_id FROM purchase_order_line WHERE  id in %s',(tuple(purchase_line_ids),))
        order_ids = [item[0] for item in self._cr.fetchall() if item[0] != None]
        self._cr.execute('SELECT pl.id FROM purchase_order_line pl,purchase_order po WHERE po.id=pl.order_id and po.id in %s',(tuple(order_ids),))
        all_purchase_line = [item[0] for item in self._cr.fetchall() if item[0] != None]
        purchase_line_to_cancel = list(set(all_purchase_line)-set(purchase_line_ids))
        self._cr.execute('update purchase_order_line set state =%s where id in %s',('cancel', tuple(purchase_line_to_cancel),))
        for purchase in purchase_obj.browse(order_ids) :
            print purchase.signal_workflow('purchase_confirm')
        return True

