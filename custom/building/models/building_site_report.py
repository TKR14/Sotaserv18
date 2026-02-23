
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
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
import datetime
import time
from dateutil.relativedelta import relativedelta


class building_site_report(models.Model):
    
    _name = 'building.site.report'
    _description = "Site Report"
    _order = "id desc"
    
    site_id = fields.Many2one("building.site", string="Affaire")
    r0 = fields.Selection([('executed', 'CA Réalisé'), ('invoiced', 'CA Facturé'), ('cashed', 'CA Encaissé'), ('inventory', 'Stock'), ('consu', 'Consommables'), ('product', 'Fournitures'), ('diesel', 'Gasoil'), ('prov_serv', 'Pres. Ser'), ('subcontracting', 'Sous-Traitance'), ('dlm', 'Location Interne'), ('dlm_rental', 'Location Externe'), ('rh', 'MO')], string="Rubrique", default='')
    amount = fields.Float(string='Montant')
    prc_amount_per_invoiced = fields.Float(string='Pourcentage/CA')
    prc_seuil = fields.Float(string='Pourcentage Seuil')

    def _get_product_last_price(self, site, product_id):
        move = self.env['stock.move'].search([('site_id', '=', site_id), ('product_id', '=', product_id), ('location_des_id', '=', site.location_id), ('state', '=', 'done')], order='id desc', limit=1)
        if move:
            return move.price_unit
        product = self.env['product.product'].search('id', '=', product_id)
        return product.product_tmpl_id.standard_price

    def building_site_report_details_tree_view(self):
        dict_type_by_product = self.site_id.get_type_by_product()
        executeds = self.env['building.executed'].search([('site_id', '=', self.site_id.id), ('state', '=', 'open')])
        for executed in executeds:
            executed.actualize_executed_amounts_daily()
        if self.r0 == 'executed':
            executed_line_report = self.env['building.executed.line.report'].search([('site_id', '=', self.site_id.id), ('r0', '=', 'executed'), ('r1', '=', 'executed'), ('executed_id', 'in', executeds.ids)])
            domain = [('id', 'in', executed_line_report.ids)]
            return {
                'name': _('Détails'),
                'domain': domain,
                'res_model': 'building.executed.line.report',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'view_mode': 'tree',
            }
        elif self.r0 == 'dlm':
            executed_line_report = self.env['building.executed.line.report'].search([('site_id', '=', self.site_id.id), ('r0', '=', 'load'), ('r1', 'in', ['site_install', 'mini_equipment', 'equipment']), ('is_rental', '=', False), ('executed_id', 'in', executeds.ids)])
            domain = [('id', 'in', executed_line_report.ids)]
            return {
                'name': _('Détails'),
                'domain': domain,
                'res_model': 'building.executed.line.report',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'view_mode': 'tree',
            }
        elif self.r0 == 'dlm_rental':
            executed_line_report = self.env['building.executed.line.report'].search([('site_id', '=', self.site_id.id), ('r0', '=', 'load'), ('r1', 'in', ['equipment']), ('is_rental', '=', True), ('executed_id', 'in', executeds.ids)])
            domain = [('id', 'in', executed_line_report.ids)]
            return {
                'name': _('Détails'),
                'domain': domain,
                'res_model': 'building.executed.line.report',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'view_mode': 'tree',
            }

        if self.r0 == 'rh':
            executed_line_report = self.env['building.executed.line.report'].search([('site_id', '=', self.site_id.id), ('r0', '=', 'load'), ('r1', 'in', ['supervisor_ressource', 'executor_ressource']), ('executed_id', 'in', executeds.ids)])
            domain = [('id', 'in', executed_line_report.ids)]
            return {
                'name': _('Détails'),
                'domain': domain,
                'res_model': 'building.executed.line.report',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'view_mode': 'tree',
            }
        
        if self.r0 == 'invoiced':
            self.env['building.site.invoiced.report'].search([('site_id', '=', self.site_id.id), ('invoice_state', '=', 'invoiced')]).unlink()
            invoices = self.env['account.move'].search([('site_id', '=', self.site_id.id), ('state', '=', 'posted'), ('move_type', '=', 'out_invoice'), ('invoice_attachment', '=', True), ('payment_state', '!=', 'paid')])
            list_invoice_report = []
            for invoice in invoices:
                for line in invoice.invoice_line_ids:
                    dict_invoice_report = {
                            'date' : invoice.invoice_date,
                            'year' : invoice.invoice_date.year,
                            'month': invoice.invoice_date.month,
                            'attach_id' : invoice.attachment_id.id, 
                            'invoice_id' : invoice.id,
                            'partner_id' : invoice.partner_id.id,
                            'site_id' : invoice.site_id.id,
                            'type_marche' : invoice.site_id.type_marche,
                            'invoice_state' : 'invoiced',
                            'user_id' : invoice.invoice_user_id.id,
                            'no_price' : invoice.attachment_line_id.chapter,
                            'description' : line.name,
                            'sale_qty' : line.attachment_line_id.line_dqe_id.quantity,
                            'qty' : line.quantity,
                            'price_unit' : line.price_unit,
                            'amount': line.price_subtotal
                        }
                    site_invoiced_report = self.env['building.site.invoiced.report'].create(dict_invoice_report)
                    list_invoice_report.append(site_invoiced_report.id)
            domain = [('id', 'in', list_invoice_report)]
            return {
                'name': _('Détails'),
                'domain': domain,
                'res_model': 'building.site.invoiced.report',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'view_mode': 'tree',
            }

        if self.r0 == 'cashed':
            self.env['building.site.invoiced.report'].search([('site_id', '=', self.site_id.id), ('invoice_state', '=', 'cashed')]).unlink()
            invoices = self.env['account.move'].search([('site_id', '=', self.site_id.id), ('state', '=', 'payed'), ('move_type', '=', 'out_invoice'), ('invoice_attachment', '=', True), ('payment_state', '=', 'paid')])
            list_invoice_report = []
            for invoice in invoices:
                for line in invoice.invoice_line_ids:
                    dict_invoice_report = {
                            'date' : invoice.invoice_date,
                            'year' : invoice.invoice_date.year,
                            'month': invoice.invoice_date.month,
                            'attach_id' : invoice.attachment_id.id, 
                            'invoice_id' : invoice.id,
                            'partner_id' : invoice.partner_id.id,
                            'site_id' : invoice.site_id.id,
                            'type_marche' : invoice.site_id.type_marche,
                            'invoice_state' : 'cashed',
                            'user_id' : invoice.invoice_user_id.id,
                            'no_price' : invoice.attachment_line_id.chapter,
                            'description' : line.name,
                            'sale_qty' : line.attachment_line_id.line_dqe_id.quantity,
                            'qty' : line.quantity,
                            'uom_id' : line.product_uom_id.id,
                            'price_unit' : line.price_unit,
                            'amount': line.price_subtotal
                        }
                    site_invoiced_report = self.env['building.site.invoiced.report'].create(dict_invoice_report)
                    list_invoice_report.append(site_invoiced_report.id)
            domain = [('id', 'in', list_invoice_report)]
            return {
                'name': _('Détails'),
                'domain': domain,
                'res_model': 'building.site.invoiced.report',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'view_mode': 'tree',
            }

        if self.r0 == 'subcontracting':
            self.env['building.site.invoiced.report'].search([('site_id', '=', self.site_id.id), ('invoice_state', 'in', ['subconstracting'])]).unlink()
            list_invoice_report = []
            invoices = self.env['account.move'].search([('site_id', '=', self.site_id.id), ('state', '=', 'posted'), ('move_type', '=', 'in_invoice'), ('invoice_attachment', '=', True)])
            for invoice in invoices:
                for line in invoice.invoice_line_ids:
                    dict_invoice_report = {
                            'date' : invoice.invoice_date,
                            'year' : invoice.invoice_date.year,
                            'month': invoice.invoice_date.month,
                            'attach_id' : invoice.attachment_id.id, 
                            'invoice_id' : invoice.id,
                            'partner_id' : invoice.partner_id.id,
                            'site_id' : invoice.site_id.id,
                            'type_marche' : '',
                            'invoice_state' : 'subcontracting',
                            'user_id' : invoice.invoice_user_id.id,
                            'no_price' : invoice.attachment_line_id.chapter,
                            'description' : line.name,
                            'sale_qty' : line.attachment_line_id.line_dqe_id.quantity,
                            'qty' : line.quantity,
                            'uom_id' : line.product_uom_id.id,
                            'price_unit' : line.price_unit,
                            'amount': line.price_subtotal
                        }
                    site_invoiced_report = self.env['building.site.invoiced.report'].create(dict_invoice_report)
                    list_invoice_report.append(site_invoiced_report.id)
            domain = [('id', 'in', list_invoice_report)]
            return {
                'name': _('Détails'),
                'domain': domain,
                'res_model': 'building.site.invoiced.report',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'view_mode': 'tree',
            }
        if self.r0 == 'prov_serv':
            self.env['building.site.invoiced.report'].search([('site_id', '=', self.site_id.id), ('invoice_state', 'in', ['other'])]).unlink()
            list_invoice_report = []
            invoices = self.env['account.move'].search([('site_id', '=', self.site_id.id), ('state', '=', 'posted'), ('move_type', '=', 'in_invoice'), ('invoice_attachment', '=', False), ('invoice_service', '=', True)])
            for invoice in invoices:
                for line in invoice.invoice_line_ids:
                    dict_invoice_report = {
                            'date' : invoice.invoice_date,
                            'year' : invoice.invoice_date.year,
                            'month': invoice.invoice_date.month,
                            'attach_id' : False, 
                            'invoice_id' : invoice.id,
                            'partner_id' : invoice.partner_id.id,
                            'site_id' : invoice.site_id.id,
                            'type_marche' : '',
                            'invoice_state' : 'other',
                            'user_id' : invoice.invoice_user_id.id,
                            'no_price' : '',
                            'description' : line.name,
                            'sale_qty' : 0,
                            'qty' : 1,
                            'uom_id' : '',
                            'price_unit' : line.price_unit,
                            'amount': line.price_subtotal
                        }
                    site_invoiced_report = self.env['building.site.invoiced.report'].create(dict_invoice_report)
                    list_invoice_report.append(site_invoiced_report.id)

            domain = [('id', 'in', list_invoice_report)]
            return {
                'name': _('Détails'),
                'domain': domain,
                'res_model': 'building.site.invoiced.report',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'view_mode': 'tree',
            }

            pickings_diesel = self.env['stock.picking'].search([('site_id', '=', self.site_id.id), ('state', '=', 'done'), ('location_dest_id', '=', self.site_id.location_diesel_id.id)])

        if self.r0 == 'product':
            self.env['building.site.stock.report'].search([('site_id', '=', self.site_id.id), ('type_op', '=', 'in'), ('pick_categ', '=', 'product')]).unlink()
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')])
            internal_pickings = self.env['stock.picking'].search([('site_id', '=', self.site_id.id), ('picking_type_id', 'in', picking_type.ids), ('state', '=', 'done')])
            pickings = self.env['stock.picking'].search([('site_id', '=', self.site_id.id), ('state', '=', 'done'), ('location_dest_id', '=', self.site_id.location_id.id), ('id', 'not in', internal_pickings.ids)])

            list_stock_report = []
            if pickings:
                for pick in pickings:
                    for mv in pick.move_ids_without_package:
                        # last_price = self._get_product_last_price(executed.site_id, mv.product_id.id)
                        # mvs = self.env['stock.move'].search([('site_id', '=', self.site_id.id), ('location_id', '=', self.site_id.location_id.id), ('product_id', '=', mv.product_id.id), ('state', '=', 'done')])
                        # sum_qty = sum(mvt.product_uom_qty for mvt in mvs)
                        type_product = dict_type_by_product[self.site_id.id][mv.product_id.id]
                        if type_product == 'material':
                            dict_stock_report = {
                                'date' : mv.date.date(),
                                'year' : mv.date.year,
                                'month': mv.date.month,
                                'purchase_id' : mv.purchase_line_id.order_id.id if mv.purchase_line_id else False, 
                                'purchase_user_id' : mv.purchase_line_id.order_id.user_id.id if mv.purchase_line_id else False, 
                                'picking_id' : pick.id,
                                'partner_id' : pick.partner_id.id,
                                'site_id' : pick.site_id.id,
                                'type_op' : 'in',
                                'pick_categ': 'product',
                                'stock_user_id' : pick.user_id.id,
                                'description' : mv.product_id.name,
                                'qty' : mv.product_uom_qty,
                                'uom_id' : mv.product_uom.id,
                                'price_unit' : mv.price_unit,
                                'amount': mv.price_unit*mv.product_uom_qty
                            }
                            site_stock_report = self.env['building.site.stock.report'].create(dict_stock_report)
                            list_stock_report.append(site_stock_report.id)

            domain = [('id', 'in', list_stock_report)]
            return {
                'name': _('Détails'),
                'domain': domain,
                'res_model': 'building.site.stock.report',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'view_mode': 'tree',
            }

        if self.r0 == 'consu':
            self.env['building.site.stock.report'].search([('site_id', '=', self.site_id.id), ('type_op', '=', 'in'), ('pick_categ', '=', 'consu')]).unlink()
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')])
            internal_pickings = self.env['stock.picking'].search([('site_id', '=', self.site_id.id), ('picking_type_id', 'in', picking_type.ids), ('state', '=', 'done')])
            pickings = self.env['stock.picking'].search([('site_id', '=', self.site_id.id), ('state', '=', 'done'), ('location_dest_id', '=', self.site_id.location_id.id), ('id', 'not in', internal_pickings.ids)])

            list_stock_report = []
            if pickings:
                for pick in pickings:
                    for mv in pick.move_ids_without_package:
                        # last_price = self._get_product_last_price(executed.site_id, mv.product_id.id)
                        # mvs = self.env['stock.move'].search([('site_id', '=', self.site_id.id), ('location_id', '=', self.site_id.location_id.id), ('product_id', '=', mv.product_id.id), ('state', '=', 'done')])
                        # sum_qty = sum(mvt.product_uom_qty for mvt in mvs)
                        type_product = dict_type_by_product[self.site_id.id][mv.product_id.id]
                        if type_product == 'conso':
                            dict_stock_report = {
                                'date' : mv.date.date(),
                                'year' : mv.date.year,
                                'month': mv.date.month,
                                'purchase_id' : mv.purchase_line_id.order_id.id if mv.purchase_line_id else False, 
                                'purchase_user_id' : mv.purchase_line_id.order_id.user_id.id if mv.purchase_line_id else False, 
                                'picking_id' : pick.id,
                                'partner_id' : pick.partner_id.id,
                                'site_id' : pick.site_id.id,
                                'type_op' : 'in',
                                'pick_categ': 'consu',
                                'stock_user_id' : pick.user_id.id,
                                'description' : mv.product_id.name,
                                'qty' : mv.product_uom_qty,
                                'uom_id' : mv.product_uom.id,
                                'price_unit' : mv.price_unit,
                                'amount': mv.price_unit*mv.product_uom_qty
                            }
                            site_stock_report = self.env['building.site.stock.report'].create(dict_stock_report)
                            list_stock_report.append(site_stock_report.id)

            domain = [('id', 'in', list_stock_report)]
            return {
                'name': _('Détails'),
                'domain': domain,
                'res_model': 'building.site.stock.report',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'view_mode': 'tree',
            }

        if self.r0 == 'diesel':
            self.env['building.site.stock.report'].search([('site_id', '=', self.site_id.id), ('type_op', '=', 'in'), ('pick_categ', '=', 'consu')]).unlink()
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')])
            internal_pickings = self.env['stock.picking'].search([('site_id', '=', self.site_id.id), ('picking_type_id', 'in', picking_type.ids), ('state', '=', 'done'), ('location_dest_id', '=', self.site_id.location_diesel_id.id)])
            # pickings = self.env['stock.picking'].search([('site_id', '=', self.site_id.id), ('state', '=', 'done'), ('location_dest_id', '=', self.site_id.location_id.id), ('id', 'not in', internal_pickings.ids)])

            list_stock_report = []
            if internal_pickings:
                for pick in internal_pickings:
                    for mv in pick.move_ids_without_package:
                        # last_price = self._get_product_last_price(executed.site_id, mv.product_id.id)
                        # mvs = self.env['stock.move'].search([('site_id', '=', self.site_id.id), ('location_id', '=', self.site_id.location_id.id), ('product_id', '=', mv.product_id.id), ('state', '=', 'done')])
                        # sum_qty = sum(mvt.product_uom_qty for mvt in mvs)
                        # type_product = dict_type_by_product[mv.product_id.id]
                        # if type_product == 'material':
                        dict_stock_report = {
                            'date' : mv.date.date(),
                            'year' : mv.date.year,
                            'month': mv.date.month,
                            'purchase_id' : mv.purchase_line_id.order_id.id if mv.purchase_line_id else False, 
                            'purchase_user_id' : mv.purchase_line_id.order_id.user_id.id if mv.purchase_line_id else False, 
                            'picking_id' : pick.id,
                            'partner_id' : pick.partner_id.id,
                            'site_id' : pick.site_id.id,
                            'type_op' : 'in',
                            'pick_categ': 'diesel',
                            'stock_user_id' : pick.user_id.id,
                            'description' : mv.product_id.name,
                            'qty' : mv.product_uom_qty,
                            'uom_id' : mv.product_uom.id,
                            'price_unit' : mv.price_unit,
                            'amount': mv.price_unit*mv.product_uom_qty
                        }
                    site_stock_report = self.env['building.site.stock.report'].create(dict_stock_report)
                    list_stock_report.append(site_stock_report.id)

            domain = [('id', 'in', list_stock_report)]
            return {
                'name': _('Détails'),
                'domain': domain,
                'res_model': 'building.site.stock.report',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'view_mode': 'tree',
            }

        # if self.r0 == 'inventory':
        #     self.env['building.site.stock.report'].search([('site_id', '=', self.site_id.id), ('type_op', '=', 'in')]).unlink()
        #     pickings = self.env['stock.picking'].search([('site_id', '=', self.site_id.id), ('location_dest_id', '=', self.site_id.location_id.id), ('state', '=', 'done')])
        #     list_stock_report = []
        #     if pickings:
        #         for pick in pickings:
        #             for mv in pick.move_ids_without_package:
        #                 last_price = self._get_product_last_price(executed.site_id, mv.product_id.id)
        #                 mvs = pickings = self.env['stock.move'].search([('site_id', '=', self.site_id.id), ('location_id', '=', self.site_id.location_id.id), ('product_id', '=', mv.product_id.id), ('state', '=', 'done')])
        #                 sum_qty = sum(mvt.product_uom_qty for mvt in mvs)
        #                 dict_stock_report = {
        #                     'date' : mv.date.date(),
        #                     'year' : mv.date.year,
        #                     'month': mv.date.month,
        #                     'purchase_id' : mv.purchase_line_id.order_id.id if mv.purchase_line_id else False, 
        #                     'purchase_user_id' : mv.purchase_line_id.order_id.user_id.id if mv.purchase_line_id else False, 
        #                     'picking_id' : pick.id,
        #                     'partner_id' : pick.partner_id.id,
        #                     'site_id' : pick.site_id.id,
        #                     'type_op' : 'in',
        #                     'stock_user_id' : pick.user_id.id,
        #                     'description' : mv.product_id.name,
        #                     'qty' : mv.product_uom_qty-sum_qty,
        #                     'uom_id' : mv.product_uom.id,
        #                     'price_unit' : last_price,
        #                     'amount': last_price*(mv.product_uom_qty-sum_qty)
        #                 }
        #                 if mv.product_id.type == 'consu':
        #                     dict_stock_report['pick_categ']  = 'consu'
        #                 if mv.product_id.type == 'product':
        #                     dict_stock_report['pick_categ']  = 'product'
        #             site_stock_report = self.env['building.site.stock.report'].create(dict_stock_report)
        #             list_stock_report.append(site_stock_report.id)

        #     pickings = self.env['stock.picking'].search([('site_id', '=', self.site_id.id), ('location_dest_id', '=', self.site_id.location_diesel_id.id), ('state', '=', 'done')])
        #     if pickings:
        #         for pick in pickings:
        #             for mv in pick.move_ids_without_package:
        #                 last_price = self._get_product_last_price(executed.site_id, mv.product_id.id)
        #                 mvs = pickings = self.env['stock.move'].search([('site_id', '=', self.site_id.id), ('location_id', '=', self.site_id.location_id.id), ('product_id', '=', mv.product_id.id), ('state', '=', 'done')])
        #                 sum_qty = sum(mvt.product_uom_qty for mvt in mvs)
        #                 dict_stock_report = {
        #                     'date' : mv.date.date(),
        #                     'year' : mv.date.year,
        #                     'month': mv.date.month,
        #                     'purchase_id' :  False, 
        #                     'purchase_user_id' : False, 
        #                     'picking_id' : pick.id,
        #                     'partner_id' : False,
        #                     'site_id' : pick.site_id.id,
        #                     'pick_categ' : 'diesel',
        #                     'type_op' : 'in',
        #                     'stock_user_id' : pick.user_id.id,
        #                     'description' : mv.product_id.name,
        #                     'qty' : mv.product_uom_qty-sum_qty,
        #                     'uom_id' : mv.product_uom.id,
        #                     'price_unit' : last_price,
        #                     'amount': last_price*(mv.product_uom_qty-sum_qty)
        #                 }
        #             site_stock_report = self.env['building.site.stock.report'].create(dict_stock_report)
        #             list_stock_report.append(site_stock_report.id)

        #     domain = [('id', 'in', list_stock_report)]
        #     return {
        #         'name': _('Détails'),
        #         'domain': domain,
        #         'res_model': 'building.site.stock.report',
        #         'type': 'ir.actions.act_window',
        #         'view_id': False,
        #         'view_mode': 'tree',
        #     }

class building_site_invoiced_report(models.Model):
    
    _name = 'building.site.invoiced.report'
    _description = "Execution report"

    date = fields.Date(string='Date de facture')
    year = fields.Char('Année')
    month = fields.Char('Mois')
    attach_id = fields.Many2one('building.attachment', 'Attachement')
    invoice_id = fields.Many2one('account.move', 'Facture')
    partner_id = fields.Many2one('res.partner', 'Partenaire')
    site_id = fields.Many2one('building.site', 'Affaire')
    type_marche  = fields.Selection([('forfait','Au Forfait'), ('metre','Au métré')], string="Type de marché", default='')
    invoice_state  = fields.Selection([('invoiced','Facturé'), ('cashed','Encaissé'), ('subconstracting','Trav'), ('other','Autre Pres. Ser')], string="Status facture", default='')
    user_id = fields.Many2one('res.users', 'Responsable')
    no_price = fields.Char('N° Prix')
    description = fields.Char('Desc')
    sale_qty = fields.Float(string='Qte Marché')
    qty = fields.Float(string='Qte Facturé')
    uom_id = fields.Many2one('uom.uom', 'Unité')
    price_unit = fields.Float(string='Prix Unit')
    amount = fields.Float(string='Montant')

class building_site_stock_report(models.Model):
    
    _name = 'building.site.stock.report'
    _description = "stock report"

    date = fields.Date(string='Date')
    year = fields.Char('Année')
    month = fields.Char('Mois')
    purchase_user_id = fields.Many2one('res.users', 'Acheteur')
    purchase_id = fields.Many2one('purchase.order', 'BC Achat')
    picking_id = fields.Many2one('stock.picking', 'BL')
    no_pick_supplier = fields.Char('BL Four')
    partner_id = fields.Many2one('res.partner', 'Fournisseur')
    site_id = fields.Many2one('building.site', 'Affaire')
    type_op  = fields.Selection([('in', 'Reception'), ('out', 'Sortie')], string="Type Produit", default='')
    pick_categ  = fields.Selection([('consu', 'Consommables'), ('product', 'Fournitures'), ('diesel', 'Gasoil')], string="Type Produit", default='')
    stock_user_id = fields.Many2one('res.users', 'Resp Recep')
    description = fields.Char('Desc')
    qty = fields.Float(string='Qte')
    uom_id = fields.Many2one('uom.uom', 'Unité')
    price_unit = fields.Float(string='Prix Unit')
    amount = fields.Float(string='Montant')


class building_executed_report(models.Model):
    
    _name = 'building.executed.report'
    _description = "Execution report"

    date = fields.Date(string='Date')
    year = fields.Char('Année')
    month = fields.Char('Année')
    day = fields.Char('Année')
    executed_id = fields.Many2one('building.executed', 'Exécution')
    site_id = fields.Many2one('building.site', 'Affaire')
    forcast_amount_business = fields.Float(string='CA Prévisionnel')
    previous_day_amount_business = fields.Float(string='CA (J-1)')
    executed_amount_business = fields.Float(string='CA')
    amount_exploitation_charges = fields.Float(string='Charges')
    amount_result_executed = fields.Float(string='Résultat de l''exploitation')
    prc_result_executed = fields.Float(string='% Résultat de l''exploitation')
    amount_forcast_result = fields.Float(string='Résultat de l''exploitation prévisionnel')
    prc_result_forcast = fields.Float(string='% Résultat de l''exploitation prévisionnel')
    line_ids = fields.One2many('building.executed.line.report', 'report_exec_id', 'Details', readonly=False, copy=True)
    
    def building_executed_line_tree_view(self):
        executed_lines_report = self.env['building.executed.line.report'].search([('site_id', '=', self.site_id.id), ('report_exec_id', '=', self.id)])
        domain = [('id', 'in', executed_lines_report.ids)]
        return {
            'name': _('Détails CA'),
            'domain': domain,
            'res_model': 'building.executed.line.report',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,graph',
            'limit': 80
        }

class building_executed_report_line(models.Model):
    
    _name = 'building.executed.line.report'
    _description = "Lignes Excution report"

    report_exec_id = fields.Many2one('building.executed.report', 'Report Exec')
    date = fields.Date(string='Date')
    year = fields.Char('Année')
    month = fields.Char('Mois')
    day = fields.Char('Jour')
    executed_id = fields.Many2one('building.executed', 'Exécution')
    site_id = fields.Many2one('building.site', 'Affaire')
    r0 = fields.Selection([('forcated', 'Prévisionnels'), ('executed', 'Réalisations'), ('load', 'Charges')], string="Rubrique", default='')
    r1 = fields.Selection([('forcated', 'Prévisionnels'), ('executed', 'Réalisations'), ('equipment', 'Matériels'), ('diesel', 'Gasoil'), ('supervisor_ressource', 'Encadrements'), ('site_install', 'Installation Chantier'), ('mini_equipment', 'Petit Matériels'), ('executor_ressource', 'Main d''oeuvre'), ('consu', 'Consommables'), ('product', 'Fournitures')], string="Sous Rubrique", default='')
    amount = fields.Float(string='Montant')
    prc_amount_per_executed = fields.Float(string='Pourcentage/CA')
    is_rental = fields.Boolean("Location Externe ?", default=False)

    def building_executed_details_tree_view(self):
        self.ensure_one()
        executed_details_report = self.env['building.executed.detail.report'].search([('site_id', '=', self.site_id.id), ('report_exec_line_id', '=', self.id)])
        domain = [('id', 'in', executed_details_report.ids)]
        search_view_id = self.env.ref('building.building_executed_report_line_action').id
        return {
            'name': _('Détails'),
            'domain': domain,
            'res_model': 'building.executed.detail.report',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree',
            'search_view_id': search_view_id,
            'limit': 80
        }



class building_executed_report_detail(models.Model):
    
    _name = 'building.executed.detail.report'
    _description = "details Excution report"

    name = fields.Char('Designation')
    report_exec_id = fields.Many2one('building.executed.report', 'Report Exec')
    report_exec_line_id = fields.Many2one('building.executed.line.report', 'Report line Exec')
    date = fields.Date(string='Date')
    year = fields.Char('Année')
    month = fields.Char('Mois')
    day = fields.Char('Jour')
    executed_id = fields.Many2one('building.executed', 'Exécution')
    site_id = fields.Many2one('building.site', 'Affaire')
    uom_id = fields.Many2one('uom.uom', 'UdM')
    price_unit = fields.Float(string='Prix Unitaire')
    quantity = fields.Float(string='Quantité', readonly=False)
    amount_total = fields.Float(string='Total', readonly=False)



class building_purchase_need_report(models.Model):
    
    _name = 'building.purchase.need.report'
    _description = "need Report"
    _order = "id desc"
    
    opp_id = fields.Many2one("crm.lead", string="Marché")
    site_id = fields.Many2one("building.site", string="Affaire")
    need_id = fields.Many2one('building.purchase.need', 'Besoin')
    r0 = fields.Selection([('equipment', 'Matériels'), ('diesel', 'Gasoil'), ('supervisor_ressource', 'Encadrements'), ('site_install', 'Installation Chantier'), ('mini_equipment', 'Petit Matériels'), ('executor_ressource', 'Main d''oeuvre'), ('consu', 'Consommables'), ('product', 'Fournitures'),  ('service_provision', 'Pres. Service')], string="Rubrique", default='')
    amount = fields.Float(string='Montant')
    prc_amount_per_load = fields.Float(string='Pourcentage/Cout')
    prc_seuil = fields.Float(string='Pourcentage Seuil')