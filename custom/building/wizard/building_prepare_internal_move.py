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
from datetime import datetime

class stock_internal_move(models.TransientModel):
 
    _name = 'stock.move.internal'
    
    location_src_id = fields.Many2one('stock.location', 'Depot Source',required=True,domain=[('usage','=','internal')])
    location_dest_id = fields.Many2one('stock.location', 'Depot Destination',required=True)
    site_id = fields.Many2one('building.site', 'Affaire')
    order_id = fields.Many2one('building.order', 'BP')
    user_id = fields.Many2one('res.users', 'User')
    picking_id = fields.Many2one('stock.picking', 'Reception')
    move_ids = fields.One2many('stock.move.internal.line', 'move_internal_id', 'Mouvement interne', domain=[('product_id', '!=', False)])
    picking_source_location_id = fields.Many2one('stock.location', string="Depot source", related='picking_id.location_id', store=False, readonly=True)
    picking_destination_location_id = fields.Many2one('stock.location', string="Depot destination", related='picking_id.location_dest_id', store=False, readonly=True)

    @api.model
    def default_get(self,fields):
        moves = []
        active_model = self._context.get('active_model')
        res = super(stock_internal_move, self).default_get(fields)
        if active_model == 'stock.picking' :
            if self._context is None: self._context = {}
            picking_ids = self._context.get('active_ids', [])
            active_model = self._context.get('active_model')
            products = []
            if not picking_ids or len(picking_ids) != 1:
                # Partial Picking Processing may only be done for one picking at a time
                return res
            assert active_model in ('stock.picking'), 'Bad context propagation'
            picking_id, = picking_ids
            picking = self.env['stock.picking'].browse(picking_id)
            for mv in picking.move_lines:
                if mv.product_id.id not in products :
                    products.append(mv.product_id.id)
                    move = {
                        'move_id': mv.id,
                        'product_id': mv.product_id.id,
                        'product_uom_id': mv.product_uom.id,
                        'sourceloc_id': mv.location_id.id,
                        'destinationloc_id': mv.location_dest_id.id,
                        'date': mv.date,
                        # 'analytic_id':mv.analytic_id.id,
                    }
                    if mv.is_first_move_internal :
                        move['quantity'] = mv.product_uom_qty
                    else :
                        move['quantity'] = mv.remaining_quantity

                    moves.append((0, 0, move))
            res.update(move_ids = moves)
            res.update(user_id = self._uid)
            res.update(site_id = picking.site_id.id)
            res.update(order_id = picking.order_id.id)
            res.update(picking_id = picking_id)
            res.update(location_src_id = picking.location_dest_id.id)
            res.update(location_dest_id = picking.site_id.location_id.id)
        if active_model == 'building.site' :
            site_id = self._context.get('active_id', [])
            site = self.env['building.site'].browse(site_id)
            res.update(user_id = self._uid)
            res.update(site_id = site_id)
            res.update(location_src_id = site.location_id.id)
        return res

    @api.onchange('order_id')
    def onchange_order_id(self):
        moves = []
        if self.order_id:
            order = self.order_id
            pickings = self.env['stock.picking'].search([('site_id','=',order.site_id.id), ('order_id', '=' , order.id), ('picking_type', '=' , 'to_site')])
            picking_ids = pickings.ids
            moves_site = self.env['stock.move'].search([('site_id', '=' , order.site_id.id), ('picking_id', 'in' , picking_ids)])
            products = []
            if moves_site :
                for mv in moves_site:
                    if mv.product_id.id not in products :
                        products.append(mv.product_id.id)
                        move = {
                            'move_id': mv.id,
                            'product_id': mv.product_id.id,
                            'product_uom_id': mv.product_uom.id,
                            'sourceloc_id': order.site_id.location_id.id,
                            'destinationloc_id': mv.location_dest_id.id,
                            'date': mv.date,
                            # 'analytic_id':mv.analytic_id.id,
                        }
                        if mv.is_first_move_internal :
                            move['quantity'] = mv.product_uom_qty
                        else :
                            move['quantity'] = mv.remaining_quantity
                        moves.append((0, 0, move))
                self.move_ids = moves

    def _prepare_order_picking(self):
        pick_name = self.env['ir.sequence'].get('stock.picking.in')
        pick_type_id = self.env['stock.picking.type'].search([('code','=', 'internal')])
        active_model = self._context.get('active_model')
        if active_model == 'stock.picking' :
            picking = self.picking_id
            record_pick = {
                            'name': pick_name,
                            'origin': picking.name,
                            'site_id':picking.site_id.id,
                            'order_id':picking.order_id.id,
                            'date':picking.date,
                            'picking_type_id': pick_type_id.id,
                            'picking_type_code': 'internal',
                            'partner_id': picking.partner_id.id,
                            'note': picking.note,
                            'picking_type':'to_site',
                            'picking_filter':'specific',
                            # 'invoice_state':'none',
                            'location_id': self.location_src_id.id,
                            'location_dest_id': self.location_dest_id.id
                            }
            return record_pick
        if active_model == 'building.site' :
            site = self.site_id
            date_pick = datetime.today()
            record_pick = {
                            'name': pick_name,
                            'origin': site.name,
                            'site_id':site.id,
                            'order_id':self.order_id.id,
                            'date':date_pick,
                            'picking_type_id': pick_type_id.id,
                            'picking_type_code': 'internal',
                            'partner_id': site.partner_id.id,
                            'note': site.description,
                            'picking_type':'to_partner',
                            'picking_filter':'specific',
                            # 'invoice_state':'none',
                            'location_id': self.location_src_id.id,
                            'location_dest_id': self.location_dest_id.id
                            }
            return record_pick


    def action_create_internal_move(self):
        picking_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        record_picking = self._prepare_order_picking()
        moves = []
        for move in self.move_ids :
            record_move = {
                'name': move.product_id.name,
                'site_id':self.picking_id.site_id.id,
                'product_id': move.product_id.id,
                'product_uom_qty':move.quantity,
                'product_uom': move.product_uom_id.id,
                # 'product_uos_qty': move.quantity,
                # 'product_uos': (move.move_id.product_uos and move.move_id.product_uos.id) or move.move_id.product_uom.id,
                'partner_id': self.picking_id.partner_id.id,
                'location_id': self.location_src_id.id,
                'location_dest_id': self.location_dest_id.id,
                'state': 'draft',
                'price_unit': move.move_id.price_unit or 0.0,
                # 'analytic_id':move.analytic_id.id,
                # 'invoice_state':'none',
            }
            moves.append((0, 0, record_move))
            move.move_id.write({'is_first_move_internal':False,'remaining_quantity':move.move_id.product_uom_qty-move.quantity})
        record_picking['move_lines'] = moves
        picking = self.env['stock.picking'].create(record_picking)
        # picking.action_confirm()
        # picking.action_assign()
        # picking.action_done()
        return True

class stock_internal_move_line(models.TransientModel):
    _name = 'stock.move.internal.line'

    move_id = fields.Many2one('stock.move', 'Mouvement')
    move_internal_id = fields.Many2one('stock.move.internal', 'Internal Mouvement')
    product_id = fields.Many2one('product.product', 'Produit')
    product_uom_id = fields.Many2one('uom.uom', 'Unité de mesure')
    quantity = fields.Float('Quantité Restant', default = 1.0)
    sourceloc_id = fields.Many2one('stock.location', 'Depot source', required=False)
    destinationloc_id = fields.Many2one('stock.location', 'Depot destination', required=False)
    date = fields.Datetime('Date')
    # analytic_id=fields.Many2one('account.analytic.account','Compte analytique')