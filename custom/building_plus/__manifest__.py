{
    "name": "Building +",
    "version": "1.0.0",
    "depends": ["base", "web", "account_plus", "building", "building_report", "purchase_request", "stock", "stock_plus","purchase_igaser", "auth_signup"],
    "author": "ABID Makram & ANWAR Othmane",
    "category": "Building",
    "description": """
    
		Gestion commercial et projet
        
    """,
    "init_xml": [],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "views/stock_picking.xml",
        "views/building_site_view.xml",
        # # "views/account_sock_view_form.xml",
        "views/blank.xml",
        # "views/assets.xml",
        "views/purchase_price_comparison_view.xml",
        "views/dashboard_view.xml",
        "views/account_remove_links_login.xml",
        "views/building_purchase_need.xml",
        "wizard/cancellation_reason.xml",
        "views/account_invoice_view.xml",
        "views/actions.xml",
        "views/menus.xml",
    ],
    'qweb': [
        'static/src/xml/generate_purchase_price_comparison_button.xml',
    ],
    'js': [
        'static/src/js/generate_purchase_price_comparison_button.js',
    ],
    "demo_xml": [],
    "installable": True,
    "active": False,
}