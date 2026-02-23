
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

MAGIC_COLUMNS = ('id','create_uid', 'create_date', 'write_uid', 'write_date')

class building_price_calculation(models.Model):
    
    _name = 'building.price.calculation'
    _description = "Etude de prix"
    _order = "id desc"

    @api.depends('line_ids.subtotal','line_ids.type_line')
    def _compute_amount(self):
        self.amount_untaxed = 0
        self.cost_amount_untaxed = 0
        self.estimated_margin_project = 0
        for line in self.line_ids :
            if line.type_line == 'price' :
                self.amount_untaxed += line.subtotal
        for price in self.building_price_detail_ids :
            self.cost_amount_untaxed += price.amount_standard_price
        if self.amount_untaxed != 0 :
            self.estimated_margin_project = ((self.amount_untaxed-self.cost_amount_untaxed)/self.amount_untaxed)*100

    name = fields.Char('Numéro du dossier d\'Étude',required=False,default=lambda self:'/')
    number = fields.Char('Nom du projet',required=False)
    ref_tendering = fields.Char('Référence appel d\'offres',required=False)
    ref_project = fields.Char('Référence Marché',required=False)
    object_project = fields.Char('Objet',required=False)
    line_ids = fields.One2many('building.price.calculation.line', 'price_calculation_id', 'Lignes d\'etude de prix', required=False)
    create_date = fields.Date(string='Date de Création',required=False,readonly=False,index=True, copy=False,default=lambda *a: time.strftime('%Y-%m-%d'))
    user_id = fields.Many2one('res.users', string='Créer Par', track_visibility='onchange',readonly=True,default=lambda self: self.env.user)
    state = fields.Selection([('draft','Brouillon'),('in_progress','En cours'),('rejected','Rajeté'),('validated','Validé'),('done','Terminé')], string='Status', required=True,default='draft',copy=False)
    partner_id = fields.Many2one('res.partner', 'Client', readonly=False,required=True, change_default=True,track_visibility='always', domain="[('customer_rank','>=', 0)]")
    commercial_id = fields.Many2one('res.users', string='Commercial', track_visibility='onchange',readonly=False,required=False)
    bid_amount = fields.Float('Montant Appel d\'offre', digits=(16, 3))
    amount_untaxed = fields.Float(string='Montant global Hors Taxes',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    cost_amount_untaxed = fields.Float(string='Montant global de revient Hors Taxes',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    estimated_margin_project = fields.Float(string='Marge prévisionnel projet',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    building_price_detail_ids = fields.One2many('building.price.details','price_calculation_id', 'Détail des prix', required=False)
    order_generated = fields.Boolean(string='Généré', readonly=True,default=False)
    with_deposit = fields.Boolean(string='Avec Caution ?', default=False)
    tender_document_id = fields.Many2one('administrative.tender.document', string='Document',readonly=False,required=False)
    deposit_amount = fields.Float('Montant de Caution', digits=(16, 3))
    deadline = fields.Datetime('Date Limite', required=False, readonly=False, copy=False)
    opening_date = fields.Datetime('Date Ouverture', required=False, readonly=False, copy=False)
    project_duration = fields.Float('Durée du projet', digits=(16, 2))

    @api.model
    def create(self,vals):
        vals['name'] = self.env['ir.sequence'].get('building.price.calculation')
        return super(building_price_calculation, self).create(vals)

    def action_validate(self):
        name = self.env['ir.sequence'].get('building.price.calculation') or '/'
        self.write({'state':'validated','name':name})

        self._cr.execute('SELECT pcl.parent_id FROM building_price_calculation pc,building_price_calculation_line pcl WHERE pc.id=pcl.price_calculation_id and pc.id = %s GROUP BY pcl.parent_id ORDER BY pcl.parent_id desc',(self.id,))
        parents_ids = [item[0] for item in self._cr.fetchall() if item[0] != None]
        if parents_ids :
            price_calculation_line = self.env['building.price.calculation.line'].browse(parents_ids[0])
            if price_calculation_line.child_ids:
                total = sum(price.subtotal for price in price_calculation_line.child_ids)
                price_calculation_line.write({'subtotal': total})

            for parent_id in parents_ids :
                total = 0
                price_calculation_line = self.env['building.price.calculation.line'].browse(parent_id)
                if price_calculation_line.child_ids :
                    total = sum(price.subtotal for price in price_calculation_line.child_ids)
                price_calculation_line.write({'subtotal':total})
        self._cr.execute('update building_price_calculation_line set state =%s where id in %s',('validated',tuple(self.line_ids.ids),))
        if self.tender_document_id :
            self.tender_document_id.write({'state':'validated'})

        # if self.with_deposit :
        #     bail_application_obj = self.env['administrative.bail.application']
        #     record_bail_application = {
        #         'name':self.env['ir.sequence'].get('administrative.bail.application'),
        #         'ref_tendering':self.ref_tendering,
        #         'bid_amount':self.bid_amount,
        #         'deposit_amount':self.deposit_amount,
        #         'price_id':self.id
        #     }
        #     bail_application=bail_application_obj.create(record_bail_application)
        #     template_obj = self.env['email.template'].search([('name', '=', 'Send Email for Bail document')], limit=1)
        #     body = template_obj.body_html
        #     body = body.replace('--name--', str(self.user_id.name))
        #     body=body.replace('--ref--', str(self.ref_tendering))
        #     body = body.replace('--num--', str(bail_application.name))
        #     body=body.replace('--amount--',str(self.deposit_amount))
        #     if template_obj:
        #         mail_values = {
        #             'subject': template_obj.subject,
        #             'body_html': body,
        #             'email_from': self.env.user.partner_id.email,
        #             'email_to':self.user_id.partner_id.email,
        #         }
        #         mail = self.env['mail.mail'].create(mail_values)
        #         mail.send()
        return True

    def _get_partner_information(self, part):
        val = {}
        if not part:
            return val
        part = self.env['res.partner'].browse(part)
        dedicated_salesman = part.user_id and part.user_id.id or self.env.user.id
        if part.child_ids :
            for contact in part.child_ids :
                if contact.type == 'invoice' :
                    partner_invoice_id = contact.id
                    partner_invoice_address = contact.contact_address
                    val = {
                            'user_id': dedicated_salesman,
                            'partner_invoice_address': partner_invoice_address,
                            'partner_invoice_id':partner_invoice_id,
                            'customer_order_ref':part.ref,
                        }
                else :
                    partner_invoice_id = part.id
                    partner_invoice_address = part.contact_address
                    val = {
                                'user_id': dedicated_salesman,
                                'partner_invoice_address': partner_invoice_address,
                                'partner_invoice_id':partner_invoice_id,
                                'customer_order_ref':part.ref,
                            }
        else :
            partner_invoice_id = part.id
            partner_invoice_address = part.contact_address
            val = {
                    'user_id': dedicated_salesman,
                    'partner_invoice_address': partner_invoice_address,
                    'partner_invoice_id':partner_invoice_id,
                    'customer_order_ref':part.ref,
                    }
        return val

    def action_create_building_order(self):
        self.order_generated = True
        record_order = {
                        'partner_id':self.partner_id.id,
                        'origin':self.name,
                        'origin_id':self.id,
                        'commercial_id':self.commercial_id.id,
                        'ref_tendering':self.ref_tendering,
                        'ref_project':self.ref_project,
                        'object_project':self.object_project,
                        'is_caution':False,
                        'deadline': self.deadline,
                        'opening_date ': self.opening_date,
                        'project_duration ': self.project_duration,
        }
        vals = self._get_partner_information(self.partner_id.id)
        record_order['user_id'] = vals['user_id']
        record_order['partner_invoice_address'] = vals['partner_invoice_address']
        record_order['partner_invoice_id'] = vals['partner_invoice_id']
        record_order['customer_order_ref'] = vals['customer_order_ref']
        record_order['is_caution'] = self.with_deposit
        order = self.env['building.order'].create(record_order)
        if self.tender_document_id :
            record_order['tender_document_id'] = self.tender_document_id.id
        lines = []
        for line in self.line_ids :
            childs = []
            if line.id not in lines :
                if line.child_ids :
                    if line.id not in lines:
                        for child in line.child_ids :
                            if child.id not in lines :
                                record_child = {
                                    'order_id': order.id,
                                    'code': child.code,
                                    'name': child.name,
                                    'price_number': child.price_number,
                                    'calculated_sales_price': child.calculated_sales_price,
                                    'price_unit': child.actual_selling_price,
                                    'type_line': child.type_line,
                                    'origin_id': child.id,
                                    'quantity': child.quantity,
                                    'product_uom': child.product_uom.id,
                                }
                                if child.type_line in ['chapter', 'component']:
                                    record_child['price_unit'] = child.subtotal
                                else:
                                    record_child['price_unit'] = child.actual_selling_price
                                childs.append((0,0,record_child))
                                lines.append(child.id)
                        record_order_line = {
                                                 'order_id':order.id,
                                                 'code':line.code,
                                                 'name':line.name,
                                                 'price_number':line.price_number,
                                                 'calculated_sales_price':line.calculated_sales_price,
                                                 'price_unit':line.actual_selling_price,
                                                 'type_line':line.type_line,
                                                 'origin_id':line.id,
                                                 'quantity':line.quantity,
                                                 'product_uom':line.product_uom.id,
                                                 'child_ids':childs if childs else None
                                            }
                        if line.type_line in ['chapter', 'component']:
                            record_order_line['price_unit'] = line.subtotal
                        else:
                            record_order_line['price_unit'] = line.actual_selling_price
                        self.env['building.order.line'].create(record_order_line)
                        lines.append(line.id)
                else :
                    record_order_line = {
                        'order_id': order.id,
                        'code': line.code,
                        'name': line.name,
                        'price_number': line.price_number,
                        'calculated_sales_price': line.calculated_sales_price,
                        'price_unit': line.actual_selling_price,
                        'type_line': line.type_line,
                        'origin_id': line.id,
                        'quantity': line.quantity,
                        'product_uom': line.product_uom.id,
                        'child_ids': childs if childs else None
                    }
                    self.env['building.order.line'].create(record_order_line)
                    lines.append(line.id)
            else :
                order_line = self.env['building.order.line'].search([('origin_id','=',line.id)])
                for child in line.child_ids:
                    if child.id not in lines:
                        record_order_line_child = {
                            'order_id': order.id,
                            'code': child.code,
                            'name': child.name,
                            'price_number': child.price_number,
                            'calculated_sales_price': child.calculated_sales_price,
                            'price_unit': child.actual_selling_price,
                            'type_line': child.type_line,
                            'origin_id': child.id,
                            'quantity': child.quantity,
                            'product_uom': child.product_uom.id,
                            'parent_id':order_line.id
                        }
                        if child.type_line in ['chapter', 'component']:
                            record_order_line_child['price_unit'] = child.subtotal
                        else:
                            record_order_line_child['price_unit'] = child.actual_selling_price
                        self.env['building.order.line'].create(record_order_line_child)
                        lines.append(child.id)
        return  True

    def action_start_price(self):
        self.state='in_progress'
        if self.tender_document_id :
            self.tender_document_id.write({'state':'in_study'})
        return True

    def action_rejected(self):
        self.state = 'rejected'
        if self.tender_document_id :
            self.tender_document_id.write({'state':'rejected'})
        return True

    def action_done(self):
        self.state = 'done'

class building_price_calculation_line(models.Model):
    
    _name = 'building.price.calculation.line'
    _description = "Lignes d\'etude de prix"
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'id'
    # _order = 'parent_left'


    @api.depends('actual_selling_price','quantity','type_line')
    def _compute_price(self):
        for line in self:
            if not line.display_type :
                price = line.actual_selling_price
                qty = line.quantity
                line.subtotal = price*qty

    name = fields.Char('Désignation',required=True)
    price_calculation_id = fields.Many2one('building.price.calculation', 'Étude des prix', required=True, ondelete='cascade', readonly=True)
    product_id = fields.Many2one('product.product','Produit')
    product_uom = fields.Many2one('uom.uom', 'Unité de mésure ', required=False, readonly=False)
    price_number = fields.Char('N° de prix',required=False)
    code = fields.Char('Code',required=False)
    calculated_sales_price = fields.Float('Prix de vente calculé', digits=(16,3))
    actual_selling_price = fields.Float('Prix de vente réel', digits=(16,3))
    type_line = fields.Selection([('chapter','Chapitre'),('component','Composant'),('price','Prix')], string='Type de la ligne', default='price',required=False)
    state = fields.Selection([('draft', 'Brouillon'),('validated', 'Validé')],string='Status', required=True, default='draft',copy=False)
    quantity = fields.Float(string='Quantité',required=True, default=1)
    parent_path = fields.Char(index=True)
    parent_id = fields.Many2one('building.price.calculation.line', 'Parent')
    child_ids = fields.One2many('building.price.calculation.line', 'parent_id', 'Childs')
    subtotal = fields.Float(string='Total HT',store=True, readonly=True, compute='_compute_price')
    # analytic_id=fields.Many2one('account.analytic.account','Compte analytique')
    # parent_left = fields.Integer('Left Parent')
    # parent_right = fields.Integer('Right Parent')
    display_type = fields.Selection([
        ('line_chapter', "Chapitre"),
        ('line_sub_chapter', "Sous Chapitre"),
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    sequence = fields.Integer(string='Sequence', default=10)

    def name_get(self):
        result = []
        for line in self:
            name = '[' + line.price_number + ']' + ' ' + line.name
            result.append((line.id, name))
        return result



    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id :
            self.product_uom = self.product_id.uom_id.id

class building_price_details(models.Model):

    _name = "building.price.details"
    _description = "Détail des prix"

    price_calculation_id = fields.Many2one('building.price.calculation','Étude des prix')
    price_calculation_line_id = fields.Many2one('building.price.calculation.line', 'Line')
    price_number = fields.Char('N° de prix', required=False)
    product_line_ids = fields.One2many('building.price.product.line', 'building_price_detail_id', 'Produits')
    resource_material_ids = fields.One2many('building.price.resource.material', 'building_price_detail_id', 'Matériaux')
    expendable_ids = fields.One2many('building.price.expendable', 'building_price_detail_id', 'Consommables')
    resource_human_ids = fields.One2many('building.price.resource.human', 'building_price_detail_id', 'Mains d\'oeuvre')
    amount_products = fields.Float(string='Déboursé Matériaux',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_meterials = fields.Float(string='Déboursé Matériels',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_expendables = fields.Float(string='Déboursé Consommables',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_humans = fields.Float(string='Déboursé MO',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_total = fields.Float(string='Déboursé Total',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    perc_construction_costs = fields.Float('% Frais de Affaire')
    amount_production_cost = fields.Float(string='Coût de Production',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    perc_special_expenses = fields.Float('% Frais Spéciaux')
    amount_direct_cost = fields.Float(string='Coût Direct',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    perc_general_costs = fields.Float('% Frais Généraux')
    amount_standard_price = fields.Float(string='Coût de Revient',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    margin_benefit = fields.Float('% Bénifice et Aléas', digits=(16, 3))
    sale_price = fields.Float(string='Prix de Vente',store=True, readonly=True, compute='_compute_amount', track_visibility='always')

    @api.depends('product_line_ids','resource_material_ids','expendable_ids','resource_human_ids','perc_construction_costs','perc_special_expenses','perc_general_costs','margin_benefit')
    def _compute_amount(self):
        self.amount_products = 0
        self.amount_meterials = 0
        self.amount_expendables = 0
        self.amount_humans = 0
        if self.product_line_ids :
            for product in self.product_line_ids :
                self.amount_products += product.quantity*product.price_unit
        if self.resource_material_ids :
            for material in self.resource_material_ids :
                self.amount_meterials += material.quantity*material.price_unit
        if self.expendable_ids:
            for expendable in self.expendable_ids :
                self.amount_expendables += expendable.quantity*expendable.price_unit
        if self.resource_human_ids :
            for human in self.resource_human_ids :
                self.amount_humans += human.quantity*human.price_unit
        self.amount_total = self.amount_products+self.amount_meterials+self.amount_expendables+self.amount_humans
        amount_production_cost = (self.amount_total*self.perc_construction_costs)/100
        self.amount_production_cost = self.amount_total+amount_production_cost
        amount_direct_cost = (self.amount_total * self.perc_special_expenses) / 100
        self.amount_direct_cost = amount_direct_cost+self.amount_production_cost
        amount_standard_price = (self.amount_total * self.perc_general_costs) / 100
        self.amount_standard_price = amount_standard_price+self.amount_direct_cost
        self.sale_price = (100+self.margin_benefit)*(self.amount_standard_price/100)

    def write(self, values):
        res = super(building_price_details, self).write(values)
        self.price_calculation_line_id.write({'calculated_sales_price':self.sale_price,'actual_selling_price':self.sale_price})
        return res

    @api.onchange('price_calculation_line_id')
    def _onchange_price_calculation_line_id(self):
        if self.price_calculation_line_id:
            self.price_number = self.price_calculation_line_id.price_number

class building_price_product_line(models.Model):

    _name = "building.price.product.line"
    _description = "Composants"

    name = fields.Char('Nom', size=1024, readonly=False)
    product_id = fields.Many2one('product.product', 'Produit', domain=[('type', '=', 'product')], required=False)
    product_uom = fields.Many2one('uom.uom', 'Unité de mésure ', required=False, readonly=False)
    building_price_detail_id = fields.Many2one('building.price.details', 'Price Details')
    margin_benefit = fields.Float('Marge', digits=(16, 3))
    quantity = fields.Float(string='Quantité', required=True,default=0)
    price_unit = fields.Float('Prix Unitaire')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            max_price = self.product_id.standard_price
            self._cr.execute("select max(invl.price_unit) from account_move inv,account_move_line invl where invl.product_id=%s and inv.move_type='%s' and inv.id=invl.move_id"%(self.product_id.id,'in_invoice'))
            result = self._cr.fetchone()
            if result[0] != None :
                max_price = result[0]
            self.name = self.product_id.name
            self.product_uom = self.product_id.uom_id.id
            self.price_unit = max_price


class building_price_resource_material(models.Model):
    _name = "building.price.resource.material"
    _description = "Ressources Matériels"

    name = fields.Char('Désignation', readonly=False)
    resource_categ_id = fields.Many2one('resource.category', 'Catégorie Matériel', required=False)
    resource_id = fields.Many2one('building.resource', 'Matériel', domain= [('type_resource', '=', 'material')], required=False)
    product_uom = fields.Many2one('uom.uom', 'Unité de mésure ', required=False, readonly=False)
    building_price_detail_id = fields.Many2one('building.price.details', 'Price Details')
    quantity = fields.Float(string='Quantité', required=True,default=0)
    price_unit = fields.Float('Prix Unitaire')

    @api.onchange('resource_categ_id')
    def onchange_resource_categ_id(self):
        if self.resource_categ_id:
            self.name = self.resource_categ_id.name
            self.product_uom = self.resource_categ_id.default_unit.id
            if self.resource_categ_id.resource_ids :
                return {'domain': {'resource_id': [('id', 'in', self.resource_categ_id.resource_ids.ids)]}}
            else :
                return {'domain': {'resource_id': [('id', 'in', [])]}}

    @api.onchange('resource_id')
    def onchange_resource_id(self):
        if self.resource_id:
            self.name = self.resource_id.name
            self.product_uom = self.resource_id.cost_unit.id
            self.price_unit = self.resource_id.schedule_cost


class building_price_expendable(models.Model):
    _name = "building.price.expendable"
    _description = "Composants"

    name = fields.Char('Nom', size=1024, readonly=False)
    product_id = fields.Many2one('product.product', 'Produit', domain=[('type', '=', 'consu')], required=False)
    product_uom = fields.Many2one('uom.uom', 'Unité de mésure ', required=False, readonly=False)
    building_price_detail_id = fields.Many2one('building.price.details', 'Price Details')
    margin_benefit = fields.Float('Marge', digits=(16, 3))
    quantity = fields.Float(string='Quantité', required=True,default=0)
    price_unit = fields.Float('Prix Unitaire')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            max_price = self.product_id.standard_price
            self._cr.execute("select max(invl.price_unit) from account_move inv,account_move_line invl where invl.product_id=%s and inv.move_type='%s' and inv.id=invl.move_id" % (self.product_id.id, 'in_invoice'))
            result = self._cr.fetchone()
            if result[0] != None:
                max_price = result[0]
            self.name = self.product_id.name
            self.product_uom = self.product_id.uom_id.id
            self.price_unit = max_price

class building_price_resource_human(models.Model):
    _name = "building.price.resource.human"
    _description = "Ressources Humaines"

    name = fields.Char('Désignation', readonly=False)
    profile_id = fields.Many2one('resource.profile', 'Profil', required=False)
    resource_id = fields.Many2one('building.resource', 'Main d\'oeuvre', domain=[('type_resource', '=', 'human')], required=False)
    product_uom = fields.Many2one('uom.uom', 'Unité de mésure ', required=False, readonly=False)
    building_price_detail_id = fields.Many2one('building.price.details', 'Price Details')
    quantity = fields.Float(string='Quantité', required=True,default=0)
    price_unit = fields.Float('Prix Unitaire')

    @api.onchange('profile_id')
    def onchange_profile_id(self):
        if self.profile_id:
            self.name = self.profile_id.name
            self.product_uom = self.profile_id.default_unit.id
            if self.profile_id.resource_ids:
                return {'domain': {'resource_id': [('id', 'in', list([self.profile_id.resource_ids._ids]))]}}
            else:
                return {'domain': {'resource_id': [('id', 'in', list([]))]}}

    @api.onchange('resource_id')
    def onchange_resource_id(self):
        if self.resource_id:
            self.name = self.resource_id.name
            self.product_uom = self.resource_id.cost_unit.id
            self.price_unit = self.resource_id.schedule_cost