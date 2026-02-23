
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
    "name": "Building",
    "version": "18.0.0.1",
    "depends": ['base', 'product', 'web', 'sale', 'hr', 'hr_timesheet', 'stock', 'purchase', 
    'account', 'purchase_request', 'maintenance', 'fleet', 'fleet_maintenance', 
    'crm', 'crm_igaser', 'hr_attendance', 'hr_igaser', 'om_hr_payroll',
    'om_hr_payroll_account', 'hr_payroll_ma'],
    "author": "Aziz ELHAMDANY",
    "category": "Building",
    "description": """
    
		Gestion commercial et projet
        
    """,
    "init_xml": [],
    'data': [
            #  'static/src/xml/building.xml',
             'security/building_groups.xml',
             'security/ir.model.access.csv',
             'data/data_document_type.xml',
             'data/data_stock_location.xml',
             'sequences/building_sequence.xml',
             'views/product_view.xml',
             'views/building_resource_view.xml',
             'views/configuration_view.xml',
             'views/ir_attachment_view.xml',
		     'views/building_price_calculation_view.xml',
             'views/building_order_view.xml',
             'views/building_caution_view.xml',
             'views/building_attachment_view.xml',
             'views/building_subcontracting_view.xml',
             'wizard/building_document_view.xml',
             'wizard/building_advance_view.xml',
             'wizard/building_assigned_ressource_view.xml',
             'wizard/building_attachment_create_view.xml',
             'wizard/building_request_view.xml',
             'wizard/building_prepare_internal_move_view.xml',
             'wizard/building_subcontracting_create_view.xml',
             'wizard/building_amendment_create_view.xml',
             'views/purchase_view.xml',
             'views/building_site_view.xml',
             'views/invoice_view.xml',
             'views/stock_view.xml',
             'views/hr_view.xml',
             'views/user_view.xml',
             'views/building_site_report_view.xml',
             'views/maintenance_view.xml',
             'menus/site.xml',
             'views/building_profile_assignment.xml',
             'menus/stock.xml',
             'views/product_buyer.xml',
             'views/building_purchase_need.xml',
             'views/building_assignment_line_vec_tree_readonly.xml',
             'views/maintenance_request_resource_material_tree_view.xml',
             'views/building_attachment_client_report.xml',
             'views/building_decompte_client_report.xml',
             'menus/resources.xml',
             'menus/sale.xml',
            #  # 'menus/invoice.xml',
            #  # 'menus/purchase.xml'
            #  # 'views/report_invoice.xml',
            #  # 'views/report_order.xml',
             'views/report_dlmassign.xml',
             'views/report_requestvehicle.xml',
             'views/report_missionorder.xml',
             'views/report_trasportschedule.xml',
             'views/report_materials_worked_hours.xml',
             'views/report_diagnosticsheet.xml',
             'views/report_intervention.xml',
             'views/report_attachment.xml',
             'report/building_report.xml',
             'wizard/dlm_common_report.xml',
             'wizard/create_line_view.xml',
             'wizard/create_section_view.xml',
             'wizard/update_section_sequence_number.xml',
             'wizard/building_set_draft_motif_wizard.xml',
             'wizard/stock_deduction_modal_view.xml',
             'wizard/view_advance_deduction_warning_wizard.xml',
            # #  'wizard/stock_transfer_details_view.xml',
            # #  'wizard/building_validate_quotation_view.xml',

    ],
    'qweb': [
        "static/src/xml/base.xml",
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'assets': {
        'web.assets_backend': [
            '/building/static/src/js/*.js',
        ],
    },
}
