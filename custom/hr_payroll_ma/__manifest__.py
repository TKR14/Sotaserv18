
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

{
    "name": "Payroll MA",
    'website': '',
    "version": "14.0.1",
    "depends": ['base','hr','om_hr_payroll','hr_contract', 'report_xlsx'],
    "author": "Aziz ELHAMDANY",
    "category": "HR",
    "description": """
    This module provide : 
		Adjustment of the Moroccan payroll
    """,
    "init_xml": [],
    'update_xml': [],
    'data': [
        'security/ir.model.access.csv',
        # 'data/payroll_data.xml',
        # 'static/src/xml/payroll.xml',
        'views/payroll_report.xml',
        'views/payroll_payslip.xml',
        'views/payroll_payslip_stc.xml',
        'views/payroll_view.xml',
        'views/payroll_jr_payslip.xml',
        'views/payroll_jr_cumul.xml',
        'views/payroll_jr_imputation.xml',
        'views/payroll_cnss.xml',
        'views/payroll_contract.xml',
        'views/hr_payslip_run_tree_view.xml',
        'views/report_payslip_batch_optimized.xml',
        'report/xlsx_report.xml',
        'wizard/payday_advance.xml',
        'wizard/personnel_permanent.xml',
        'wizard/personnel_permanent_xml.xml',
        ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'assets': {
        'web.assets_backend': [
            'hr_payroll_ma/static/src/css/payroll.css',
        ],
    },
}
