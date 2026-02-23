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
from datetime import timedelta


MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')



class stock_picking(models.Model):
    _inherit = 'stock.picking'

    def _site_id_domain(self):
        domain = []
        if self.env.context.get("outgoing_process") or self.env.context.get("scrap_process") or self.env.context.get("return_process"):
            site_ids = self.env.context.get("site_ids")
            domain = [("id", "in", site_ids)]
        return domain
    
    site_id = fields.Many2one('building.site','Affaire', domain=lambda self: self._site_id_domain())
    order_id = fields.Many2one('building.order','BP')
    picking_type = fields.Selection([('to_stock','Vers le Stock principal'), ('to_site','Vers Affaire'), ('to_partner','Vers Client')], string="Type", default='to_stock')
    picking_filter = fields.Selection([('standard','Standard'),('specific','Specific')], string="Type",default='standard')
    origin_id =  fields.Many2one('purchase.order', string='Origin')
    mvt_type = fields.Selection([('material','Matérieaux'), ('conso','Consommables'), ('equipment','Matériels'), ('mini_equipment','Petit Matériels'), ('diesel','Gasoil'), ('load','Autres Charges')], string="Type d'achat", default='')
    date_validation = fields.Date(string='Date')
    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location",
        default=lambda self: self.env['stock.picking.type'].browse(self._context.get('default_picking_type_id')).default_location_dest_id,
        check_company=True, readonly=False, required=True,
        states={'draft': [('readonly', False)]})
    vehicle_id =  fields.Many2one('fleet.vehicle', string='IG')
    is_coffech = fields.Boolean("Coffrage/EChaffaudage ?", default=False)
    maintenance_request_line_id = fields.Many2one('maintenance.request.resource.material.line', string="Demande")
    date_deadline = fields.Datetime(string="Echéance", compute="_compute_date_deadline")
    certification_state = fields.Selection([('certification', 'Attente Certification'), ('certified', 'Certifié'), ('invoiced', 'Facturé')], default="certification", tracking=True)
    remaining_advance = fields.Float(string="Reliquat d'avance", readonly=True,)
    amount_advance_deduction = fields.Float(string="Déduction d'avance", readonly=True,)
    advance_accumulation = fields.Float(string="Cumul d'avance", compute="_compute_advance_accumulation")
    is_last = fields.Boolean(compute="_compute_is_last")
    is_cg = fields.Boolean(compute="_compute_is_cg")
    modal_message = fields.Char(string="Message")
    create_vehicle = fields.Boolean(compute="_compute_create_vehicle")

    @api.depends("move_ids_without_package")
    def _compute_create_vehicle(self):
        for picking in self:
            move_lines = picking.move_ids_without_package

            if not move_lines:
                picking.create_vehicle = False
                continue

            categories = [
                ml.product_id.categ_id.category_type
                for ml in move_lines
            ]

            if any(cat == 'equipment' for cat in categories):
                picking.create_vehicle = True
            else:
                picking.create_vehicle = False
                continue

    def action_create_vehicles(self):    
        equipment_lines = self.move_ids_without_package.filtered(
            lambda line: line.product_id.categ_id.category_type == 'equipment' and (line.quantity_done or 0) > 0
        )
        
        FleetVehicle = self.env['fleet.vehicle']
        default_model = self.env['fleet.vehicle.model'].search([], limit=1)
        vehicle_count = 0

        for line in equipment_lines:
            qty_done = int(line.quantity_done)
            for i in range(qty_done):
                FleetVehicle.create({
                    'name2': f"{line.product_id.display_name} - {i + 1}",
                    'product_id': line.product_id.id,
                    'model_id': default_model.id,
                    'is_reception_vehicle': True,
                })
            vehicle_count += qty_done

        if vehicle_count > 1:
            message = _("%s véhicules ont été créés avec succès.") % vehicle_count
        elif vehicle_count == 1:
            message = _("Le véhicule a été créé avec succès.")
        else:
            message = False
            
        return message

    def action_mark_as_certified(self):
        self.sudo().write({"certification_state":"certified", "modal_message": ""})

    def action_generate_picking_invoice(self):
        self.action_generate_invoice()

    def action_set_deduction_advance(self):
        if len(set(self.mapped("origin"))) > 1:
            raise UserError("Veuillez sélectionner uniquement des réceptions associées au même bon de commande.")
        
        if any(state != "done" for state in self.mapped("state")):
            raise UserError("Veuillez sélectionner uniquement des réceptions clôturé.")
        
        if any(certification_state == "certification" for certification_state in self.mapped("certification_state")):
            raise UserError("Veuillez sélectionner uniquement des réceptions certifié.")

        if any(self.mapped("is_invoiced")):
            raise UserError("Veuillez sélectionner uniquement les réceptions qui n'ont pas encore été facturées.")

        purchase_id = self.purchase_id

        advance_move = self.env['account.move'].search([
            ('invoice_origin', '=', purchase_id.name),
            ('site_id', '=', purchase_id.site_id.id),
            ('move_type', '=', 'in_invoice'),
            ('move_type_code', '=', 'inv_advance'),
            ('state', '!=', 'cancel'),
        ], limit=1)

        if advance_move and advance_move.amount_total > 0:
            return {
                "type": "ir.actions.act_window",
                "name": "Déduction d'avance",
                "res_model": "stock.deduction.modal.wizard",
                "view_mode": "form",
                "view_id": self.env.ref("building.stock_deduction_modal_view").id,
                "context": {
                    'default_stock_ids': [(6, 0, self.ids)],
                },
                "target": "new",
            }
        else:
            return self.action_generate_invoice()

    @api.depends("backorder_id")
    def _compute_is_last(self):
        for picking in self:
            picking.is_last = False

            backorder_id = self.env["stock.picking"].search([("backorder_id", "=", picking.id)])
            if not backorder_id:
                picking.is_last = True

    @api.depends("is_cg")
    def _compute_is_cg(self):
        for picking in self:
            picking.is_cg = False
            if self.env.user.has_group("account_plus.acount_move_group_cg"):
                picking.is_cg = True

    @api.depends('purchase_id')
    def _compute_advance_accumulation(self):
        for picking in self:
            picking.advance_accumulation = 0
            if picking.purchase_id and picking.backorder_id:
                order_id = picking.purchase_id
                if order_id.avance:
                    picking.advance_accumulation = picking.backorder_id.advance_accumulation + picking.backorder_id.amount_advance_deduction

    @api.onchange('amount_advance_deduction')
    def _check_amount_advance_deduction(self):
        if self.amount_advance_deduction > (self.remaining_advance + self.amount_advance_deduction):
                raise ValidationError("La déduction d'avance ne peut pas dépasser le reliquat d'avance.")

    @api.constrains('purchase_id', 'amount_advance_deduction', 'remaining_advance')
    def _check_amount_advance(self):
        for rec in self:
            if rec.amount_advance_deduction > (rec.remaining_advance + rec.amount_advance_deduction):
                raise ValidationError("La déduction d'avance ne peut pas dépasser le reliquat d'avance.")
                
    @api.depends("origin_id")
    def _compute_date_deadline(self):
        for rec in self:
            order_id = self.env["purchase.order"].search([("name", "=", rec.origin), ("site_id", "=", rec.site_id.id)], limit=1)
            if order_id and order_id.date_planned and order_id.payment_term_id:
                total_days = 0
                for term in order_id.payment_term_id.line_ids:
                    total_days += term.days
                rec.date_deadline = order_id.date_planned + timedelta(days=total_days)
            else:
                rec.date_deadline = False

    @api.model
    def create(self, vals):
        res = super(stock_picking, self).create(vals)
        for pick in res:
            for mv in pick.move_ids_without_package:
                mv.price_unit = mv.product_id.product_tmpl_id.standard_price
        return res

    # def button_validate(self):
    #     # internal_type = self.env['stock.picking.type'].search([('sequence_code', '=', 'INT')])
    #     for move in self:
    #         # if move.site_id and move.picking_type_id.id == internal_type.id and move.location_dest_id.id == move.site_id.location_id.id:
    #         # if move.site_id and move.location_dest_id.id in [move.site_id.location_id.id, move.site_id.location_diesel_id.id] and move.site_id.is_with_purchase_need:
    #         # if move.site_id and move.site_id.is_with_purchase_need:
    #         is_gasoil_station = move.location_id.is_mobile_station or move.location_dest_id.is_mobile_station or move.location_id.is_principal_station or move.location_dest_id.is_principal_station or (move.location_id.id == move.site_id.location_diesel_id.id)
    #         if move.site_id and not is_gasoil_station and move.site_id.is_with_purchase_need:

    #             for mline in move.move_line_ids_without_package:
    #                 need_line = self.env['building.purchase.need.line'].search([('product_id', '=', mline.product_id.id), ('site_id', '=', move.site_id.id), ('state', '=', 'approuved')])
    #                 ######controle transfert coffrage
    #                 qty_control = 0
    #                 if mline.product_id.categ_id.is_coffrage:
    #                     need_line = self.env['building.purchase.need.coffecha'].search([('product_id', '=', mline.product_id.id), ('site_id', '=', move.site_id.id), ('state', '=', 'approuved')])
    #                 # elif mline.location_dest_id.id == move.site_id.location_diesel_id.id:
    #                 #     need_line = self.env['building.purchase.need.diesel.consumption'].search([('product_id', '=', mline.product_id.id), ('site_id', '=', move.site_id.id), ('state', '=', 'approuved')])
    #                 if need_line:
    #                     need_line = need_line[0]
    #                     if mline.product_id.categ_id.is_coffrage or mline.location_dest_id.id == move.site_id.location_diesel_id.id:
    #                         qty_control = need_line.quantity_remaining
    #                     else:
    #                         qty_control = need_line.quantity_to_receve
                        
    #                     qty_to_controle = mline.qty_done
    #                     if qty_to_controle == 0:
    #                         qty_to_controle = mline.product_uom_qty
                        
    #                     if qty_to_controle > qty_control:
    #                         raise UserError(_('Attention!: Il y a un depassement de quantité pour l''article %s')%mline.product_id.name)
    #                     else:
    #                         if qty_to_controle > need_line.quantity_remaining:
    #                             raise UserError(_('Attention!: Il y a un depassement de quantité pour l''article %s')%mline.product_id.name)
    #                 else:
    #                     raise UserError(_('Attention!: Il y a pas un besoin defini pour l''article %s')%mline.product_id.name)
    #     res = super(stock_picking, self).button_validate()
    #     return res


class stock_move(models.Model):
    
    _inherit = 'stock.move'
    
        
    site_id = fields.Many2one('building.site','Affaire', related='picking_id.site_id', store=True)
    remaining_quantity = fields.Float('Quantité restant' ,default=0)
    is_first_move_internal = fields.Boolean('Premier Mouvement interne',default=True)
    price_line_id = fields.Many2one('building.price.calculation.line','Ligne Étude')
    # analytic_id = fields.Many2one('account.analytic.account','Compte analytique')
    move_type = fields.Selection(related='picking_id.picking_type', store=True, readonly=True, copy=False)
    transport_cost_unit = fields.Float('coût de transport unitaire' ,default=0.0)
    mvt_type = fields.Selection(related='picking_id.mvt_type', store=True, readonly=True, copy=False)

class stock_move_line(models.Model):
    
    _inherit = 'stock.move.line'
    
    site_id = fields.Many2one('building.site', 'Affaire', related='picking_id.site_id', store=True)
   
class stock_quant(models.Model):
    """
    Quants are the smallest unit of stock physical instances
    """
    _inherit = "stock.quant"
    _description = "Quants"

    # analytic_id = fields.Many2one('account.analytic.account', 'Compte analytique')
    site_id = fields.Many2one('building.site', 'Affaire')

    @api.model
    def create(self, values):
        if "location_id" in values:
            location_id = values.get("location_id")
            location = self.env["stock.location"].browse(location_id)
            warehouse = self.env["stock.warehouse"].search([("view_location_id", "=", location.location_id.id)])
            site = self.env["building.site"].search([("warehouse_id", "=", warehouse.id)])
            if bool(warehouse) and bool(site):
                values["site_id"] = site.id
        return super(stock_quant, self).create(values)

    def write(self, values):
        res = super(stock_quant, self).write(values)
        # if "site_id" in values:
        #     site_id = values["site_id"]
        #     self.site_id = site_id
        if "location_id" in values:
            location_id = values.get("location_id")
            location = self.env["stock.location"].browse(location_id)
            warehouse = self.env["stock.warehouse"].search([("view_location_id", "=", location.location_id.id)])
            site = self.env["building.site"].search([("warehouse_id", "=", warehouse.id)])
            if bool(warehouse) and bool(site):
                values["site_id"] = site.id
        return res
