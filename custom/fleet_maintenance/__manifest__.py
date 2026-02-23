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
    "name": "Gestion de parc et maintenance",
    'version': '18.0.0.0',
    'category': 'Divers',
    'sequence': 14,
    'author':  'ELHAMDANY Aziz',
    'website': '',
    'license': 'AGPL-3',
    'summary': '',
    "description": """
    	- Gestion gasoil
        - Gestion des demandes affectation
        - Enrichissement des fiches existants
    """,
    'depends': [
        "base", "maintenance", "fleet", "stock"
    ],
    'external_dependencies': {
    },
    'data': [
        'security/ir.model.access.csv',
        'security/groups.xml',
        # 'static/import.xml',
        'views/fleet_new_view.xml',
        'views/fleet_view.xml',
        'views/fleet_vehicle_tree_view_inherit.xml',
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
    'assets': {
        'web.assets_backend': [
            'fleet_maintenance/static/src/css/fleet_maintenance.css',
        ],
    },
}
