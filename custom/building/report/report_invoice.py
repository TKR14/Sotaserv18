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

import time
from functools import partial
from openerp.osv import osv
from openerp.report import report_sxw
from openerp import models, fields, api, _
#from common_report_header import common_report_header


class invoice_report(report_sxw.rml_parse):

    @api.v7
    def __init__(self, cr, uid, name, context=None):
        super(invoice_report, self).__init__(cr, uid, name, context=context)
        
        self.localcontext.update({
            'time': time,
        })
        


class report_invoice(osv.AbstractModel):
    _name = 'report.building.report_invoice'
    _inherit = 'report.abstract_report'
    _template = 'building.report_invoice'
    _wrapped_report_class = invoice_report

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
