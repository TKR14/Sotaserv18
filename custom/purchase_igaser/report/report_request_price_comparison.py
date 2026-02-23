# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class ReportRequestPriceComparison(models.AbstractModel):
    _name = 'report.report_request_price_comparison'
    _description = 'Comparison offer'

    # def get_lines(self, po_ids):

    #     lines = {}
    #     orders = self.env['purchase.order'].browse(po_ids)
    #     partners = {}
    #     for order in orders:
    #         if order.partner_id.id not in partners:
    #             partners[order.partner_id.id] = order.partner_id.name
    #         for line in order.order_line:
    #             if line.product_id.id not in lines:
    #                 lines[line.product_id.id] = {}
    #                 lines[line.product_id.id]['name'] = line.product_id.name
    #             if order.partner_id.id not in lines[line.product_id.id]:
    #                 lines[line.product_id.id][order.partner_id.id] = {}
    #             lines[line.product_id.id][order.partner_id.id] = line.price_unit 

    #     return lines