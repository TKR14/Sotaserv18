
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
from datetime import datetime
from dateutil.relativedelta import relativedelta



class account_analytic_account(models.Model):

    _inherit = 'account.analytic.account'

    site_id = fields.Many2one('building.site')
    product_id = fields.Many2one('product.product', 'Produit')
    order_id = fields.Many2one('building.order', 'Réf DQE')
    origin_id = fields.Many2one('building.order.line', 'Réf ligne DQE')
    number = fields.Char("Numéro du Chantier",size=256)
    account_analytic_type = fields.Selection([("stock", "Stock"),("timesheet", "Temps de travail"),('material','Fourniture'),("subcontracting", "Sous-traitance"),("workforce", "Main-d’œuvre"),("equipment","Matériel"),("vehicule","Véhicule"),("load", "Charge"),("production", "Production Entreprise"),("purchase", "Achat"),("service", "Service"),("Other", "Divers")], string="Type de ligne",default='production')

class account_analytic_account_template(models.Model):

    _name = 'account.analytic.account.template'

    name =fields.Char('Nom du Compte', required=True, track_visibility='onchange')
    code = fields.Char('Référence', select=True, track_visibility='onchange', copy=False)
    account_analytic_type  = fields.Selection([('workforce','Main-d’œuvre'),('equipment','Matériel'),('material','Fourniture'),('service','Service')], string="Catégorie du compte",default='material')
    type_compte = fields.Selection([('view','Vue Analytique'), ('normal','Compte analytique'),('contract','Contrat ou Projet'),('template','Template')], 'Type de compte', required=True)
    description = fields.Text('Description')
    parent_id = fields.Many2one('account.analytic.account.template', 'Compte Parent', select=2)
    child_ids = fields.One2many('account.analytic.account.template', 'parent_id', 'Comptes analytique')
    company_id = fields.Many2one('res.company', 'Société', required=False)

# class building_order(models.Model):

#     _inherit = 'building.order'

#     def action_gained(self):
#         res=super(building_order,self).action_gained()
#         analytic_obj=self.env['account.analytic.account']
#         if not self.amendment :
#             record_analytic_account={
#                 'name':'Matériels',
#                 'code':'Frais de matériel',
#                 # 'type': 'normal' ,
#                 'product_id': False,
#                 'site_id':self.site_id.id,
#                 'order_id':self.id,
#                 'account_analytic_type':'equipment',
#             }

#             analytic_obj.create(record_analytic_account)

#             record_analytic_account={
#                 'name':'Fournitures',
#                 'code':'Achats de fourniture',
#                 # 'type': 'normal' ,
#                 'product_id': False,
#                 'site_id':self.site_id.id,
#                 'order_id':self.id,
#                 'account_analytic_type':'material',
#             }

#             analytic_obj.create(record_analytic_account)

#             record_analytic_account={
#                 'name':'Main-d’œuvre',
#                 'code':'Imputation de la Main-d’œuvre',
#                 # 'type': 'normal' ,
#                 'product_id': False,
#                 'site_id':self.site_id.id,
#                 #'origin_id':self.id,
#                 'order_id':self.id,
#                 'account_analytic_type':'workforce',
# 		        # 'use_timesheets':True,
#             }
#             analytic_obj.create(record_analytic_account)

#             record_analytic_account={
#                 'name':'Sous-traitance',
#                 'code':'Contras de Sous traitance',
#                 # 'type': 'view' ,
#                 'product_id': False,
#                 'site_id':self.site_id.id,
#                 #'origin_id':self.id,
#                 'order_id':self.id,
#                 'account_analytic_type':'subcontracting',
#             }
#             analytic_obj.create(record_analytic_account)

#             record_analytic_account={
#                 'name':'Charges',
#                 'code':'Autres charge chantier',
#                 # 'type': 'normal' ,
#                 'product_id': False,
#                 'site_id':self.site_id.id,
#                 #'origin_id':self.id,
#                 'order_id':self.id,
#                 'account_analytic_type':'load',
#             }
#             analytic_obj.create(record_analytic_account)

#             record_analytic_account={
#                 'name':'Productions',
#                 'code':'Production de l\'Entreprise',
#                 # 'type': 'normal' ,
#                 'product_id': False,
#                 'site_id':self.site_id.id,
#                 'order_id':self.id,
#                 'account_analytic_type':'production',
#             }
#             account = analytic_obj.create(record_analytic_account)
#             for line in self.order_line :
#                 if line.display_type:
#                     line.write({'analytic_id':account.id})

#             record_analytic_account={
#                 'name':'Services',
#                 'code':'Achat de service',
#                 # 'type': 'normal' ,
#                 'product_id': False,
#                 'site_id':self.site_id.id,
#                 'order_id':self.id,
#                 'account_analytic_type':'service',
#             }
#             analytic_obj.create(record_analytic_account)

#         return res


# class building_subcontracting(models.Model):

#     _inherit = 'building.subcontracting'

#     def action_confirmed(self):
#         res = super(building_subcontracting,self).action_confirmed()
#         analytic_obj = self.env['account.analytic.account']
#         account = analytic_obj.search([('site_id','=',self.site_id.id),('account_analytic_type','=','subcontracting')],limit=1)
#         record_analytic_account = {
#                 'name':'Sous-traitance partenaire %s'%self.partner_id.name,
#                 'code': 'sous-traitance',
#                 # 'type': 'normal' ,
#                 'product_id': False,
#                 'site_id':self.site_id.id,
#                 'origin_id':line.order_line_id.id,
#                 'order_id':self.origin_id.id,
#                 'account_analytic_type':'subcontracting',
#                 'parent_id':account.id
#             }
#         analytic_account = analytic_obj.create(record_analytic_account)
#         for line in self.order_line :
#             line.write({'analytic_id':analytic_account.id})
#         return res

# class stock_picking(models.Model):

#     _inherit = 'stock.picking'

#     @api.cr_uid_ids_context
#     def do_transfer(self, cr, uid, picking_ids, context=None):
#         """
#             If no pack operation, we do simple action_done of the picking
#             Otherwise, do the pack operations
#         """
#         if not context:
#             context = {}
#         stock_move_obj = self.pool.get('stock.move')
#         for picking in self.browse(cr, uid, picking_ids, context=context):
#             if not picking.pack_operation_ids:
#                 self.action_done(cr, uid, [picking.id], context=context)
#                 continue
#             else:
#                 need_rereserve, all_op_processed = self.picking_recompute_remaining_quantities(cr, uid, picking, context=context)
#                 #create extra moves in the picking (unexpected product moves coming from pack operations)
#                 todo_move_ids = []
#                 if not all_op_processed:
#                     todo_move_ids += self._create_extra_moves(cr, uid, picking, context=context)

#                 #split move lines if needed
#                 toassign_move_ids = []
#                 for move in picking.move_lines:
#                     remaining_qty = move.remaining_qty
#                     if move.state in ('done', 'cancel'):
#                         #ignore stock moves cancelled or already done
#                         continue
#                     elif move.state == 'draft':
#                         toassign_move_ids.append(move.id)
#                     if float_compare(remaining_qty, 0,  precision_rounding = move.product_id.uom_id.rounding) == 0:
#                         if move.state in ('draft', 'assigned', 'confirmed'):
#                             todo_move_ids.append(move.id)
#                     elif float_compare(remaining_qty,0, precision_rounding = move.product_id.uom_id.rounding) > 0 and \
#                                 float_compare(remaining_qty, move.product_qty, precision_rounding = move.product_id.uom_id.rounding) < 0:
#                         new_move = stock_move_obj.split(cr, uid, move, remaining_qty, context=context)
#                         todo_move_ids.append(move.id)
#                         #Assign move as it was assigned before
#                         toassign_move_ids.append(new_move)
#                 if need_rereserve or not all_op_processed:
#                     if not picking.location_id.usage in ("supplier", "production", "inventory"):
#                         self.rereserve_quants(cr, uid, picking, move_ids=todo_move_ids, context=context)
#                     self.do_recompute_remaining_quantities(cr, uid, [picking.id], context=context)
#                 if todo_move_ids and not context.get('do_only_split'):
#                     self.pool.get('stock.move').action_done(cr, uid, todo_move_ids, context=context)
#                 elif context.get('do_only_split'):
#                     context = dict(context, split=todo_move_ids)
#             self._create_backorder(cr, uid, picking, context=context)
#             if picking.picking_type_id.code== "internal" and picking.picking_type == 'to_partner':
#                 account=self.pool.get('account.account').search(cr,uid,[('code','=','611400'),('company_id','=',picking.company_id.id) ])
#                 for move in picking.move_lines:
#                     analytic_datas = {
#                         'product_uom_id': move.product_uom.id,
#                         'product_id': move.product_id.id ,
#                         'general_account_id':account[0] ,
#                         'account_id':move.analytic_id.id,
#                         'journal_id':4 ,
#                         'ref':picking.name,
#                         'name':move.product_id.name,
#                         'currency_id': move.company_id.currency_id.id,
#                         'amount':move.price_unit*move.product_qty,
#                         'unit_amount':move.product_qty,
#                         'type':'stock',
#                         'site_id':picking.site_id.id,
#                         'order_id':picking.order_id.id,
#                                 }
#                     self.pool.get('account.analytic.line').create(cr,uid,analytic_datas)
#             if toassign_move_ids:
#                 stock_move_obj.action_assign(cr, uid, toassign_move_ids, context=context)
#         return True



class account_analytic_line(models.Model):

    _inherit = 'account.analytic.line'

    site_id = fields.Many2one('building.site')
    order_id = fields.Many2one('building.order', 'Réf BP')
    state = fields.Selection([("invoiced", "Facturé"),("paid", "payé"),("none", "Not Applicable")], string="Statut de la ligne",default='none')
    type_analytic_line = fields.Selection([("stock", "Stock"),("timesheet", "Temps de travail"),('material','Fourniture'),("subcontracting", "Sous-traitance"),("workforce", "Main-d’œuvre"),("equipment","Matériel"),("vehicule","Véhicule"),("load", "Charge"),("production", "Production Entreprise"),("purchase", "Achat"),("service", "Service"),("Other", "Divers")], string="Type de ligne",default='production')
    equipement_id = fields.Many2one('maintenance.equipment', 'Matériel')
    vehicule_id = fields.Many2one('fleet.vehicle', 'Véhicule')



# class account_move_line(models.Model):
#     _inherit = "account.move.line"
#     _description = "Journal Items"


#     def _prepare_analytic_line(self, cr, uid, obj_line, context=None):
#         """
#         Prepare the values given at the create() of account.analytic.line upon the validation of a journal item having
#         an analytic account. This method is intended to be extended in other modules.

#         :param obj_line: browse record of the account.move.line that triggered the analytic line creation
#         """
#         return {'name': obj_line.name,
#                 'date': obj_line.date,
#                 'account_id': obj_line.analytic_account_id.id,
#                 'unit_amount': obj_line.quantity,
#                 'product_id': obj_line.product_id and obj_line.product_id.id or False,
#                 'product_uom_id': obj_line.product_uom_id and obj_line.product_uom_id.id or False,
#                 'amount': (obj_line.credit or  0.0) - (obj_line.debit or 0.0),
#                 'general_account_id': obj_line.account_id.id,
#                 'journal_id': obj_line.journal_id.analytic_journal_id.id,
#                 'ref': obj_line.ref,
#                 'move_id': obj_line.id,
#                 'user_id': uid,
#                 'site_id':obj_line.move_id.site_id.id,
#                 'order_id':obj_line.move_id.order_id.id,
#                 'type':obj_line.move_id.type,
#                 'state':'invoiced',
#                }


# class account_voucher(models.Model):
#     _inherit = "account.voucher"
#     _description = "paiment"

#     @api.multi
#     def button_proforma_voucher(self):
#         res = super(account_voucher,self).button_proforma_voucher()
#         invoice_id = self._context.get('invoice_id',False)
#         inv = self.env['account.invoice'].browse(invoice_id)
#         if not inv.invoice_advance :
#             for line in inv.invoice_line :
#                 record_analytic_line = {'name': inv.number,
#                         'date': self.date,
#                         'account_id': line.account_analytic_id.id if line.account_analytic_id else False,
#                         'unit_amount': line.quantity,
#                         'product_id': line.product_id and line.product_id.id or False,
#                         'product_uom_id': line.product_id.uom_id and line.product_id.uom_id.id or False,
#                         #'amount':line.quantity*line.price_unit ,
#                         'unit_amount':line.quantity,
#                         'general_account_id': line.account_id.id,
#                         'journal_id': inv.journal_id.analytic_journal_id.id,
#                         'ref': inv.number,
#                         'user_id': self._uid,
#                         'site_id':inv.site_id.id,
#                         'order_id':inv.order_id.id,
#                         'state':'paid',
#                        }

#                 if inv.invoice_type == 'specific' :
#                     if inv.type == 'out_invoice' and not inv.invoice_advance and inv.invoice_attachment:
#                         record_analytic_line['type'] = 'production'
#                         record_analytic_line['amount'] = line.quantity*line.price_unit
#                     if inv.type == 'in_invoice' :
#                         record_analytic_line['type'] = inv.categ_invoice
#                         record_analytic_line['amount'] = - line.quantity*line.price_unit
#                         if not inv.invoice_advance and inv.invoice_attachment :
#                             record_analytic_line['type'] = 'subcontracting'
#                             record_analytic_line['amount'] = - line.quantity*line.price_unit
#                 # if inv.type == 'out_invoice' and inv.invoice_type == 'specific' and  inv.invoice_attachment :
#                 #     record_analytic_line['type'] = 'production'
#                 #     record_analytic_line['amount'] = line.quantity*line.price_unit
#                 # if inv.type == 'in_invoice' and inv.invoice_type == 'specific' and inv.invoice_attachment :
#                 #     record_analytic_line['type'] = 'subcontracting'
#                 #     record_analytic_line['amount'] = - line.quantity*line.price_unit
#                 # if inv.type == 'in_invoice' and inv.invoice_type == 'specific'  and inv.invoice_workforce :
#                 #     record_analytic_line['type'] = 'workforce'
#                 #     record_analytic_line['amount'] = - line.quantity*line.price_unit
#                 # if inv.type == 'in_invoice' and inv.invoice_type == 'specific' and inv.invoice_material :
#                 #     record_analytic_line['type'] = 'purchase'
#                 #     record_analytic_line['amount'] = - line.quantity*line.price_unit
#                 # if inv.type == 'in_invoice' and inv.invoice_type == 'specific' and inv.invoice_equipment :
#                 #     record_analytic_line['type'] = 'equipment'
#                 #     record_analytic_line['amount'] = - line.quantity*line.price_unit
#                 # if inv.type == 'in_invoice' and inv.invoice_type == 'specific' and inv.invoice_load :
#                 #     record_analytic_line['type'] = 'load'
#                 #     record_analytic_line['amount'] = - line.quantity*line.price_unit
#                 # if inv.type == 'in_invoice' and inv.invoice_type == 'specific' and inv.invoice_service :
#                 #     record_analytic_line['type'] = 'service'
#                 #     record_analytic_line['amount'] = - line.quantity*line.price_unit
#                 # if inv.type == 'in_invoice' and inv.invoice_type == 'specific' and not inv.invoice_load and not inv.invoice_material and not inv.invoice_workforce and not inv.invoice_attachment:
#                 #     record_analytic_line['type'] = 'purchase'
#                 #     record_analytic_line['amount'] = - line.quantity*line.price_unit
#                 self.env['account.analytic.line'].create(record_analytic_line)
#         return res


