{
    'name': 'cnss_upload_txt',
    'version': '1.0',
    'author': 'ABID Makram',
    'summary': '',
    'sequence': 1,
    'description': """ """,
    'category': '',
    'website': '',
    'depends': ['hr_payroll_ma', 'om_hr_payroll'],
    'data': [
        # 'views/assets.xml',
        'security/ir.model.access.csv',
        'views/custom_main_upload_button.xml',
        'views/cnss_import_txt_wizard_view.xml',
    ],

    'qweb': [
        'static/src/xml/cnss_upload_txt_button.xml',
    ],
    'js': [
        'static/src/js/cnss_upload_txt_button.js',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
