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
    "name": "CRM Management",
    'version': '18.0.0.0',
    'category': 'Base',
    'sequence': 14,
    'author':  'ELHAMDANY',
    'website': '',
    'license': 'AGPL-3',
    'summary': '',
    "description": """
    	Suivi des consultations
    """,
    'depends': [
        "base", "crm", "sale_crm"
    ],
    'external_dependencies': {
    },
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/crm_lead.xml',
        'views/crm_case_raedonly_tree_view_oppor.xml',
        'wizard/crm_lead_return_wizard.xml',

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
