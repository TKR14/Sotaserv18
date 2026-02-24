{
    "name": "Account Plus",
    "version": "18.0.0.0",
    "summary": "Enhanced Features for Accounting",
    "description": """
        This module provides enhanced accounting features to improve 
        financial management and reporting.
        """,
    "category": "Accounting",
    "depends": ["base", "account", "partner_igaser"],
    "data": [
        'security/account_groups.xml',
        'security/ir.model.access.csv',
        'views/account_move_view.xml',
        'views/account_move_received_view.xml',
        'views/purchase_view.xml',
        'views/account_journal.xml',
        'views/account_payment_register.xml',
        'views/account_payment.xml',
        'views/account_move_bo_view_form.xml',
        'views/stock_picking_readonly_tree_view.xml',
        'views/virement.xml',
        'views/account_bank_statement_view.xml',
        'views/account_customer_invoice_report.xml',
        'views/account_payment_search_view.xml',
        'views/account_move_type_view.xml',
        'views/account_move_invoice_client_report.xml',
        # 'views/assets.xml',
        'views/account_daf_views.xml',
        'wizard/reset_draft_reason_wizard.xml',
        'wizard/account_rg_release.xml',
        'wizard/hr_payslip_run_payment.xml',
        'wizard/tax_line_wizard.xml',
        # 'static/src/xml/account_plus.xml',
    ]
}