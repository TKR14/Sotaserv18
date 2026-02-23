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
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import time

class building_assigned_ressource(models.TransientModel):
    
    _name = 'building.assigned.ressource'
    
    @api.depends('categ_assignment', 'site_id')
    def _compute_jobs(self):
        need = self.env['building.purchase.need'].search([('site_id', '=', self.site_id.id)])
        if self.site_id and not need:
            raise UserError(_('Attention!: Il y a pas un besoin pour cette affaire %s')%self.site_id.name)
        job_ids = [line.job_id.id for line in need.ressource_humain_ids if line.type_resource == self.categ_assignment]
        self.job_ids = job_ids

    @api.depends('categ_assignment_equip', 'site_id')
    def _compute_categ_equipment(self):
        need = self.env['building.purchase.need'].search([('site_id', '=', self.site_id.id)])
        if self.site_id and not need:
            raise UserError(_('Attention!: Il y a pas un besoin pour cette affaire %s')%self.site_id.name)
        categ_ids = []
        if self.categ_assignment_equip == 'mini_equipment':
            categ_ids = [line.equipment_id.id for line in need.mini_equipment_ids]
        if self.categ_assignment_equip == 'site_installation':
            categ_ids = [line.equipment_id.id for line in need.site_installation_ids]
        self.categ_equipment_ids = categ_ids

    @api.depends('categ_assignment', 'site_id')
    def _compute_vehicules(self):
        need = self.env['building.purchase.need'].search([('site_id', '=', self.site_id.id), ('state', '=', 'approuved')])
        if self.site_id and not need:
            raise UserError(_('Attention!: Il y a pas un besoin pour cette affaire %s, ou bien nom approuvé')%self.site_id.name)
        categ_vehicule_ids = [line.equipment_category_id.id for line in need.equipment_ids]
        self.categ_vehicule_ids = categ_vehicule_ids

    @api.depends('job_id', 'site_id')
    def _compute_employees(self):
        need = self.env['building.purchase.need'].search([('site_id', '=', self.site_id.id), ('state', '=', 'approuved')])
        contracts = self.env['hr.contract'].search([('site_id', '=', self.site_id.id), ('state', '=', 'open'), ('job_id', '=', self.job_id.id)])
        employee_ids = [ctr.employee_id.id for ctr in contracts if ctr.employee_id.state == 'available']
        self.list_employee_ids = employee_ids

    start_date = fields.Date('Date de Début', required=True, readonly=False, index=True, copy=False,default=lambda *a: time.strftime('%Y-%m-%d'))
    end_date = fields.Date('Date de Fin', required=True, readonly=False, index=True, copy=False, default=lambda *a: time.strftime('%Y-%m-%d'))
    job_ids = fields.Many2many('hr.job', 'building_assigned_job_rel', 'job_id', 'emp_id', "Postes", compute='_compute_jobs')
    list_employee_ids = fields.Many2many('hr.employee', 'building_assigned_employee_rel', 'assigned_id', 'emp_id', "Employées", compute='_compute_employees')
    employee_ids = fields.Many2many('hr.employee', 'building_assigned_employee_rel', 'assigned_id', 'emp_id', "Employées")
    categ_equipment_ids = fields.Many2many('maintenance.equipment.category', string='Categories petit matériels', compute='_compute_categ_equipment')
    equipment_id = fields.Many2one('product.product', string="Petit Matériels")
    categ_vehicule_ids = fields.Many2many('maintenance.vehicle.category', 'building_assigned_job_rel', 'categ_id', 'assigned_id', "Categories Matériels", compute='_compute_vehicules')
    vehicule_ids = fields.Many2many('fleet.vehicle', 'building_assigned_vehicle_rel', 'assigned_id', 'vehicle_id', "Matériels", domain=[('state', '=', 'available')])
    categ_assignment  = fields.Selection([('supervisor', 'Encadrement'), ('executor', 'Main-d’œuvre')], string="Catégorie Affectation", default='')
    categ_assignment_equip  = fields.Selection([('site_installation', 'Installation de chantier'), ('mini_equipment', 'Outillage')], string="Catégorie Affectation", default='')
    maintenance_request_id = fields.Many2one('maintenance.request.resource.material', string="Demande")
    site_id = fields.Many2one('building.site', related='maintenance_request_id.site_id', string="Affaire")
    maintenance_request_line_id = fields.Many2one('maintenance.request.resource.material.line', string="Ligne demande")
    categ_vehicule_id = fields.Many2one('maintenance.vehicle.category', "Categorie Matériel")
    job_id = fields.Many2one('hr.job', "Poste")
    product_id = fields.Many2one('product.product', "Article")

    consumption = fields.Float(string='Consommation(L/J)')
    qty = fields.Float(string='Quantité')
    available_quantity = fields.Float(string='Quantité Disponible', compute='_compute_available_quantity')
    location_id = fields.Many2one("stock.location", string="Emplacement Source", domain=[('usage','=','internal')])

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.end_date < record.start_date:
                    raise ValidationError(
                        "La date de fin doit être postérieure ou égale à la date de début d'affectation."
                    )

    @api.depends('site_id', 'maintenance_request_line_id.categ_fleet_id')
    def _compute_available_quantity(self):
        for record in self:
            record.available_quantity = 0.0

            if not record.site_id or not record.maintenance_request_line_id.categ_fleet_id:
                continue

            warehouse = self.env['stock.warehouse'].search(
                [('code', '=', '002')],
                limit=1
            )
            lot_stock_id = warehouse.lot_stock_id
            stock_quants = self.env['stock.quant'].search([
                ('location_id', '=', lot_stock_id.id),
                ('product_id', '=', record.maintenance_request_line_id.categ_fleet_id.id),
            ])

            record.available_quantity = sum(stock_quants.mapped('available_quantity'))

    def get_nb_emp_by_job(self, site_id):
        dict_nb_emp_by_jobs = {}
        need = self.env['building.purchase.need'].search([('site_id', '=', site_id)])
        if site_id and not need:
            raise UserError(_('Attention!: Il y a pas un besoin pour cette affaire %s')%self.site_id.name)
        for line in need.ressource_humain_ids:
            if line.type_resource not in dict_nb_emp_by_jobs:
                dict_nb_emp_by_jobs[line.type_resource] = {}
            if line.job_id.id not in dict_nb_emp_by_jobs[line.type_resource]:
                dict_nb_emp_by_jobs[line.type_resource][line.job_id.id] = 0
            dict_nb_emp_by_jobs[line.type_resource][line.job_id.id] += line.quantity
        return dict_nb_emp_by_jobs

    def get_nb_emp_by_assignment_job(self, site_id):
        dict_nb_emp_by_jobs = {}
        assignment_lines = self.env['building.assignment.line'].search([('site_id', '=', site_id)])
        if assignment_lines:
            for line in assignment_lines:
                if line.categ_assignment not in dict_nb_emp_by_jobs:
                    dict_nb_emp_by_jobs[line.categ_assignment] = {}
                if line.job_id.id not in dict_nb_emp_by_jobs[line.categ_assignment]:
                    dict_nb_emp_by_jobs[line.categ_assignment][line.job_id.id] = 0
                dict_nb_emp_by_jobs[line.categ_assignment][line.job_id.id] += 1
        return dict_nb_emp_by_jobs

    def create_assigned(self):
        type_assigned = self._context.get('type_assigned', False)
        model = self._context.get('active_model', False)
        model_id = self._context.get('active_id', False)

        model_obj = self.env[model].browse(model_id)
        site_id = model_obj.site_id.id
        site = model_obj.site_id
        assignment = self.env['building.assignment'].search([('site_id', '=', site_id)])
        if not assignment:
            assignment = self.env['building.assignment'].create({'site_id': site_id})

        need = self.env['building.purchase.need'].search([('site_id', '=', site_id), ('state', '=', 'approuved')])
        if site_id and not need:
            raise UserError(_('Attention!: Il y a pas un besoin pour cette affaire %s')%self.site_id.name)

        if type_assigned == 'emp':

            uom_id = None
            uom = self.env['uom.uom'].search([('name', '=', 'H')])
            if uom:
                uom_id = uom[0].id
            uom_j_id = None
            uom_j = self.env['uom.uom'].search([('name', '=', 'J')])
            if uom_j:
                uom_j_id = uom_j[0].id

            list_record_assigned = []
            dict_nb_emp_assigned_by_job = {}
            for emp in self.employee_ids:
                contract = self.env['hr.contract'].search([('employee_id', '=', emp.id), ('state', '=', 'open')])
                
                if not contract:
                    raise UserError(_('Attention!: employée %s sans contrat, merci de créer son contrat')%emp.name)

                record_assigned ={
                                    'code':emp.registration_number,
                                    'employee_id': emp.id,
                                    'site_id' :site_id,
                                    'uom_id' : uom_id if contract.contract_type == 'cdc' else uom_j_id,
                                    'cost': contract.wage if contract.contract_type == 'cdc' else contract.wage/30,
                                    'date_start':self.start_date,
                                    'date_end' :self.end_date,
                                    'state' :'open',
                                    'type_assignment': 'emp',
                                    'categ_assignment': self.categ_assignment,
                                    'job_id': emp.job_id.id,
                                    'assignment_id': assignment.id
                                    }
                if emp.job_id.id not in dict_nb_emp_assigned_by_job:
                    dict_nb_emp_assigned_by_job[emp.job_id.id] = 0
                dict_nb_emp_assigned_by_job[emp.job_id.id] += 1
                list_record_assigned.append(record_assigned)
                
                emp.state = 'assigned' if contract.contract_type == 'cdc'  else 'available'

            for job_id, nb_emp in dict_nb_emp_assigned_by_job.items():
                ressource_by_job = self.env['building.purchase.need.ressource.humain'].search([('job_id', '=', job_id), ('need_id', '=', need[0].id)])
                job = self.env['hr.job'].browse(job_id)
                if not ressource_by_job:
                    raise UserError(_('Pas de besoin definie pour ce poste')%job.name)
                
                if nb_emp > (model_obj.qty-model_obj.quantity_affected):
                    raise UserError(_('Attention : nombre à affecter %d depasse la quantité demandée restante %d pour le Poste %s')%(nb_emp, model_obj.qty-model_obj.quantity_affected, job.name))

                if nb_emp > ressource_by_job[0].quantity_remaining:
                    raise UserError(_('Attention nombre affecté %d depasse le nombre restant a affecter %d pour ce poste %s')%(nb_emp, ressource_by_job[0].quantity_remaining, job.name))
            
            self.env['building.assignment.line'].create(list_record_assigned)
        
        if type_assigned == 'equipement':
            list_equip_assign = []
            dict_equip_assign = {}
            for equip in self.vehicule_ids:
                equips = self.env['building.purchase.need.equipment'].search([('equipment_category_id', '=', equip.categ_fleet_id.id)])
                if not equips:
                    raise UserError(_('Pas de besoin definie pour cette categorie %s')%equip.categ_fleet_id.name)
                record_assigned ={
                    'vehicle_id': equip.id,
                    'attendance_type': equip.attendance_type,
                    'site_id' :site_id,
                    'uom_id' : equip.categ_fleet_id.uom_id.id,
                    'date_start':self.start_date,
                    'date_end' :self.end_date,
                    'state' :'open',
                    'type_assignment': 'equipment',
                    'categ_assignment': 'equipment',
                    'consumption':equip.consumption,
                    'categ_fleet_id': equip.categ_fleet_id.id,
                    'assignment_id': assignment.id,
                    'maintenance_request_id' : model_obj.maintenance_request_id.id,
                    'maintenance_request_line_id': model_obj.id
                }
                list_equip_assign.append(record_assigned)
                if equip.categ_fleet_id.id not in dict_equip_assign:
                    dict_equip_assign[equip.categ_fleet_id.id] = 0
                dict_equip_assign[equip.categ_fleet_id.id] += 1
                equip.state = 'assigned'
                equip.location = site.name
            
            for category_fleet_id, nb_fleet in dict_equip_assign.items():
                fleet_by_categ = self.env['building.purchase.need.equipment'].search([('equipment_category_id', '=', category_fleet_id), ('need_id', '=', need[0].id)])
                categ = self.env['maintenance.vehicle.category'].browse(category_fleet_id)

                if not fleet_by_categ:
                    raise UserError(_('Pas de besoin definie pour cette categorie')%categ.name)
                if nb_fleet > (model_obj.qty-model_obj.quantity_affected):
                    raise UserError(_('Attention : nombre à affecter %d depasse la quantité demandée restante %d pour la categ %s')%(nb_fleet, model_obj.qty-model_obj.quantity_affected, categ.name))

                if nb_fleet > fleet_by_categ[0].quantity_remaining:
                    raise UserError(_('nombre à affecter %d depasse le nombre restant a affecter %d pour la categ %s')%(nb_equip, fleet_by_categ[0].quantity_remaining, categ.name))

            self.env['building.assignment.line'].create(list_equip_assign)

        if type_assigned == 'small_equipment':
            if self.qty > self.maintenance_request_line_id.qty:
                raise UserError(_('Quantité à affecter dépasse la quantité demandée'))
            elif self.qty < 0:
                raise UserError(_('Quantité à affecter doit être positive'))


            warehouse = self.env["stock.warehouse"].search([("code", "=", "002")], limit=1)
            picking_type_id = self.env["stock.picking.type"].search([("sequence_code", "=", "INT"), ("warehouse_id", "=", warehouse.id)], limit=1).id
            source_id = warehouse.lot_stock_id.id
            site_warehouse = self.env['stock.warehouse'].search([('site_id', '=', self.site_id.id)], limit=1)
            location_dest_id = site_warehouse.lot_stock_id.id

            move_vals = []

            move_vals.append((0, 0, {
                'product_id': self.maintenance_request_line_id.categ_fleet_id.id,
                'product_uom_qty': self.qty,
                'product_uom': self.maintenance_request_line_id.categ_fleet_id.uom_id.id,
                'name': self.maintenance_request_line_id.categ_fleet_id.display_name,
                'location_id': source_id,
                'location_dest_id': location_dest_id,
            }))

            picking = self.env['stock.picking'].create({
                'is_compliant':'compliant',
                'is_logistic': True,
                'site_id': self.site_id.id,
                'location_id': source_id,
                'location_dest_id': location_dest_id,
                'picking_type_id': picking_type_id,
                'origin': self.maintenance_request_line_id.code,
                'move_ids_without_package': move_vals,
            })

            picking.action_confirm()
            picking.action_assign()

            message = _("Transfert du petit matériel a été créé !")

            return {
                'type': 'ir.actions.act_multi',
                'actions': [
                    {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _("Succès"),
                            'message': message,
                            'type': 'success',
                            'sticky': False,
                            'next': {'type': 'ir.actions.act_window_close'},
                        }
                    }
                ]
            }

        if type_assigned == 'product':

            need_line = self.env['building.purchase.need.coffecha'].search([('site_id', '=', self.site_id.id), ('product_id' ,'=' ,self.product_id.id)])
            if not need_line:
                raise UserError(_('Pas de besoin definie pour ce produit')%self.product_id.name)

            if self.qty > (need_line.quantity-need_line.quantity_ordered):
                raise UserError(_('Attention : nombre à affecter %d depasse la quantité restante a affecter %d pour le produit %s')%(self.qty, need_line.quantity-need_line.quantity_ordered, self.product_id.name))

            if self.qty > (model_obj.qty-model_obj.quantity_affected):
                raise UserError(_('Attention : nombre à affecter %d depasse la quantité demandée restante %d pour le produit %s')%(self.qty, model_obj.qty-model_obj.quantity_affected, self.product_id.name))

            record_assigned ={
                                'code':self.product_id.code,
                                'product_id': self.product_id.id,
                                'site_id' :site_id,
                                'quantity':self.qty,
                                'uom_id' : self.product_id.uom_id.id,
                                'cost': self.product_id.standard_price,
                                'date_start':self.start_date,
                                'date_end' :self.end_date,
                                'state' :'open',
                                'type_assignment': 'product',
                                'categ_assignment': 'product',
                                # 'categ_maintenance_id': self.product_id.category_id.id,
                                'assignment_id': assignment.id,
                                'maintenance_request_id' : self.maintenance_request_id.id,
                                'maintenance_request_line_id': model_obj.id
                            }
            self.env['building.assignment.line'].create(record_assigned)

            view_id = self.env.ref("stock.view_picking_form", False).id
            stock_warehouse = self.env['stock.warehouse'].search([('partner_id', '=', self.env.user.company_id.partner_id.id)])[0]
            stock_move = {
                'product_id': self.product_id.id,
                'reference': self.maintenance_request_id.name,
                'location_id':self.location_id.id,
                'location_dest_id':self.site_id.location_id.id,
                'product_uom_qty':self.qty,
                'date':model_obj.shipping_date,
                'site_id':self.site_id.id,
                'company_id':self.env.user.company_id.id,
            }

            stock_move['name'] = self.product_id.name
            stock_move['quantity_done'] = self.qty
            stock_move['product_uom'] = self.product_id.uom_id.id
            stock_warehouse = self.env['stock.warehouse'].search([('partner_id', '=', self.env.user.company_id.partner_id.id)])[0]
            stock_picking = {
                'is_compliant':'compliant',
                'site_id':self.site_id.id,
                'picking_type_id':stock_warehouse.int_type_id.id,
                'scheduled_date':model_obj.shipping_date,
                'origin':self.maintenance_request_id.name,
                'move_ids_without_package':[(0, 0, stock_move)],
                'location_id':self.location_id.id,
                'location_dest_id':self.site_id.location_id.id,
                'is_coffech':True,
                'maintenance_request_line_id':model_obj.id
            }

            stock_pick = self.env['stock.picking'].create(stock_picking)
            
            pick_record =  {
                'name': 'Transferts',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'form',
                'view_id': view_id,
                'res_id': stock_pick.id
            }
            return pick_record
        return True

class building_assigned_close(models.TransientModel):
    
    _name = 'building.assigned.close'
    
    end_date = fields.Date('Date de Fin', required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
    location_id = fields.Many2one("stock.location", string="Emplacement Source", domain=[('usage','=','internal')])
    location_dest_id = fields.Many2one("stock.location", string="Emplacement Destination", domain=[('usage','=','internal')])
    is_product = fields.Boolean('Coffrage?', default=False)
    qty = fields.Float(string='Qte à réaffecter')

    @api.model
    def default_get(self, fields):
        if self._context is None: self._context = {}
        res = super(building_assigned_close, self).default_get(fields)
        assignment_line_id = self._context.get('active_id', [])
        assignment_line = self.env['building.assignment.line'].browse(assignment_line_id)
        is_product = self._context.get('is_product')

        if is_product:
            res.update(location_id=assignment_line.site_id.location_id.id, is_product=is_product, qty=assignment_line.quantity)
        return res

    def close_assigned(self):
        assignment_line_id = self._context.get('active_id', [])
        assignment_line = self.env['building.assignment.line'].browse(assignment_line_id)
        assignment_line.date_end = self.end_date
        assignment_line.action_closing()
        # if self.is_product:
        #     if self.qty > assignment_line.quantity:
        #         raise UserError(_('Attention : qte à réaffecter %d depasse la quantité affectée %d')%(self.qty, assignment_line.quantity))

        #     if self.qty < assignment_line.quantity:
        #         record_assigned ={
        #             'code':assignment_line.product_id.code,
        #             'product_id': assignment_line.product_id.id,
        #             'site_id' :assignment_line.site_id.id,
        #             'uom_id' : assignment_line.product_id.uom_id.id,
        #             'cost': assignment_line.product_id.standard_price,
        #             'quantity':assignment_line.quantity-self.qty,
        #             'date_start':self.end_date,
        #             'date_end' :assignment_line.date_end,
        #             'state' :'open',
        #             'type_assignment': 'product',
        #             'categ_assignment': 'product',
        #             'assignment_id': assignment_line.assignment_id.id,
        #             'maintenance_request_id' : assignment_line.maintenance_request_id.id,
        #             'maintenance_request_line_id': assignment_line.maintenance_request_line_id.id
        #         }
        #         self.env['building.assignment.line'].create(record_assigned)

        #     view_id = self.env.ref("stock.view_picking_form", False).id
        #     stock_warehouse = self.env['stock.warehouse'].search([('partner_id', '=', self.env.user.company_id.partner_id.id)])[0]
        #     stock_move = {
        #         'product_id': assignment_line.product_id.id,
        #         'reference': assignment_line.name,
        #         'location_id':stock_warehouse.int_type_id.default_location_src_id.id,
        #         'location_dest_id':assignment_line.site_id.location_id.id,
        #         'product_uom_qty':self.qty,
        #         'date':assignment_line.date_start,
        #         'site_id':assignment_line.site_id.id,
        #         'company_id':self.env.user.company_id.id,
        #     }

        #     stock_move['name'] = assignment_line.product_id.name
        #     stock_move['quantity_done'] = assignment_line.quantity
        #     stock_move['product_uom'] = assignment_line.product_id.uom_id.id
        #     stock_warehouse = self.env['stock.warehouse'].search([('partner_id', '=', self.env.user.company_id.partner_id.id)])[0]
        #     stock_picking = {
        #         'is_compliant':'compliant',
        #         'site_id':assignment_line.site_id.id,
        #         'picking_type_id':stock_warehouse.int_type_id.id,
        #         'scheduled_date':assignment_line.date_start,
        #         'origin':assignment_line.name,
        #         'move_ids_without_package':[(0, 0, stock_move)],
        #         'location_id':stock_warehouse.int_type_id.default_location_src_id.id,
        #         'location_dest_id':assignment_line.site_id.location_id.id,
        #         'is_coffech':True,
        #     }

        #     stock_pick = self.env['stock.picking'].create(stock_picking)
            
        #     pick_record =  {
        #         'name': 'Transferts',
        #         'type': 'ir.actions.act_window',
        #         'res_model': 'stock.picking',
        #         'view_mode': 'form',
        #         'view_id': view_id,
        #         'res_id': stock_pick.id
        #     }
        #     return pick_record

        return True