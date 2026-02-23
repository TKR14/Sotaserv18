# -*- coding: utf-8 -*-
# from odoo import http


# class CnssBdsIgaser(http.Controller):
#     @http.route('/cnss_bds_igaser/cnss_bds_igaser/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cnss_bds_igaser/cnss_bds_igaser/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('cnss_bds_igaser.listing', {
#             'root': '/cnss_bds_igaser/cnss_bds_igaser',
#             'objects': http.request.env['cnss_bds_igaser.cnss_bds_igaser'].search([]),
#         })

#     @http.route('/cnss_bds_igaser/cnss_bds_igaser/objects/<model("cnss_bds_igaser.cnss_bds_igaser"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cnss_bds_igaser.object', {
#             'object': obj
#         })
