# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
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
{
    "name": "Purchase Multiple Price Management",
    'version': '18.0.0.0',
    'category': 'Purchases',
    'sequence': 14,
    'author':  'ANWAR Othmane & ABID Makram',
    'website': '',
    'license': 'AGPL-3',
    'summary': '',
    "description": """
    	- Ajouter multiple demande de prix
        - Ajouter tableau comparatif des offres
    """,
    'depends': [
        "base", "purchase", "purchase_stock", "account", "purchase_request", "hr_assignment" ,"building"
    ],
    'external_dependencies': {
    },
    'data': [
        # 'static/assets_backend.xml',
        'security/purchase_requ_groups.xml',
        'security/ir.model.access.csv',
        'wizard/request_price_view.xml',
        'wizard/request_price_comparison_view.xml',
        'wizard/purchase_request_line_make_purchase_order_view.xml',
        'report/report_request_price_comparison.xml',
        'report/purchase_order_templates.xml',
        'report/report_invoice.xml',
        'report/report_requestorder.xml',
        'views/purchase_view.xml',
        'views/purchase_order.xml',
        'views/stock_picking.xml',
        'views/menus.xml',
        'views/approval_chain.xml',
    ],
    'qweb': [
    ],

    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
