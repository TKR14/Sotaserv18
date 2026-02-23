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

class fleet_vehicle(models.Model):

    _inherit = "fleet.vehicle"

    code =  fields.Char(string='Code')
    name2 =  fields.Char(string='Nom')
    classification =  fields.Char(string='Classification') #a mettre en format selection voir possibilite de paramétrage
    type_vihicle =  fields.Char(string='Type')
    serial_number = fields.Char(string='N° de serie')
    is_amort = fields.Boolean("Amoritissable ?")
    amort_year = fields.Char(string='Année')
    nb_year_amort = fields.Integer(string='Amortissement')
    state  = fields.Selection([('available', 'Disponible'), ('assigned', 'Affecté'), ('workshop', 'En Maintenance')], string="status", default='available')
    consumption = fields.Float(string='Consommation(L/J)')
    plan_to_change_car = fields.Char('Plan d''Action pour Changer de Voiture')
    plan_to_change_bike = fields.Char('Plan d''Action pour Changer de Moto')
    driver_id = fields.Many2one('hr.employee', string='Conducteur')
    controle_value_change = fields.Float(string='Valeur de controle vidange')
    unit_change = fields.Many2one('uom.uom', string='Unité de controle de vidange')
    categ_fleet_id = fields.Many2one('maintenance.vehicle.category', string='Catégorie')
    cost =  fields.Float(string='Cout de location interne')
    sale_date =  fields.Date(string='Date Vente')
    sale_value =  fields.Float(string='Valeur Vente')
    is_rental = fields.Boolean("Location ?")
    rental_end_date =  fields.Date(string='Date de fin location')
    uom_id = fields.Many2one('uom.uom', string='Unité')
    odometer_unit = fields.Selection([
        ('kilometers', 'km'),
        ('miles', 'mi'),
        ('heures', 'heures')
        ], 'Odometer Unit', default='kilometers', help='Unit of the odometer ', required=True)

    po_date =  fields.Date(string='Date Aquisition')
    cost_h =  fields.Float(string='Cout horaire de location interne')
    uom_h_id = fields.Many2one('uom.uom', string='Unité horaire')
    vehicle_picture = fields.Binary(string="Photo du véhicule")

    state_name = fields.Char(related='state_id.name')
    product_id = fields.Many2one('product.product', string="Article")

    is_reception_vehicle = fields.Boolean("Véhicule de Réception ?")

    attendance_type = fields.Selection(
        [
            ('daily', 'Journalier'),
            ('monthly', 'Mensuel'),
        ],
        string="Type de pointage",
        default='daily',
        required=True
    )

    def unlink(self):
        for vehicle in self:
            if vehicle.is_reception_vehicle:
                raise UserError(_("Vous ne pouvez pas supprimer un matériel créé depuis une réception."))
        return super(fleet_vehicle, self).unlink()

    def fields_get(self, fields=None, attributes=None):
        res = super(fleet_vehicle, self).fields_get(fields)
        fields_to_hide = ['nb_year_amort', 'classification', 'mobility_card', 'sale_date', 'rental_end_date', 'is_amort', 'driver_id', 'next_assignation_date', 'future_driver_id', 'old_location', 'is_rental', 'fuel_type']
        for field in fields_to_hide:
            if res.get(field):
                res.get(field)['searchable'] = False 
                res.get(field)['sortable'] = False
        return res

    def action_set_inscrit(self):
        inscrit_state = self.env['fleet.vehicle.state'].search([('name', '=', 'Inscrit')], limit=1)
        if inscrit_state:
            self.state_id = inscrit_state.id

    def action_set_draft(self):
        draft_state = self.env['fleet.vehicle.state'].search([('name', '=', 'Brouillon')], limit=1)
        if draft_state:
            self.state_id = draft_state.id

    # def name_get(self):
    #     result = []
    #     for record in self:
    #         result.append((record.id, "%s %s" % ('['+record.code+']', record.name2)))
    #     return result

    @api.depends('code', 'name2')
    def _compute_vehicle_name(self):
        for record in self:
            record.name = '[' + (record.code or '') + ']' + (record.name2 or '')

class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    purchaser_id = fields.Many2one('hr.employee', string="Conducteur", compute='_compute_purchaser_id', readonly=False, store=True)
    next_change_oil = fields.Float(string='Prochain vidange')
    date_next_change_oil = fields.Date(string='Date Prochain vidange')
    next_odometre = fields.Float(string='Prochain KM')
    duree = fields.Float(string='Durée')
    start_date = fields.Date(string='Date debut')
    end_date = fields.Date(string='Date de fin')
    category  = fields.Selection([('contract', 'Contrat'), ('service', 'Service')], string="Categorie", default='service', related='service_type_id.category')


# class maintenance_equipment_category(models.Model):

#     _inherit = 'maintenance.equipment.category'

#     cost =  fields.Float(string='Cout Unitaire')
#     uom_id = fields.Many2one('uom.uom', string='Unité')

class fleet_vehicle_consumption(models.Model):
    _name = 'fleet.vehicle.consumption'

    vehicle_id = fields.Many2one('fleet.vehicle', string="IG")
    type_consumption  = fields.Selection([('in_site', 'Chantier'), ('mobile_station', 'Station Mobile'), ('principal_station', 'Station Principale')], string="Station Gasoil", default='in_site')
    dest_from_principal_location = fields.Selection([('to_mobile_location', 'Vers Station Mobile'), ('to_ig', 'Vers IG')], string="Destination Gasoil", default='to_mobile_location')
    dest_from_mobile_location = fields.Selection([('to_site_location', 'Vers Chantier'), ('to_ig', 'Vers IG')], string="Destination Gasoil", default='to_site_location')
    principal_location_id = fields.Many2one('stock.location', string="Station Principale")
    mobile_location_id = fields.Many2one('stock.location', string="Station Mobile", domain=[('is_mobile_station', '=', True)])
    site =  fields.Char(string='Affaire')
    consumption_date = fields.Date(string='Date')
    num_move =  fields.Char(string='N° de sorti')
    product_id = fields.Many2one('product.product', string="Article", domain=[('categ_id.is_diesel', '=', True)])
    counter_value = fields.Float(string='Compteur')
    qty = fields.Float(string='Quantité')
    price_unit = fields.Float(string='Prix')
    amount = fields.Float(string='Montant', compute='_compute_amount')
    state  = fields.Selection([('draft', 'Brouillon'), ('validated', 'Validé')], string="status", default='draft')

    @api.depends('qty', 'price_unit')
    def _compute_amount(self):
        for cons in self:
            cons.amount = cons.qty*cons.price_unit

    def action_validated(self):
        self.state = 'validated'
        stock_location = self.env['stock.location'].search([('usage', '=', 'customer')])
        if not stock_location:
            raise UserError("Attention : il faut definir un emplacement de type client")
        stock_location = stock_location[0]
        stock_move = {
            'product_id': self.product_id.id,
            'reference': self.num_move,
            # 'location_dest_id':stock_location.id,
            'product_uom_qty':self.qty,
            'date':self.consumption_date,
            'site_id':self.site_id.id,
            'company_id':self.env.user.company_id.id,
        }

        if self.type_consumption == 'in_site':
            stock_move['location_id'] = self.site_id.location_diesel_id.id
            stock_move['location_dest_id'] = stock_location.id
                
        if self.type_consumption == 'principal_station' and self.dest_from_principal_location == 'to_ig':
            stock_move['location_id'] = self.principal_location_id.id
            stock_move['location_dest_id'] = stock_location.id
        
        if self.type_consumption == 'mobile_station' and self.dest_from_mobile_location == 'to_ig':
            stock_move['location_id'] = self.mobile_location_id.id
            stock_move['location_dest_id'] = stock_location.id

        if self.type_consumption == 'principal_station' and self.dest_from_principal_location == 'to_mobile_location':
            stock_move['location_id'] = self.principal_location_id.id
            stock_move['location_dest_id'] = self.mobile_location_id.id
        
        if self.type_consumption == 'mobile_station' and self.dest_from_mobile_location == 'to_site_location':
            stock_move['location_id'] = self.mobile_location_id.id
            stock_move['location_dest_id'] = self.site_id.location_diesel_id.id


        stock_move_line = stock_move.copy()
        stock_move['name'] = self.product_id.name
        stock_move['quantity_done'] = self.qty
        stock_move['product_uom'] = self.product_id.uom_id.id
        stock_move_line['product_uom_id'] = self.product_id.uom_id.id
        stock_move_line['qty_done'] = self.qty
        # stock_move['move_line_ids'] = [(0, 0, stock_move_line)]
        stock_warehouse = self.env['stock.warehouse'].search([('partner_id', '=', self.env.user.company_id.partner_id.id)])[0]
        stock_picking = {
            'is_compliant':'compliant',
            'site_id':self.site_id.id,
            'picking_type_id':stock_warehouse.out_type_id.id,
            'scheduled_date':self.consumption_date,
            'origin':self.num_move,
            'move_ids_without_package':[(0, 0, stock_move)],
            # 'move_line_ids_without_package':[(0, 0, stock_move_line)],
        }
        
        if self.type_consumption == 'in_site':
            stock_picking['location_id'] = self.site_id.location_diesel_id.id
            stock_picking['location_dest_id'] = stock_location.id
                
        if self.type_consumption == 'principal_station' and self.dest_from_principal_location == 'to_ig':
            stock_picking['vehicle_id'] = self.vehicle_id.id
            stock_picking['location_id'] = self.principal_location_id.id
            stock_picking['location_dest_id'] = stock_location.id
        
        if self.type_consumption == 'mobile_station' and self.dest_from_mobile_location == 'to_ig':
            stock_picking['vehicle_id'] = self.vehicle_id.id
            stock_picking['location_id'] = self.mobile_location_id.id
            stock_picking['location_dest_id'] = stock_location.id

        if self.type_consumption == 'principal_station' and self.dest_from_principal_location == 'to_mobile_location':
            stock_picking['location_id'] = self.principal_location_id.id
            stock_picking['location_dest_id'] = self.mobile_location_id.id
            stock_picking['picking_type_id'] = stock_warehouse.int_type_id.id
        
        if self.type_consumption == 'mobile_station' and self.dest_from_mobile_location == 'to_site_location':
            stock_picking['location_id'] = self.mobile_location_id.id
            stock_picking['location_dest_id'] = self.site_id.location_diesel_id.id
            stock_picking['picking_type_id'] = stock_warehouse.int_type_id.id
        # raise UserError(str(stock_picking))
        stock_pick = self.env['stock.picking'].create(stock_picking)
        stock_pick.action_confirm()
        stock_pick.button_validate()

class maintenance_request(models.Model):

    _inherit = 'maintenance.request'

    is_service_delivery = fields.Boolean("Prestation Externe ?")
    pick_num =  fields.Char(string='N° BL')
    partner_id = fields.Many2one('res.partner', string='Fournisseur', domain=[('supplier_rank', '>', 0)])
    line_ids = fields.One2many('maintenance.request.line', 'request_id', string='Réalisation', copy=True)
    odometre = fields.Float(string='Compteur')
    uom_id = fields.Many2one('uom.uom', string='Unité')
    note_motor = fields.One2many('maintenance.vehicle.note.motor', 'request_id', string='Moteur', copy=True)
    note_chasis = fields.One2many('maintenance.vehicle.note.motor', 'request_id', string='Châssis', copy=True)
    note_elec = fields.One2many('maintenance.vehicle.note.elec', 'request_id', string='Electrique', copy=True)
    note_hydro = fields.One2many('maintenance.vehicle.note.hydro', 'request_id', string='Hydraulique', copy=True)
    note_pneu = fields.One2many('maintenance.vehicle.note.pneu', 'request_id', string='Pneumatique', copy=True)
    note_other = fields.One2many('maintenance.vehicle.note.other', 'request_id', string='Autres', copy=True)
    start_date =  fields.Datetime(string='Date de début')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Matériel')
    type_maint  = fields.Selection([('equip', 'Equipement'), ('vehicle', 'Matériel'), ('coff', 'Coffrage'), ('other', 'Divers')], string="Type Maintenance", default='equip')
    cost = fields.Float(string='Coût')
    product_id = fields.Many2one('product.product', string='Coffrage', domain=[('categ_id.is_coffrage', '=', True)])
    order_id = fields.Many2one('purchase.order', string='BC', domain=[('state', '=', 'purchase')])
    order_num =  fields.Char(string='Numéro commande')
    contract_num =  fields.Char(string='Numéro contrat')
    external_cost = fields.Float(string='Coût Externe')
    stopping_cost = fields.Float(string='Coût arrêt')
    stopping_date =  fields.Datetime(string='Date d''arrêt')
    qty = fields.Float(string='Qte')

    @api.model
    def create(self, vals):
        res = super(maintenance_request, self).create(vals)
        if 'vehicle_id' in vals:
            self.vehicle_id.state = 'workshop'
        if 'equipment_id' in vals:
            self.equipment_id.state = 'under_reparation'
        return res
        
class maintenance_request_line(models.Model):

    _name = 'maintenance.request.line'

    date_exec = fields.Date("Date")
    qty_realized =  fields.Integer(string='Quantité réalisé')
    request_id = fields.Many2one('maintenance.request', string='demande')

class maintenance_vahicle_category(models.Model):

    _name = 'maintenance.vehicle.category'

    name =  fields.Char(string='Gamme')
    code =  fields.Char(string='Code')
    cost =  fields.Float(string='Cout Unitaire')
    cost_h =  fields.Float(string='Cout Unitaire horaire', digits=(15,5))
    uom_id = fields.Many2one('uom.uom', string='Unité')
    uom_h_id = fields.Many2one('uom.uom', string='Unité horaire')
    consumption = fields.Float(string='Consommation(L/J)')

class note_motor(models.Model):

    _name = 'maintenance.vehicle.note.motor'

    anom =  fields.Text(string='Anomalies constatées')
    trait =  fields.Text(string='Traitement')
    pieces =  fields.Text(string='Pièces & Consommables requis pour la réparation')
    observ = fields.Text(string='Observation')
    request_id = fields.Many2one('maintenance.request', string='demande')

class note_chasis(models.Model):

    _name = 'maintenance.vehicle.note.chasis'

    anom =  fields.Text(string='Anomalies constatées')
    trait =  fields.Text(string='Traitement')
    pieces =  fields.Text(string='Pièces & Consommables requis pour la réparation')
    observ = fields.Text(string='Observation')
    request_id = fields.Many2one('maintenance.request', string='demande')

class note_elec(models.Model):

    _name = 'maintenance.vehicle.note.elec'

    anom =  fields.Text(string='Anomalies constatées')
    trait =  fields.Text(string='Traitement')
    pieces =  fields.Text(string='Pièces & Consommables requis pour la réparation')
    observ = fields.Text(string='Observation')
    request_id = fields.Many2one('maintenance.request', string='demande')

class note_hydro(models.Model):

    _name = 'maintenance.vehicle.note.hydro'

    anom =  fields.Text(string='Anomalies constatées')
    trait =  fields.Text(string='Traitement')
    pieces =  fields.Text(string='Pièces & Consommables requis pour la réparation')
    observ = fields.Text(string='Observation')
    request_id = fields.Many2one('maintenance.request', string='demande')

class note_pneu(models.Model):

    _name = 'maintenance.vehicle.note.pneu'

    anom =  fields.Text(string='Anomalies constatées')
    trait =  fields.Text(string='Traitement')
    pieces =  fields.Text(string='Pièces & Consommables requis pour la réparation')
    observ = fields.Text(string='Observation')
    request_id = fields.Many2one('maintenance.request', string='demande')

class note_other(models.Model):

    _name = 'maintenance.vehicle.note.other'

    anom =  fields.Text(string='Anomalies constatées')
    trait =  fields.Text(string='Traitement')
    pieces =  fields.Text(string='Pièces & Consommables requis pour la réparation')
    observ = fields.Text(string='Observation')
    request_id = fields.Many2one('maintenance.request', string='demande')

# class maintenance_request_resource_material(models.Model):

#     _name = 'maintenance.request.resource.material'

#     # site =  fields.Char(string='Affaire')
#     site_id = fields.Many2one('building.site', string="Affaire")
#     request_date = fields.Date(string='Date')
#     state  = fields.Selection([('draft', 'Brouillon'), ('requested', 'Demandeur'), ('dlm', 'DLM'), ('dga', 'DGA')], string="status", default='draft')
#     line_ids = fields.One2many('maintenance.request.resource.material.line', 'maintenance_request_id', string='Demandes')

#     def action_requested(self):
#         self.state = 'requested'

#     def action_dlm(self):
#         self.state = 'dlm'

#     def action_dga(self):
#         self.state = 'dga'

# class maintenance_request_resource_material_line(models.Model):

#     _name = 'maintenance.request.resource.material.line'

#     maintenance_request_id = fields.Many2one('maintenance.request.resource.material', string="Parent")
#     # site =  fields.Char(string='Affaire')
#     site_id = fields.Many2one('building.site', string="Affaire", related='maintenance_request_id.site_id', store=True)
#     request_date = fields.Date(string='Date', related='maintenance_request_id.request_date', store=True)
#     code =  fields.Char(string='Code')
#     request_type  = fields.Selection([('material', 'Matériel'), ('mini_material', 'Petit Matériel')], string="Type demande", default='material')
#     categ_id = fields.Many2one('maintenance.equipment.category', string="Gamme")
#     categ_vec_id = fields.Many2one('maintenance.vahicle.category', string="Gamme")
#     qty = fields.Float(string='Quantité')
#     shipping_date = fields.Date(string='Date de livraison')
#     duration = fields.Float(string='Durée')
#     rental_type  = fields.Selection([('internal', 'Interne'), ('external', 'Externe')], string="Type de location", default='internal')
#     state  = fields.Selection([('draft', 'Brouillon'), ('requested', 'Demandeur'), ('dlm', 'DLM'), ('dga', 'DGA')], string="status", default='draft', related='maintenance_request_id.state')

class product_template(models.Model):
    
    _inherit="product.template"
    
    is_coffrage = fields.Boolean('Coffrage/EChaffaudage?')
