from odoo import models, api


class MaintenanceRequestResourceMaterial(models.Model):
    _inherit = "maintenance.request.resource.material"
    _description = "Demandes Matériels"

    def action_get_user_demande_material(self, readonly=False, nocreate=False):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
        ])

        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'search_default_group_by_requested_by': 1,
            'group_by': ['site_id'],
            'search_default_is_equipment': 1,
            'default_is_equipment': 1,
            'default_is_equip': 0,
            'default_is_product': 0,
            'default_site_ids': site_ids
        }

        domain = [
            ('site_id', 'in', site_ids),
            ('is_equipment','=',1)
        ]

        return {
            'name': 'Demandes Matériels',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'maintenance.request.resource.material',
            'views': [
                (self.env.ref('building.maintenance_request_resource_material_tree_view').id, 'tree'),
                (self.env.ref('building.maintenance_request_resource_material_form_view').id, 'form')
            ],
            'domain': domain,
            'context': context,
        }
    
    def action_get_user_material_requests_allocated(self, readonly=False, nocreate=False):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
        ])

        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'search_default_group_by_requested_by': 1,
            'group_by': ['site_id'],
            'create': 0,
            'search_default_is_equipment': 1, 
            'default_is_equipment': 1, 
            'default_is_equip': 0, 
            'default_is_product': 0,
            'default_site_ids': site_ids,
            
        }

        domain = [
            ('site_id', 'in', site_ids),
            ('is_equipment','=',1),
            ('is_equipment','=',1),
            ('state', '=', 'approved'),
            ('is_open_1', '=', True)
        ]

        return {
            'name': 'Demandes Matériels a Affecter',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'maintenance.request.resource.material',
            'views': [
                (self.env.ref('building.maintenance_request_resource_material_tree_view').id, 'tree'),
                (self.env.ref('building.maintenance_request_resource_material_form_view').id, 'form')
            ],
            'domain': domain,
            'context': context,
        }
    
class MaintenanceRequestResourceMaterialLine(models.Model):
    _inherit = "maintenance.request.resource.material.line"
    _description = "Demandes Matériels Line"

    def action_get_user_demande_material_line(self, readonly=False, nocreate=False):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
        ])

        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'search_default_group_by_requested_by': 1,
            'group_by': ['site_id'],
        }

        domain = [
            ('site_id', 'in', site_ids),
        ]

        return {
            'name': 'Demandes Matériels Line',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'maintenance.request.resource.material.line',
            'views': [
                (self.env.ref('building.material_requests_line_view').id, 'tree')
            ],
            'domain': domain,
            'context': context,
        }
    
class BuildingAssignmentLine(models.Model):
    _inherit = "building.assignment.line"

    def action_get_user_material_vehicle_assignments(self, readonly=False, nocreate=False):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
        ])

        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'search_default_group_by_requested_by': 1,
            'group_by': ['site_id'],
            'search_default_filt_site':1
            
        }

        domain = [
            ('site_id', 'in', site_ids),
            ('categ_assignment','=','equipment')
        ]

        return {
            'name': 'Affectations des Matériels',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'building.assignment.line',
            'views': [
                (self.env.ref('building.building_assignment_vehicle_tree').id, 'tree')
            ],
            'domain': domain,
            'context': context,
        }
    
class MaterialsWorkedHours(models.Model):
    _inherit = "materials.worked.hours"

    def action_get_user_material_scores(self, readonly=False, nocreate=False):
        return {
            'name': 'Pointages Matériels',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'materials.worked.hours',
            'views': [
                (self.env.ref('building.materials_worked_hours_tree_view').id, 'tree'),
                (self.env.ref('building.materials_worked_hours_form_view').id, 'form')
            ]
        }
    
class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    def action_get_material(self, readonly=False, nocreate=False):
        return {
            'name': 'Matériel',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'fleet.vehicle',
            'views': [
                (self.env.ref('fleet.fleet_vehicle_view_tree').id, 'tree'),
                (self.env.ref('fleet.fleet_vehicle_view_form').id, 'form')
            ]
        }
    
class FleetVehicleState(models.Model):
    _inherit = "fleet.vehicle.state"

    def action_state_material(self, readonly=False, nocreate=False):
        return {
            'name': 'Statut du Matériel',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'fleet.vehicle.state',
            'views': [
                (self.env.ref('fleet.fleet_vehicle_state_view_tree').id, 'tree'),
            ]
        }
