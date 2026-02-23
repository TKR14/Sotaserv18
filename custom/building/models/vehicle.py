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

class maintenance_request_resource_material(models.Model):

    _name = 'maintenance.request.resource.material'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    @api.depends('site_id', 'line_ids.categ_vec_id')
    def _compute_vecs(self):
        for rec in self:
            rec.vehicle_ids = False

            if not rec.site_id:
                continue

            needs = self.env['building.purchase.need'].search([
                ('site_id', '=', rec.site_id.id),
                ('state', '=', 'approuved'),
            ])

            available_categories = needs.equipment_ids.filtered(
                lambda l: l.price_subtotal > 0
            ).mapped('equipment_category_id')

            used_categories = rec.line_ids.filtered(
                lambda l: l.id != rec.id and l.categ_vec_id
            ).mapped('categ_vec_id')

            rec.vehicle_ids = available_categories - used_categories

    @api.depends('site_id', 'line_ids.categ_fleet_id')
    def _compute_fleet_vecs(self):
        for rec in self:
            rec.fleet_vehicle_ids = False

            if not rec.site_id:
                continue

            needs = self.env['building.purchase.need'].search([
                ('site_id', '=', rec.site_id.id),
                ('state', '=', 'approuved'),
            ])

            available_products = needs.small_equipment_ids.filtered(
                lambda l: l.price_subtotal > 0
            ).mapped('equipment_id')

            used_products = rec.line_ids.filtered(
                lambda l: l.id != rec.id and l.categ_fleet_id
            ).mapped('categ_fleet_id')

            rec.fleet_vehicle_ids = available_products - used_products

    @api.depends('site_id')
    def _compute_equips(self):
        needs = self.env['building.purchase.need'].search([('site_id', '=', self.site_id.id), ('state', '=', 'approuved')])
        equips = []
        for need in needs:
            if need.site_installation_ids:
                for s_install in need.site_installation_ids:
                    if s_install.equipment_id and s_install.equipment_id.id not in equips:
                        equips.append(s_install.equipment_id.id)
            for equip in need.mini_equipment_ids:
                if equip.equipment_id and equip.equipment_id.id not in equips:
                    equips.append(equip.equipment_id.id)
        self.equip_ids = equips

    @api.depends('site_id')
    def _compute_products(self):
        needs = self.env['building.purchase.need'].search([('site_id', '=', self.site_id.id), ('state', '=', 'approuved')])
        products = []
        for need in needs:
            if need.coffecha_ids:
                for coff in need.coffecha_ids:
                    if coff.product_id and coff.product_id.id not in products:
                        products.append(coff.product_id.id)
        self.product_ids = products

    @api.depends('site_id')
    def _compute_jobs(self):
        needs = self.env['building.purchase.need'].search([('site_id', '=', self.site_id.id), ('state', '=', 'approuved')])
        jobs = []
        for need in needs:
            if need.ressource_humain_ids:
                for n_hr in need.ressource_humain_ids:
                    if n_hr.job_id and n_hr.job_id.id not in jobs:
                        jobs.append(n_hr.job_id.id)
        self.job_ids = jobs

    def _compute_state_request(self):
        for request in self:
            for line in request.line_ids:
                if line.is_open:
                    request.is_open = True
                    request.is_open_1 = True
                    return True
            request.is_open = False
            request.is_open_1 = False

    name =  fields.Char(string='Référence de la demande', default='/', readonly=True)
    requested_by = fields.Many2one("res.users", string="Demandée par", default=lambda self: self.env.user.id)
    description = fields.Text(string="Description")
    site_id = fields.Many2one('building.site', string="Affaire", required=True, domain=lambda self: self._site_id_domain())
    site_ids = fields.Many2many('building.site')
    request_date = fields.Date(string='Date de création', default=fields.Date.context_today, tracking=True)
    state  = fields.Selection([('draft', 'Brouillon'), ('validated', 'Validée'), ('approved', 'Approuvée')], string="status", default='draft')
    line_ids = fields.One2many('maintenance.request.resource.material.line', 'maintenance_request_id', string='Demandes')
    is_equipment = fields.Boolean("Matériel ?")
    is_equip = fields.Boolean("Petit Matériel ?")
    is_product = fields.Boolean("Coffrage/EChaffaudage ?")
    is_hr = fields.Boolean("RH ?")
    vehicle_ids = fields.Many2many('maintenance.vehicle.category', 'Matériels', compute='_compute_vecs')
    fleet_vehicle_ids = fields.Many2many('product.product', 'Petit Matériels', compute='_compute_fleet_vecs')
    equip_ids = fields.Many2many('maintenance.equipment.category', 'Equipements', compute='_compute_equips')
    product_ids = fields.Many2many('product.product', 'Coffrage/EChaffaudage', compute='_compute_products')
    job_ids = fields.Many2many('hr.job', 'Postes', compute='_compute_jobs')
    is_open = fields.Boolean("Ouverte ?", compute='_compute_state_request')
    is_open_1 = fields.Boolean("Ouverte ?", compute='_compute_state_request', store=True)
    motif = fields.Char(string="Motif")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id,)
    estimated_cost = fields.Monetary(
        compute="_compute_estimated_cost",
        string="Total Estimated Cost",
        store=True,
    )

    def action_open_user_maintenance_request_resource_material_action(self, group):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
            ("group_id.name", "=", group),
            ("active", "=", True)
        ])
        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'search_default_group_requested_by': 1, 
            'default_is_equipment': 1, 
            'is_equipment': True, 
            'default_is_equip': 0,
        }

        domain = [
            ('is_equipment', '=', 1),
            ('site_id', 'in', site_ids),
        ]

        if group == "SOTASERV_DIRECTEUR_ZONE":
            context.update({
                'create': False,
                'delete': False,
                'edit': False,
            })

            domain.append(('state', '!=', 'draft'))

        return {
            'name': 'Demandes',
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request.resource.material',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('building.maintenance_request_resource_material_tree_view').id, 'tree'),
                (self.env.ref('building.maintenance_request_resource_material_form_view').id, 'form'),
            ],
            'domain': domain,
            'context': context,
        }

    def action_open_user_maintenance_request_resource_small_material_action(self, group):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
            ("group_id.name", "=", group),
            ("active", "=", True)
        ])
        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'search_default_group_requested_by':1, 
            'default_is_equip':1, 
            'is_equip': True, 
            'default_is_equipment':0
        }

        domain = [
            ('is_equip', '=', 1),
            ('site_id', 'in', site_ids)
        ]

        if group == "SOTASERV_DIRECTEUR_ZONE":
            context.update({
                'create': False,
                'delete': False,
                'edit': False,
            })

            domain.append(('state', '!=', 'draft'))

        return {
            'name': 'Demandes',
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request.resource.material',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('building.maintenance_request_resource_material_tree_view').id, 'tree'),
                (self.env.ref('building.maintenance_request_resource_small_material_form_view').id, 'form'),
            ],
            'domain': domain,
            'context': context,
        }

    def _site_id_domain(self):
        domain = []

        profile_assignments = self.env["building.profile.assignment"]

        if self.env.context.get("is_equipment") or self.env.context.get("is_equip"):
            if self.env.user.has_group("building_plus.sotaserv_chef_projet"):
                profile_assignments = self.env["building.profile.assignment"].search([
                    ("user_id", "=", self.env.user.id),
                    ("group_id.name", "=", "SOTASERV_CHEF_PROJET"),
                ])
            elif self.env.user.has_group("building_plus.sotaserv_conduct_trv"):
                profile_assignments = self.env["building.profile.assignment"].search([
                    ("user_id", "=", self.env.user.id),
                    ("group_id.name", "=", "SOTASERV_CONDUCT_TRV"),
                ])

            site_ids = profile_assignments.mapped("site_id").ids
            domain = [("id", "in", site_ids)]

        return domain

    @api.depends("line_ids", "line_ids.estimated_cost")
    def _compute_estimated_cost(self):
        for rec in self:
            rec.estimated_cost = sum(rec.line_ids.mapped("estimated_cost"))

    def action_requested(self):
        for request in self:
            # if request.site_id.is_with_purchase_need and request.is_equipment:
            #     count_request = self.env['maintenance.request.resource.material'].search_count([('site_id', '=', request.site_id.id), ('state', '!=', 'draft'), ('is_equipment','=', True)])
            #     for line in request.line_ids:
            #         need_line = self.env['building.purchase.need.equipment'].search([('equipment_id', '=', line.categ_vec_id.id), ('site_id', '=', request.site_id.id), ('state', '=', 'approuved')])
            #         if line.qty > (need_line.quantity-need_line.quantity_requested):
            #             raise UserError(_('Attention!: Il y a un depassement de quantité demandée pour la categorie %s, quantité reste à demnader %s ')%(line.categ_vec_id.name, (need_line.quantity-need_line.quantity_requested)))
            #         if line.qty > need_line.quantity_remaining:
            #             raise UserError(_('Attention!: Il y a un depassement de quantité pour la categorie %s, quantité reste à affecter %s ')%(line.categ_vec_id.name, need_line.quantity_remaining))
            # if request.site_id.is_with_purchase_need and request.is_equip:
            #     count_request = self.env['maintenance.request.resource.material'].search_count([('site_id', '=', request.site_id.id), ('state', '!=', 'draft'), ('is_equip','=', True)])
            #     for line in request.line_ids:
            #         need_line = self.env['building.purchase.need.mini.equipment'].search([('equipment_id', '=', line.categ_id.id), ('site_id', '=', request.site_id.id), ('state', '=', 'approuved')])
            #         if line.categ_id.nature_equip == 'install_site':
            #             need_line = self.env['building.purchase.need.site.installation'].search([('equipment_id', '=', line.categ_id.id), ('site_id', '=', request.site_id.id), ('state', '=', 'approuved')])
            #         if line.qty > (need_line.quantity-need_line.quantity_requested):
            #             raise UserError(_('Attention!: Il y a un depassement de quantité demandée pour la categorie %s, quantité reste à demnader %s ')%(line.categ_id.name, (need_line.quantity-need_line.quantity_requested)))
            #         if line.qty > need_line.quantity_remaining:
            #             raise UserError(_('Attention!: Il y a un depassement de quantité pour la categorie %s, quantité reste à affecter %s ')%(line.categ_id.name, need_line.quantity_remaining))
            # if request.site_id.is_with_purchase_need and request.is_product:
            #     count_request = self.env['maintenance.request.resource.material'].search_count([('site_id', '=', request.site_id.id), ('state', '!=', 'draft'), ('is_product','=', True)])
            #     for line in request.line_ids:
            #         need_line = self.env['building.purchase.need.coffecha'].search([('product_id', '=', line.product_id.id), ('site_id', '=', request.site_id.id), ('state', '=', 'approuved')])
            #         if line.qty > (need_line.quantity-need_line.quantity_requested):
            #             raise UserError(_('Attention!: Il y a un depassement de quantité demandée pour la categorie %s, quantité reste à demnader %s ')%(line.product_id.name, (need_line.quantity-need_line.quantity_requested)))
            #         if line.qty > need_line.quantity_remaining:
            #             raise UserError(_('Attention!: Il y a un depassement de quantité pour la categorie %s, quantité reste à affecter %s ')%(line.product_id.name, need_line.quantity_remaining))
            # if request.site_id.is_with_purchase_need and request.is_hr:
            #     count_request = self.env['maintenance.request.resource.material'].search_count([('site_id', '=', request.site_id.id), ('state', '!=', 'draft'), ('is_hr','=', True)])
            #     for line in request.line_ids:
            #         need_line = self.env['building.purchase.need.ressource.humain'].search([('job_id', '=', line.job_id.id), ('site_id', '=', request.site_id.id), ('state', '=', 'approuved')])
            #         if line.qty > (need_line.quantity-need_line.quantity_requested):
            #             # raise UserError(str([need_line,need_line.job_id.name,need_line.quantity,need_line.quantity_requested,need_line.quantity-need_line.quantity_requested]))
            #             raise UserError(_('Attention!: Il y a un depassement de quantité demandée pour le poste %s, quantité reste à demnader %s ')%(line.job_id.name, (need_line.quantity-need_line.quantity_requested)))
            #         if line.qty > need_line.quantity_remaining:
            #             raise UserError(_('Attention!: Il y a un depassement de quantité pour la categorie %s, quantité reste à affecter %s ')%(line.job_id.name, need_line.quantity_remaining))

            domain = [('site_id', '=', self.site_id.id), ('state', '!=', 'draft')]
            number = False

            if request.is_equipment:
                count = self.search_count(domain + [('is_equipment', '=', True)]) + 1
                number = f"DM/{self.site_id.number}/{count:04d}"

            elif request.is_equip:
                count = self.search_count(domain + [('is_equip', '=', True)]) + 1
                number = f"DPM/{self.site_id.number}/{count:04d}"

            request.state = 'validated'
            request.name = number

            for idx, line in enumerate(request.line_ids, start=1):
                line.code = f"L{request.name}-{idx}"
    
    def action_open_set_draft_wizard(self):
        return {
            'name': 'Définir le Motif',
            'type': 'ir.actions.act_window',
            'res_model': 'set.draft.motif.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id}
        }
    
    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise ValidationError(
                    "Vous ne pouvez pas supprimer cette demande car son état n'est pas 'Brouillon'."
                )
        return super(maintenance_request_resource_material, self).unlink()

    def _check_step_2(self, button):
        user = self.env["res.users"].browse(self.write_uid.id)
        approval_chain_line = self.env["approval.chain.line"].search([("step_1", "=", user.id), ("parent_id.model_id", "=", self._name)])
        allowed_uids = approval_chain_line.mapped("step_2")

        if self.env.user not in allowed_uids:
            raise ValidationError(f"Vous n'êtes pas autorisé à {button} cette demande.\n\nAucune chaîne d'approbation ne ressemble à celle-ci:\n{user.name} ─ Vous")

    def action_dlm(self):
        self._check_step_2("Approuvée")
        self.state = 'approved'

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    maintenance_request_line_id = fields.Many2one('maintenance.request.resource.material.line', string='Ligne demande')

class maintenance_request_resource_material_line(models.Model):

    _name = 'maintenance.request.resource.material.line'

    maintenance_request_id = fields.Many2one('maintenance.request.resource.material', string="Demande")
    site_id = fields.Many2one('building.site', string="Affaire", related='maintenance_request_id.site_id', store=True)
    request_date = fields.Date(string='Date', related='maintenance_request_id.request_date', store=True)
    code =  fields.Char(string='Code')
    request_type  = fields.Selection([('material', 'Matériel'), ('mini_material', 'Petit Matériel'), ('executor', 'Main-d\'oeuvre'), ('supervisor', 'Encadrement')], string="Type demande", default='material')
    categ_id = fields.Many2one('maintenance.equipment.category', string="Gamme")
    categ_vec_id = fields.Many2one('maintenance.vehicle.category', string="Matériels")
    categ_fleet_id = fields.Many2one('product.product', string="Petit Matériel")
    qty = fields.Float(string='Quantité')
    quantity_affected =  fields.Float(string='Quantité Affectée', compute='_compute_state_qty_affected', store=True)
    shipping_date = fields.Date(string='Date de livraison', required=True)
    duration = fields.Float(string='Durée')
    rental_type  = fields.Selection([('internal', 'Interne'), ('external', 'Externe')], string="Type de location", default='internal')
    state  = fields.Selection([("draft", "Brouillon"), ("validated", "Validée"), ("approved", "Approuvée"), ("in_affectation", "En cours d'affectation"),("affected", "Affectée")], string="status", compute='_compute_state', store=True)
    product_id = fields.Many2one('product.product', string='Coffrage', domain=[('is_coffrage', '=', True)])
    job_id = fields.Many2one('hr.job', string='Poste')
    note =  fields.Text(string='Observation')
    is_open = fields.Boolean("Ouverte ?", compute='_compute_state_qty_affected')
    type =  fields.Selection([('equipment', 'Matériel'), ('small_equipment', 'Petit matériel')], string="Type", compute="_compute_type")
    qty_available = fields.Float(string='Quantité disponible', compute="_compute_qty_available")
    duree_available = fields.Float(string='Durée LDB', compute="_compute_duration")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id,)
    estimated_cost = fields.Monetary(string="Coût estimé", currency_field="currency_id")
    requested_by = fields.Many2one(related="maintenance_request_id.requested_by", string="Demandée par", store=True)
    vehicle_category = fields.Char(string="Catégorie", compute="_compute_vehicle_category")
    assignment_line_ids = fields.One2many('building.assignment.line', 'maintenance_request_line_id', string='Affectations') 
    move_line_ids = fields.One2many('stock.move.line', 'maintenance_request_line_id', string='Transferts de matériel')

    @api.depends(
        'qty',
        'assignment_line_ids.state',
        'move_line_ids.quantity',
    )
    def _compute_state_qty_affected(self):
        for line in self:
            assignment_count = len(line.assignment_line_ids.filtered(lambda l: l.state != 'canceled'))

            move_qty = sum(line.move_line_ids.mapped('quantity')) if line.maintenance_request_id.is_equip else 0

            line.quantity_affected = assignment_count + move_qty
            line.is_open = line.qty != line.quantity_affected

    def action_open_user_maintenance_request_resource_material_line(self, group):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
            ("group_id.name", "=", group),
            ("active", "=", True)
        ])
        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'create': 0,
            'edit': 0,
            'delete': 0,
        }

        domain = [
            ('state', 'in', ['approved', 'in_affectation', 'affected']),
            ('maintenance_request_id.is_equipment', '=', 1),
            ('maintenance_request_id.site_id', 'in', site_ids)
        ]

        return {
            'name': 'Lignes de Demandes',
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request.resource.material.line',
            'view_mode': 'tree',
            'views': [
                (self.env.ref('building.maintenance_request_resource_material_line_tree_view').id, 'tree'),
            ],
            'domain': domain,
            'context': context,
            'search_view_id': self.env.ref('building.maintenance_request_resource_material_line_search_view').id,
        }

    def action_open_user_maintenance_request_resource_small_material_line(self, group):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
            ("group_id.name", "=", group),
            ("active", "=", True)
        ])
        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'create': 0,
            'edit': 0,
            'delete': 0,
        }

        domain = [
            ('state', 'in', ['approved', 'in_affectation', 'affected']),
            ('maintenance_request_id.is_equip','=',1),
            ('maintenance_request_id.site_id', 'in', site_ids)
        ]

        return {
            'name': 'Lignes de Demandes',
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request.resource.material.line',
            'view_mode': 'tree',
            'views': [
                (self.env.ref('building.maintenance_request_resource_small_material_line_tree_view').id, 'tree'),
            ],
            'domain': domain,
            'context': context,
            'search_view_id': self.env.ref('building.maintenance_request_resource_small_equipment_line_search_view').id,
        }

    @api.depends('quantity_affected', 'qty', 'maintenance_request_id.state')
    def _compute_state(self):
        for record in self:
            if record.quantity_affected == record.qty and record.qty > 0:
                record.state = "affected"
            elif record.quantity_affected > 0 and record.quantity_affected < record.qty:
                record.state = "in_affectation"
            else:
                record.state = record.maintenance_request_id.state

    @api.constrains('qty', 'qty_available', 'duration', 'duree_available')
    def _check_qty_and_duration(self):
        for record in self:
            if record.qty <= 0:
                raise ValidationError('La quantité doit être supérieure à zéro.')
            if record.duration <= 0 and record.maintenance_request_id.is_equip == False:
                raise ValidationError('La durée doit être supérieure à zéro.')
            if record.qty > record.qty_available :
                raise ValidationError("La quantité demandée ne peut pas dépasser la quantité disponible.")
            if record.duration > record.duree_available and record.maintenance_request_id.is_equip == False:
                raise ValidationError("La durée ne peut pas être supérieure à la durée nécessaire dans la liste des besoins.")

    @api.depends('type')
    def _compute_vehicle_category(self):
        for record in self:
            if record.type == "equipment":
                record.vehicle_category = record.categ_vec_id.display_name
            if record.type == "small_equipment":
                record.vehicle_category = record.categ_fleet_id.display_name

    @api.depends('maintenance_request_id')
    def _compute_type(self):
        for record in self:
            if record.maintenance_request_id:
                if record.maintenance_request_id.is_equipment:
                    record.type = "equipment"
                elif record.maintenance_request_id.is_equip:
                    record.type = "small_equipment"
                else:
                    record.type = False
            else:
                record.type = False

    @api.onchange('qty', 'categ_vec_id', 'categ_fleet_id')
    def _onchange_estimated_cost(self):
        for record in self:
            purchase_needs = []
            if record.type == "equipment":
                purchase_needs = self.env['building.purchase.need.equipment'].search([('site_id', '=', record.site_id.id), ('equipment_category_id', '=', record.categ_vec_id.id)])
            if record.type == "small_equipment":
                purchase_needs = self.env['building.purchase.need.small.equipment'].search([('site_id', '=', record.site_id.id), ('equipment_id', '=', record.categ_fleet_id.id)])
            total_price = sum(pn.price_unit for pn in purchase_needs)
            record.estimated_cost = total_price * record.qty

    @api.onchange("categ_vec_id", "categ_fleet_id")
    def _onchange_categ_vec_fleet_id(self):
        self._compute_qty_available()

    @api.depends("site_id", "type", "categ_vec_id", "categ_fleet_id")
    def _compute_qty_available(self):
        for record in self:
            record.qty_available = 0

            need = self.env['building.purchase.need'].search([
                ('site_id', '=', record.site_id.id),
                ('state', '=', 'approuved')
            ], limit=1)

            if not need:
                continue

            request_domain = [('site_id', '=', record.site_id.id),]

            if record.id:
                request_domain.append(('id', '<', record.id))

            if record.type == "equipment" and record.categ_vec_id:
                request_domain.append(('categ_vec_id', '=', record.categ_vec_id.id))

            elif record.type == "small_equipment" and record.categ_fleet_id:
                request_domain.append(('categ_fleet_id', '=', record.categ_fleet_id.id))

            request_lines = self.env['maintenance.request.resource.material.line'].search(request_domain)
            sum_requested_qty = sum(request_lines.mapped('qty'))

            if record.type == "equipment":
                filtered_needs = need.equipment_ids.filtered(lambda n: n.equipment_category_id == record.categ_vec_id)
                if filtered_needs:
                    record.qty_available = filtered_needs[0].quantity - sum_requested_qty

            elif record.type == "small_equipment":
                filtered_needs = need.small_equipment_ids.filtered(lambda n: n.equipment_id == record.categ_fleet_id)
                if filtered_needs:
                    record.qty_available = filtered_needs[0].quantity - sum_requested_qty

            record.qty_available = max(record.qty_available, 0.0)
            
    @api.depends("site_id", "type", "categ_vec_id", "categ_fleet_id")
    def _compute_duration(self):
        for record in self:
            record.duree_available = 0

            need = self.env['building.purchase.need'].search([
                ('site_id', '=', record.site_id.id),
                ('state', '=', 'approuved')
            ], limit=1)

            if not need:
                continue

            request_domain = [
                ('site_id', '=', record.site_id.id),
            ]

            if record.id:
                request_domain.append(('id', '<', record.id))

            if record.type == "equipment" and record.categ_vec_id:
                request_domain.append(('categ_vec_id', '=', record.categ_vec_id.id))

            elif record.type == "small_equipment" and record.categ_fleet_id:
                request_domain.append(('categ_fleet_id', '=', record.categ_fleet_id.id))

            request_lines = self.env['maintenance.request.resource.material.line'].search(request_domain)
            sum_requested_duration = sum(request_lines.mapped('duration'))

            if record.type == "equipment":
                filtered_needs = need.equipment_ids.filtered(lambda n: n.equipment_category_id == record.categ_vec_id)
                if filtered_needs:
                    record.duree_available = filtered_needs[0].duree_j - sum_requested_duration

            record.duree_available = max(record.duree_available, 0.0)
    
    def action_affected(self):
        dict_wiz = {
            'site_id': self.site_id.id,
            'maintenance_request_id': self.maintenance_request_id.id,
            'maintenance_request_line_id': self.id
        }
        view_id = False
        self.env.context = dict(self.env.context)
        if self.maintenance_request_id.is_equip:
            view_id = self.env.ref("building.view_assigned_ressource_equipement", False).id
            dict_wiz['equipment_id'] =  self.categ_fleet_id.id
            self.env.context.update({'type_assigned': 'small_equipment'})

        if self.maintenance_request_id.is_equipment:
            view_id = self.env.ref("building.view_assigned_ressource_vehicule", False).id
            dict_wiz['categ_vehicule_id'] = self.categ_vec_id.id
            self.env.context.update({'type_assigned': 'equipement'})

        if self.maintenance_request_id.is_hr:
            view_id = self.env.ref("building.view_assigned_ressource_emp", False).id
            dict_wiz['job_id'] = self.job_id.id
            need_line = self.env['building.purchase.need.ressource.humain'].search([('site_id', '=', self.site_id.id), ('job_id' ,'=' ,self.job_id.id)])
            if need_line.type_resource == 'supervisor':
                dict_wiz['categ_assignment'] = 'supervisor'
            if need_line.type_resource == 'executor':
                dict_wiz['categ_assignment'] = 'executor'

            self.env.context.update({'type_assigned': 'emp'})
        
        if self.maintenance_request_id.is_product:
            view_id = self.env.ref("building.view_assigned_product", False).id
            dict_wiz['product_id'] = self.product_id.id
            dict_wiz['qty'] = self.qty
            # need_line = self.env['building.purchase.need.ressource.humain'].search([('site_id', '=', self.site_id.id), ('job_id' ,'=' ,self.job_id.id)])
            # if need_line.type_resource == 'supervisor':
            #     dict_wiz['categ_assignment'] = 'supervisor'
            # if need_line.type_resource == 'executor':
            #     dict_wiz['categ_assignment'] = 'executor'
            self.env.context.update({'type_assigned': 'product'})

        wizard = self.env['building.assigned.ressource'].create(dict_wiz)
        dict_wiz =  {
            'name': 'Affectation',
            'type': 'ir.actions.act_window',
            'res_model': 'building.assigned.ressource',
            'view_mode': 'form',
            'context': self._context,
            'view_id': view_id,
            'res_id': wizard.id,
            'target': 'new'
        }
        return dict_wiz


class materials_worked_hours(models.Model):

    _name = 'materials.worked.hours'

    @api.depends('worked_hours_by_vehicle', 'internal_location_cost')
    def _compute_amount_location(self):
        for w_mat in self:
            w_mat.internal_location_amount = w_mat.internal_location_cost*w_mat.worked_hours_by_vehicle
    
    site_id = fields.Many2one('building.site', string="Affaire")
    maintenance_request_id = fields.Many2one('maintenance.request.resource.material', string="Demande de maintenance")
    maintenance_request_line_id = fields.Many2one('maintenance.request.resource.material.line', string="Ligne de demande de maintenance")
    maintenance_request_name = fields.Char(string="Demande", related='maintenance_request_id.name')
    maintenance_line_code = fields.Char(string="Ligne de demande", related='maintenance_request_line_id.code')
    assignment_line_id = fields.Many2one('building.assignment.line', string="Ligne d'affectation")
    worked_date = fields.Date(string='Date')
    vehicle_id = fields.Many2one('fleet.vehicle', string="Engin")
    cost = fields.Float(string='Coût', related='vehicle_id.cost')
    code =  fields.Char(string='Code', related='vehicle_id.code')
    emp_id = fields.Many2one('hr.employee', string="Conducteur")
    worked_hours_by_emp = fields.Float(string='Nombre H Chauffeur')
    worked_hours_by_vehicle = fields.Float(string='Heures')
    vehicle_counter = fields.Float(string='Compteur')
    qty_diesel = fields.Float(string='Gasoil')
    signature_customer = fields.Boolean(string='Signature Client')
    note = fields.Text(string='Observation')

    #a rajouter cout de location/h et montant de location pour suivre chiffres
    internal_location_cost = fields.Float(string='Cout de location')
    internal_location_amount = fields.Float(string='CA', store = True, compute='_compute_amount_location')
    state  = fields.Selection([('draft', 'Brouillon'), ('submitted', 'Soumis'), ('validated', 'Validé'), ('invoiced', 'Facturé'),], string="status", default='draft')
    is_editable = fields.Boolean(compute='_compute_is_editable')

    def action_open_user_materials_worked_hours(self, group):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
            ("group_id.name", "=", group),
            ("active", "=", True)
        ])
        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'create': 0,
            'edit': 0,
            'delete': 0,
        }

        domain = [
            ('site_id', 'in', site_ids)
        ]

        return {
            'name': 'Pointages',
            'type': 'ir.actions.act_window',
            'res_model': 'materials.worked.hours',
            'view_mode': 'tree',
            'domain': domain,
            'context': context,
            'search_view_id': self.env.ref('building.materials_worked_hours_search_view').id,
        }

    @api.depends('state')
    def _compute_is_editable(self):
        for record in self:
            record.is_editable = (
                record.state == 'draft' and
                self.env.user.has_group('logistics.logistics_group')
            )

    def action_submitted(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError("Seuls les pointages en brouillon peuvent être soumis.")
            rec.state = 'submitted'
        return True


    def action_invoiced(self):
        for rec in self:
            if rec.state != 'validated':
                raise UserError("Seuls les pointages validés peuvent être facturés.")
            rec.state = 'invoiced'
        return True

    def action_validated(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError("Seuls les pointages soumis peuvent être validés.")
            rec.state = 'validated'
        return True

    @api.onchange('vehicle_id')
    def change_vehicle_id(self):
        if self.vehicle_id:
            self.code = self.vehicle_id.code
            self.internal_location_cost = self.vehicle_id.cost_h

    # def action_validated(self):
    #     assignment_obj = self.env['building.assignment.line']
    #     executed_ressource_obj = self.env['building.executed.equipment']
    #     for worked_h in self:
    #         if worked_h.state != 'submitted':
    #             raise UserError("Seuls les pointages soumis peuvent être validés.")

    #         building_exec = self.env['building.executed'].search([('date_start', '<=', worked_h.worked_date), ('date_end', '>=', worked_h.worked_date), ('state', '=', 'open')])
    #         day = (worked_h.worked_date-building_exec.date_start).days
    #         attr_to_upate = 'quantity'+str(day)
    #         assignment = assignment_obj.search([('vehicle_id', '=', worked_h.vehicle_id.id), ('site_id', '=', worked_h.site_id.id), ('state', '=', 'open')])
    #         if assignment:
    #             assignment = assignment[0]
    #             executed_ressource = executed_ressource_obj.search([('executed_id', '=', building_exec.id), ('site_id', '=', worked_h.site_id.id), ('assignment_id', '=', assignment.id)])
    #             if executed_ressource:
    #                 executed_ressource = executed_ressource[0]
    #                 executed_ressource.wrtie({attr_to_upate: worked_h.worked_hours_by_vehicle})
    #     return True

class transport_mission_order(models.Model):

    _name = 'transport.mission.order'

    emp_id = fields.Many2one('hr.employee', string="Conducteur")
    registration_number =  fields.Char(string='Matricule')
    vehicle_id = fields.Many2one('fleet.vehicle', string="Engin")
    code =  fields.Char(string='Code')
    date = fields.Date(string='Date')
    start_km = fields.Float(string='Km Départ')
    end_km = fields.Float(string='Km fin mission')
    trasport_schedule_ids = fields.Many2many('trasport.schedule', 'trasport_schedule_mission_order', 'trasport_schedule_id', 'trs_order_id', 'PLANNING DE TRANSPORT')

    @api.onchange('vehicle_id')
    def change_vehicle_id(self):
        if self.vehicle_id:
            self.code = self.vehicle_id.code

    @api.onchange('emp_id')
    def change_emp_id(self):
        if self.emp_id:
            self.registration_number = self.emp_id.registration_number

class trasport_schedule(models.Model):

    _name = 'trasport.schedule'

    site_src_id = fields.Many2one('building.site', string="Lieu de chargement")
    site_dest_id = fields.Many2one('building.site', string="Destination (Lieu de déchargement)")
    vehicle_id = fields.Many2one('fleet.vehicle', string="Engin")
    code =  fields.Char(string='Code')
    start_date = fields.Datetime(string='Date de départ')
    end_date = fields.Datetime(string='Date de d’arrivée')
    merchandise = fields.Char(string='MARCHANDISES')
    qty = fields.Float(string='QUANTITE')
    note = fields.Text(string='Observations')
    
    @api.onchange('vehicle_id')
    def change_vehicle_id(self):
        if self.vehicle_id:
            self.code = self.vehicle_id.code

class maintenance_request(models.Model):

    _inherit = 'maintenance.request'

    site_id = fields.Many2one('building.site', string="Localisation")
    old_serial_number =  fields.Char(string='Ancien Numéro de serie')
    new_serial_number =  fields.Char(string='Nouveau Numéro de serie')
    old_ref_battery =  fields.Char(string='Ancien Ref. Batterie')
    new_ref_battery =  fields.Char(string='Nouveau Ref. Batterie')

class fleet_vehicle_consumption(models.Model):

    _inherit = 'fleet.vehicle.consumption'

    site_id = fields.Many2one('building.site', string="Affaire")
    site_ids = fields.Many2many('building.site', string='Affaires')

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        assignment_obj = self.env['building.assignment.line']
        if self.vehicle_id:
            assignment_lines = assignment_obj.search([('vehicle_id', '=', self.vehicle_id.id), ('state', '=', 'open')])
            sites = []
            self.site_ids = [(6, 0, [])]
            if assignment_lines :
                for line in assignment_lines:
                    sites.append(line.site_id.id)
            else:
                sites = self.env['building.site'].search([])
            self.site_ids = sites
        else:
            self.site_ids = self.env['building.site'].search([])

    def action_validated(self):
        assignment_obj = self.env['building.assignment.line']
        executed_ressource_obj = self.env['building.executed.diesel']
        res = super(fleet_vehicle_consumption, self).action_validated()
        for consum in self:
            if consum.vehicle_id and consum.site_id:
                building_exec = self.env['building.executed'].search([('date_start', '<=', consum.consumption_date), ('date_end', '>=', consum.consumption_date), ('state', '=', 'open')])
                if building_exec:
                    day = (consum.consumption_date-building_exec.date_start).days
                    attr_to_upate = 'quantity'+str(day)
                    assignment = assignment_obj.search([('vehicle_id', '=', consum.vehicle_id.id), ('site_id', '=', consum.site_id.id), ('state', '=', 'open')])
                    if assignment:
                        assignment = assignment[0]
                        executed_ressource = executed_ressource_obj.search([('executed_id', '=', building_exec.id), ('site_id', '=', consum.site_id.id), ('assignment_id', '=', assignment.id)])
                        if executed_ressource:
                            executed_ressource = executed_ressource[0]
                            executed_ressource.write({attr_to_upate:consum.qty})
        return res

class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    # localisation  = fields.Selection([('workshop', 'Atelier'), ('haouzia', 'DEPOT EL HAOUZIA'), ('site', 'Chantier'), ('other', 'Autre')], string="Localisation", default='')
    # place =  fields.Char(string='Lieu')

    def _compute_odometre_remaining(self):
        consumption_obj = self.env['fleet.vehicle.consumption']
        for serv in self:
            if serv.service_type_id.category == 'service':
                odometre_remaining = serv.next_change_oil
                consu = consumption_obj.search([('site_id', '=', serv.site_id.id), ('vehicle_id', '=', serv.vehicle_id.id)], order='id desc', limit=1)
                if consu and serv.state in ('todo'):
                    odometre_remaining = odometre_remaining - consu.counter_value 
                serv.odometre_remaining = odometre_remaining
                serv.value_odometre_alert = odometre_remaining - serv.vehicle_id.controle_value_change
            if serv.service_type_id.category == 'contract':
                odometre_remaining = 365
                if serv.state in ('running'):
                    odometre_remaining = (serv.end_date - serv.start_date).days
                serv.odometre_remaining = odometre_remaining
                serv.value_odometre_alert = odometre_remaining - 5

    site_id = fields.Many2one('building.site', string="Affaire", domain=[('state', '=', 'open')])
    odometre_remaining =  fields.Float(string='Prochain vidange ?', compute='_compute_odometre_remaining')
    value_odometre_alert =  fields.Float(string='Valeur de controle', compute='_compute_odometre_remaining')
