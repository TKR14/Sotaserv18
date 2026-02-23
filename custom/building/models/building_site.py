
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
from datetime import datetime, date, time
# from datetime import datetime
from dateutil.relativedelta import relativedelta

MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')


class building_site(models.Model):
    
    _name = 'building.site'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Site"
    _order = "number desc, id desc"

    penalite = fields.Float(string="Pénalité")
    order_ids = fields.One2many("building.order", "site_id", string="Orders")
    nature_service = fields.Char(string="Nature de prestation")
    vat_exempt = fields.Text(string="Exonération TVA")
    amount_billed = fields.Float(string="Montant Facturé (HT)")
    advance_opening_amount  = fields.Float(tracking=True)
    rg_opening_prc = fields.Float(tracking=True)
    all_risk_site_insurance__opening_amount = fields.Float(tracking=True)
    ten_year__opening_amount = fields.Float(tracking=True)
    malus_retention_opening_amount = fields.Float(tracking=True)
    last_attachment_number = fields.Integer(string="Numéro dernier Attachement", tracking=True)
    is_opening_invisible = fields.Boolean(compute="_compute_is_opening_invisible")

    @api.depends('date_start')
    def _compute_is_opening_invisible(self):
        for rec in self:
            if rec.date_start and rec.date_start > datetime(2025, 7, 1).date():
                rec.is_opening_invisible = True
            else:
                rec.is_opening_invisible = False
    
    def get_type_by_product(self):
        dict_pruduct_by_type = {}
        for site in self:
            dict_pruduct_by_type[site.id] = {}
            need_lines = self.env['building.purchase.need.line'].search([('site_id','=', site.id)])
            for line in need_lines:
                dict_pruduct_by_type[site.id][line.product_id.id] = line.type_produit
        return dict_pruduct_by_type

    # def name_search(self,name, args=None, operator='ilike', context=None, limit=100):
    #     sites = self.search(['|',('name', operator, name),('number', operator, name)]+ args, limit=limit)
    #     return sites.name_get()

    def name_get(self):
        result = []
        for site in self:
            result.append((site.id, "%s %s" % ('['+site.number+']', site.name)))
        return result

    def action_open(self):
        if self.state == "created":
            self.number = self.env["ir.sequence"].get("building.site") or "/"
            self._create_warehouse()
        self.state = "open"

    def action_stopping(self):
        self.write({'state':'stopping'})
        return True
    
    def action_provisional_receipt(self):
        orders = self.env['building.order'].search([('site_id','=',self.id),('shipped','=',False)])
        if orders :
            raise Warning(_('Reception provisoire interdite : il y a encore des ouvrables non livrés.'))
        subcontractings = self.env['building.subcontracting'].search([('site_id','=',self.id),('shipped','=',False)])
        if subcontractings :
            raise Warning(_('Reception provisoire interdite : il y a encore des ouvrables non livrés.'))
        self.write({'state':'provisional_receipt'})
        return True

    def action_ultimately_reception(self):
        # invoice_obj = self.env['account.invoice']
        # invoice_line_obj = self.env['account.invoice.line']
        # # caution = self.env['building.caution'].search([('site_id','=',self.id),('type_caution','=','definitif_caution')])
        # inv_values = {
        #     'name': caution.origin_id.customer_order_ref or caution.origin_id.name,
        #     # 'origin': caution.origin_id.name,
        #     'move_type': 'out_invoice',
        #     'reference': False,
        #     'invoice_type':'specific',
        #     'account_id': caution.origin_id.partner_id.property_account_receivable.id,
        #     'partner_id': caution.origin_id.partner_invoice_id.id,
        #     'currency_id': caution.origin_id.currency_id.id,
        #     'comment': 'Facture caution définitif',
        #     'fiscal_position_id': caution.origin_id.partner_id.property_account_position.id,
        #     'invoice_caution':True,
        #     'site_id':self.id,
        #     'order_id':caution.origin_id.id,
        # }

        # invoice_id = invoice_obj.create(inv_values)
        # # caution.write({'invoice_id':invoice_id.id,'state': 'caution_diposed'})
        # account_caution_id = self.env['account.account'].search([('code', '=', 248640)])

        # inv_line_values = {
        #     'invoice_id':invoice_id.id,
        #     'name': 'Facture caution définitif',
        #     # 'origin': caution.origin_id.name,
        #     'account_id': account_caution_id.id,
        #     'price_unit': caution.amount_caution,
        #     'quantity': 1.0,
        #     'discount': False,
        #     'product_uom_id': False,
        #     'product_id': False,
        #     'tax_ids': [(6, 0, [caution.tax_id.id])],
        # }
        # invoice_line_obj.create(inv_line_values)
        self.write({'state': 'ultimately_reception'})
        return True

    def action_closing(self):
        self.write({'state':'closing'})
        return True

    @api.onchange('date_start', 'duration')
    def _get_date_end(self):
        if self.date_start :
            # start = datetime.strptime(self.date_start, '%Y-%m-%d')
            end = self.date_start + relativedelta(days=self.duration)
            end = end.strftime("%Y-%m-%d")
            self.date_end = end
            
    @api.depends('date_start')
    def _compute_count(self):
        attachments = 0
        orders = 0
        analytics = 0
        if self.id:
            orders = self.env['building.order'].search([('site_id', '=', self.id)], count=True)
            attachments = self.env['building.attachment'].search([('site_id', '=', self.id)], count=True)
            # analytics = self.env['account.analytic.account'].search([('site_id', '=', self.id)], count=True)
        self.attachment_count = attachments
        self.order_count = orders
        # self.analytic_count = analytics


    # def _compute_amount(self):
    #     spent_analytic_lines = self.env['account.analytic.line'].search([('site_id', '=', self.id), ('type_analytic_line', 'in', ('purchase', 'subcontracting', 'workforce', 'equipment', 'material', 'load')), ('state', '=','invoiced')])
    #     spent_analytic_lines_timesheet = self.env['account.analytic.line'].search([('site_id', '=', self.id), ('type_analytic_line', '=','timesheet')])
    #     spent_amount = sum((-line.amount for line in spent_analytic_lines if spent_analytic_lines), 0.0) + sum((line.amount for line in spent_analytic_lines_timesheet if spent_analytic_lines_timesheet), 0.0)
    #     invoiced_analytic_lines = self.env['account.analytic.line'].search([('site_id', '=', self.id), ('type_analytic_line', '=','production'), ('state', '=','invoiced')])
    #     invoiced_amount = sum((line.amount for line in invoiced_analytic_lines if invoiced_analytic_lines), 0.0)
    #     cashed_analytic_lines = self.env['account.analytic.line'].search([('site_id', '=', self.id), ('type_analytic_line', '=','production'), ('state', '=','paid')])
    #     cashed_amount = sum((line.amount for line in cashed_analytic_lines if cashed_analytic_lines), 0.0)
    #     quants = self.env['stock.quant'].search([('site_id', '=', self.id), ('location_id', '=', self.location_id.id)])
    #     inventory_value = sum((line.inventory_value for line in quants if quants), 0.0)
    #     self.spent_amount = spent_amount if spent_amount !=0 else 0
    #     self.invoiced_amount = invoiced_amount
    #     self.cashed_amount = cashed_amount
    #     self.inventory_value = inventory_value
    #     self.difference_amount_invoiced_spent = self.invoiced_amount - self.spent_amount
    #     self.difference_amount_cashed_invoiced = self.cashed_amount - self.invoiced_amount
    #     self.margin_amount = self.invoiced_amount - self.spent_amount
    #     self.perc_margin_amount = self.margin_amount/self.invoiced_amount if self.invoiced_amount !=0 else 0

    def _compute_amount(self):
        for business in self:
            site_installation_amount = 0
            rh_supervisor_amount = 0
            material_amount = 0
            service_provision_amount = 0
            conso_amount = 0
            equipment_amount = 0
            mini_equipment_amount = 0
            diesel_amount = 0
            rh_executor_amount = 0
            indirect_load_amount = 0
            invoiced_amount = 0
            subcontracting_amount = 0
            excuted_amount = 0
            rental_equipment_amount = 0
            order_amount = 0


            # execs = self.env['building.executed'].search([('site_id', '=', business.id), ('state', 'in', ('open', 'closing'))])
            # purchases = self.env['purchase.order'].search([('site_id', '=', business.id), ('state', 'in', ('purchase', 'done'))])
            # picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')])
            # internal_pickings = self.env['stock.picking'].search([('site_id', '=', business.id), ('picking_type_id', 'in', picking_type.ids), ('state', '=', 'done')])
            # # moves = self.env['stock.move'].search([('picking_id', 'in', internal_pickings.ids), ('move_type', 'in', 'to_site')])
            # attachments = self.env['building.attachment'].search([('site_id', '=', business.id), ('state', '=', 'done')])

            # pickings = self.env['stock.picking'].search([('site_id', '=', business.id), ('state', '=', 'done'), ('location_dest_id', '=', business.location_id.id), ('id', 'not in', internal_pickings.ids)])
            # pickings_diesel = self.env['stock.picking'].search([('site_id', '=', business.id), ('state', '=', 'done'), ('location_dest_id', '=', business.location_diesel_id.id)])
            # prov_ser_invoices = self.env['account.move'].search([('site_id', '=', business.id), ('state', '=', 'posted'), ('move_type', '=', 'in_invoice'), ('invoice_attachment', '=', False), ('invoice_diesel', '=', False)])

            # service_provision_amount = sum(inv.amount_untaxed for inv in prov_ser_invoices)

            orders = self.env['building.order'].search([('site_id', '=', business.id)])
            order_amount = sum(order.amount_untaxed for order in orders)

            # for exc in execs:
            #     site_installation_amount += exc.total_amount_site_install
            #     rh_supervisor_amount += exc.total_amount_ressource
            #     equipment_amount += exc.total_amount_equipment
            #     mini_equipment_amount += exc.total_amount_mini_equipment
            #     rh_executor_amount += exc.total_amount_executor_ressource
            #     # indirect_load_amount += exc.amount_indirect_load
            #     excuted_amount += exc.executed_amount_business
            #     rental_equipment_amount += exc.total_amount_rental_equipment

            # dict_type_by_product = self.get_type_by_product()

            # if pickings:
            #     for pick in pickings:
            #         for mv in pick.move_ids_without_package:
            #             type_product = dict_type_by_product[business.id][mv.product_id.id]
                        
            #             if type_product == 'material':
            #                 material_amount += mv.price_unit*mv.quantity_done
            #             if type_product == 'conso':
            #                 conso_amount += mv.price_unit*mv.quantity_done

            #             #self._get_product_last_price(executed.site_id.id, mv.product_id.id) # a devlopper une fct qu prend en chargela MAJ du prix PMP
            #             # if mv.product_id.type == 'consu':
            #             #     conso_amount += mv.price_unit*mv.quantity_done
            #             # if mv.product_id.type == 'product':
            #             #     material_amount += mv.price_unit*mv.quantity_done

            # if pickings_diesel:
            #     for pick in pickings_diesel:
            #         for mv in pick.move_ids_without_package:
            #             diesel_amount += mv.product_id.product_tmpl_id.standard_price*mv.quantity_done

            # # for po in purchases:
            # #     if po.purchase_type == 'material':
            # #         material_amount += po.amount_untaxed
            # #     if po.purchase_type == 'service':
            # #         service_provision_amount += po.amount_untaxed
            # #     if po.purchase_type == 'conso':
            # #         conso_amount += po.amount_untaxed
            # # for move in moves:
            # #     if move.mvt_type == 'material':
            # #         material_amount += move.price_unit*move.product_qty
            # #     if po.mvt_type == 'diesel':
            # #         diesel_amount += move.price_unit*move.product_qty
            # #     if po.purchase_type == 'conso':
            # #         conso_amount += move.price_unit*move.product_qty

            # for attach in attachments:
            #     if attach.type_attachment == 'sale':
            #         invoiced_amount += attach.amount_current_untaxed
            #     if attach.type_attachment == 'purchase':
            #         subcontracting_amount += attach.amount_current_untaxed

            business.site_installation_amount = site_installation_amount
            business.rh_supervisor_amount = rh_supervisor_amount
            business.material_amount = material_amount
            business.service_provision_amount = service_provision_amount
            business.conso_amount = conso_amount
            business.equipment_amount = equipment_amount
            business.rental_equipment_amount = rental_equipment_amount
            business.mini_equipment_amount = mini_equipment_amount
            business.diesel_amount = diesel_amount
            business.rh_executor_amount = rh_executor_amount
            business.indirect_load_amount = indirect_load_amount
            business.excuted_amount = excuted_amount
            # business.invoiced_amount = invoiced_amount
            business.diff_excuted_invoiced_amount = excuted_amount - invoiced_amount
            business.subcontracting_amount = subcontracting_amount
            business.cost_amount = site_installation_amount+rh_supervisor_amount+material_amount+service_provision_amount+conso_amount+equipment_amount+mini_equipment_amount+diesel_amount+rh_executor_amount+indirect_load_amount+subcontracting_amount
            business.margin_amount = invoiced_amount - business.cost_amount
            business.dlm_amount = site_installation_amount + equipment_amount + mini_equipment_amount
            business.rh_amount = rh_supervisor_amount + rh_executor_amount
            business.other_amount = service_provision_amount + subcontracting_amount
            business.expected_revenue = order_amount
            business.total_dlm_amount = business.dlm_amount + rental_equipment_amount

            # Vendu:
            sold = 0

            sold_search = self.env['building.order'].search([('site_id', '=', business.id)])

            for s in sold_search:
                sold += s.amount_total

            business.sold_amount = sold

            # Facture Client:
            cashed = 0 
            invoiced = 0
            stored = 0

            facs_cl_search = self.env['account.move'].search([('site_id', '=', business.id), ('state', '=', 'posted'), ('move_type', 'in', ['out_invoice', 'out_refund'])])
            attchs_search = self.env['building.attachment'].search([('site_id', '=', business.id), ('type_attachment','=','sale'), ('state', '!=', 'done')])

            for f in facs_cl_search:
                invoiced += f.amount_untaxed
                if f.payment_state == 'paid':
                    cashed += f.amount_untaxed
                elif f.payment_state == 'partial':
                    cashed += f.amount_untaxed - f.amount_residual
                # elif f.payment_state == 'not_paid':
            for a in attchs_search:
                stored += a.amount_current_untaxed
                
            business.cashed_amount = cashed
            business.invoiced_amount = invoiced
            business.remains_covered_amount = business.invoiced_amount - business.cashed_amount
            business.stored_amount = stored
            business.total_ca = business.invoiced_amount + business.stored_amount

            if business.sold_amount != 0:
                business.total_ca_prc = (business.total_ca / business.sold_amount) * 100
            else:
                business.total_ca_prc = 0

            # Budget
            budget = 0

            needs_search = self.env['building.purchase.need'].search([('site_id','=', business.id)])

            for need in needs_search:
                budget += need.total_amount

            business.budget_amount = budget
            
    sold_amount = fields.Float(string='Vendu', readonly=False, compute='_compute_amount')
    invoiced_amount = fields.Float(string='Facturé', readonly=False, compute='_compute_amount')
    cashed_amount = fields.Float(string='Encaissé', readonly=False, compute='_compute_amount')
    remains_covered_amount = fields.Float(string='Reste à recouvrir', readonly=False, compute='_compute_amount')
    stored_amount = fields.Float(string='Stocké', readonly=False, compute='_compute_amount')
    total_ca = fields.Float(string='Total Réalisé', readonly=False, compute='_compute_amount')
    total_ca_prc = fields.Float(string='% Réalisé', readonly=False, compute='_compute_amount')
    budget_amount = fields.Float(string='Budget', readonly=False, compute='_compute_amount')

    name = fields.Char('Nom de l\'Affaire',required=True)
    number = fields.Char('Numéro de l\'Affaire',required=True,default=lambda self:'/')
    code = fields.Char('Code')
    opp_id = fields.Many2one('crm.lead', 'Marché')
    project_manager_id = fields.Many2one('hr.employee', 'Chef de Projet')
    site_manager_id = fields.Many2one('hr.employee','Chef de l\'Affaire')
    partner_id = fields.Many2one('res.partner', 'Client', domain=[('customer_rank', '>', 0)], required=False)
    deposit_number = fields.Float('Restitution d\'accompte')
    guaranty_number = fields.Float('Rétention de garantie')
    assurance_number = fields.Float('Assurance')
    state  = fields.Selection([('created', 'Créé'), ('open','Ouvert'), ('stopping','En arrêt'), ('provisional_receipt','En réception provisoire'), ('ultimately_reception','En réception définitive'), ('closing','Cloturé')], string="status", default='created')
    location_id = fields.Many2one("stock.location", string="Stock", domain=[('usage','=','internal')])
    location_diesel_id = fields.Many2one("stock.location", string="Stock Gasoil", domain=[('usage','=','internal')])
    date_start = fields.Date(string='Date Début', readonly=False,index=True, copy=False)
    date_end = fields.Date(string='Date Fin prévisionel',store=True, track_visibility='always')
    stopping_date = fields.Date(string='Date dernier arrêt',required=False,readonly=False,index=True, copy=False,default=lambda *a: time.strftime('%Y-%m-%d'))
    provisional_receipt_date = fields.Date(string='Date de réception provisoire', required=False, readonly=False, index=True, copy=False, default=lambda *a: time.strftime('%Y-%m-%d'))
    ultimately_reception_date = fields.Date(string='Date de reception définitif', required=False, readonly=False, index=True, copy=False, default=lambda *a: time.strftime('%Y-%m-%d'))
    duration = fields.Float('Durée (en jours)')
    description = fields.Text('Description de l\'Affaire')
    user_id = fields.Many2one('res.users', string='Créer Par', track_visibility='onchange', readonly=True, default=lambda self: self.env.user)
    create_date = fields.Date(string='Date de Création', readonly=False, index=True, copy=False, default=fields.Date.today)
    type_op  = fields.Selection([('sale','Affaire Client'), ('purchase','Affaire Prestatire')], string="Type de l\'Affaire", default='sale')
    analytical_accounts_created = fields.Boolean('Comptes analytiques crées ?', default=False)
    with_advance = fields.Boolean('Avec Acompte ?', default=False)
    advance_invoiced = fields.Boolean('Acompte payé ?', default=False)
    last_attachment = fields.Boolean('Dern. Attachement ?',default=False)
    attachment_count = fields.Integer(string='Attachements', readonly=False, compute='_compute_count')
    order_count = fields.Integer(string='DQE', readonly=False, compute='_compute_count')
    # analytic_count = fields.Integer(string='Comptes analytiques', readonly=False, compute='_compute_count')
    # spent_amount = fields.Float(string='Montant Total Déboursé', readonly=False, compute='_compute_amount')
    excuted_amount = fields.Float(string='CA Réalisé', readonly=False, compute='_compute_amount')
    # invoiced_amount = fields.Float(string='CA Facturé', readonly=False, compute='_compute_amount')
    diff_excuted_invoiced_amount = fields.Float(string='Écart CA Réalisé et Facturé', readonly=False, compute='_compute_amount')
    # cashed_amount = fields.Float(string='Montant Encaissé', readonly=False, compute='_compute_amount')
    inventory_value = fields.Float(string='Stock', readonly=False, compute='_compute_amount')
    # difference_amount_invoiced_spent = fields.Float(string='Différence entre le facturé et le déboursé', readonly=False, compute='_compute_amount')
    # difference_amount_cashed_invoiced = fields.Float(string='Différence entre l\'encaissé et le facturé', readonly=False, compute='_compute_amount')
    margin_amount = fields.Float(string='Résultat', readonly=False, compute='_compute_amount')
    # perc_margin_amount = fields.Float(string='Pourcentage de la Marge', readonly=False, compute='_compute_amount')
    type_marche  = fields.Selection([('forfait','Au Forfait'), ('metre','Au métré')], string="Type de marché", default='metre')

    site_installation_amount = fields.Float(string='Installation de chantier', readonly=False, compute='_compute_amount')
    rh_supervisor_amount = fields.Float(string='Encadrement', readonly=False, compute='_compute_amount')
    material_amount = fields.Float(string='Fournitures', readonly=False, compute='_compute_amount')
    service_provision_amount = fields.Float(string='Prestation de service', readonly=False, compute='_compute_amount')
    conso_amount = fields.Float(string='Consommables', readonly=False, compute='_compute_amount')
    equipment_amount = fields.Float(string='Matériels', readonly=False, compute='_compute_amount')
    mini_equipment_amount = fields.Float(string='Petit Matériels', readonly=False, compute='_compute_amount')
    diesel_amount = fields.Float(string='Gasoil', readonly=False, compute='_compute_amount')
    rh_executor_amount = fields.Float(string='Main-d’œuvre', readonly=False, compute='_compute_amount')
    indirect_load_amount = fields.Float(string='Charges Indirects', readonly=False, compute='_compute_amount')
    subcontracting_amount = fields.Float(string='Sous-traitance', readonly=False, compute='_compute_amount')
    cost_amount = fields.Float(string='Coût de Revient', readonly=False, compute='_compute_amount')
    expected_revenue = fields.Float(string='Montant Marché (HT)', compute='_compute_amount')
    dlm_amount = fields.Float(string='Location', readonly=False, compute='_compute_amount')
    rh_amount = fields.Float(string='MO', readonly=False, compute='_compute_amount')
    other_amount = fields.Float(string='Pres. Ser & Trav.', readonly=False, compute='_compute_amount')
    wsso_date = fields.Date(string='Date Ordre de service', readonly=False, states={'open': [('readonly', True)],'closing': [('readonly', True)]},index=True, copy=False)
    final_deposit_date = fields.Date(string='Date Caution déf', readonly=False, states={'open': [('readonly', True)],'closing': [('readonly', True)]},index=True, copy=False)
    guarantee_date = fields.Date(string='Date Ret garantie', readonly=False, states={'open': [('readonly', True)],'closing': [('readonly', True)]},index=True, copy=False)
    categ_marche_id = fields.Many2one("building.categ.site", string="Categ Projet")
    rental_equipment_amount = fields.Float(string='Matériels Externe', readonly=False, compute='_compute_amount')
    total_dlm_amount = fields.Float(string='Location', readonly=False, compute='_compute_amount')
    is_with_purchase_need = fields.Boolean('Avec Liste des besoins ?', default=True)
    caution_ids = fields.One2many('account.caution', 'site_id', string='Cautions', copy=True)
    prc_cd = fields.Float('% CD')
    type_gr  = fields.Selection([('none','Pas de retenue de garantie'),('g_gr','Pas de retenue de garantie'),('att_gr','Retenue de garantie par décompte'),('inv_gr','Retenue de garantie sur facturation')], string="status",default='none')
    # prc_gr = fields.Float('% RG')


    prc_gr = fields.Float('Retenue de garantie (%)', tracking=True)
    prc_advance_deduction = fields.Float("Montant d'avance (HT)", tracking=True)
    prc_ten_year = fields.Float('% Retenue Assurance décennale', tracking=True)

    sum_prc_gr = fields.Float("Cumul Retenue de Garantie", compute="_compute_sum_prc")
    sum_prc_advance_deduction = fields.Float("Cumul Déduction Avance", compute="_compute_sum_prc")
    sum_prc_ten_year = fields.Float("Cumul Retenue Assurance Décennale", compute="_compute_sum_prc")

    def _compute_sum_prc(self, exclude_me=None):
        for site in self:
            out_invoices = self.env["account.move"].search([("site_id", "=", site.id), ("move_type", "=", "out_invoice"), ("id", "!=", exclude_me)])
            site.sum_prc_gr = sum(out_invoices.mapped("prc_gr"))
            site.sum_prc_advance_deduction = sum(out_invoices.mapped("prc_advance_deduction"))
            site.sum_prc_ten_year = sum(out_invoices.mapped("prc_ten_year"))

    prc_all_risk_site_insurance = fields.Float('Déduction TRC (HT)', tracking=True)
    prc_prorata_account = fields.Float('% Déduction Compte Prorata', tracking=True)
    prc_finish = fields.Float('% Déduction Autres Retenue', tracking=True)

    opening_visible = fields.Boolean('Ouverture visible?', compute="_compute_opening_visible_and_others")
    has_building_order = fields.Boolean('Avec DQE?', compute="_compute_opening_visible_and_others")
    has_purchase_need = fields.Boolean('Avec Liste des besoins?', compute="_compute_opening_visible_and_others")

    is_invisible_advance = fields.Boolean(default=False, compute="_compute_is_invisible_advance")
    tax_id = fields.Many2one("account.tax", string="Taxe sur le Client", compute="_compute_tax_id")

    @api.constrains("prc_advance_deduction")
    def _check_prc_advance_deduction(self):
        for rec in self:
            if rec.prc_advance_deduction > rec.expected_revenue:
                raise ValidationError(
                    "Le montant de l'avance (HT) ne peut excéder 100 % du montant total de la BDP (HT)."
                )

    @api.depends('tax_id')
    def _compute_tax_id(self):
        for rec in self:
            order_id = rec.env['building.order'].search([('site_id', '=', rec.id)], limit=1)
            if order_id:
                rec.tax_id = order_id.tax_id
            else:
                rec.tax_id = False

    @api.constrains('prc_gr')
    def _check_prc_gr(self):
        for record in self:
            if record.prc_gr < 0 or record.prc_gr > 100:
                raise ValidationError("La valeur de 'Retenue de Garantie' doit être comprise entre 0 et 100.")
            
    def _compute_is_invisible_advance(self):
        for record in self:
            advance_invoice = self.env['account.move'].search([
                ('site_id', '=', record.id),
                ('move_type', '=', 'out_invoice'),
                ('move_type_code', '=', 'inv_advance')
            ], limit=1)
            record.is_invisible_advance = bool(advance_invoice)

    def action_create_advance_invoice(self):
        if self.prc_advance_deduction > 0:
            move_type = self.env['account.move.type'].search([('code', '=', 'inv_advance')], limit=1)
            invoice_vals = {
                'move_type': 'out_invoice',
                'move_type_id': move_type.id if move_type else False,
                'partner_id': self.partner_id.id,
                'journal_id': 1,
                'site_id': self.id,
                'ref': f"Avance, {self.number}",
                'invoice_date': datetime.today(),
                'invoice_origin': self.name,
                'date': datetime.today(),
                'invoice_line_ids': [
                    (0, 0, {
                        'account_id': self.env['account.account'].search([('code', '=', '4191000')], limit=1).id,
                        'price_unit': self.prc_advance_deduction,
                        'quantity': 1,
                        'exclude_from_invoice_tab': False,
                        'tax_ids': self.tax_id,
                    }),
                ],
            }
            self.env['account.move'].create(invoice_vals)

    @api.constrains('code')
    def _check_code_length(self):
        for record in self:
            if len(record.code) > 30:
                raise ValidationError("Le code ne doit pas dépasser 30 caractères.")
            
    @api.constrains('code')
    def _check_code_unique(self):
        for record in self:
            existing_records = self.search([('code', '=', record.code), ('id', '!=', record.id)])
            if existing_records:
                raise ValidationError("Ce code est déjà utilisé. Veuillez choisir un code unique.")
            
    def _compute_opening_visible_and_others(self):
        for rec in self:
            rec.opening_visible = False
            rec.has_building_order = False
            rec.has_purchase_need = False

            building_order = self.env['building.order'].search([('site_id', '=', rec.id)])
            building_purchase_need = self.env['building.purchase.need'].search([('site_id', '=', rec.id)])

            if building_order:
                rec.has_building_order = True

            if building_purchase_need:
                rec.has_purchase_need = True

            if self.state == 'created':
                if building_order and building_purchase_need:
                    rec.opening_visible = True


    def order_tree_view(self):
        orders = self.env['building.order'].search([('site_id', '=', self.id)])
        order_ids = []
        for order in orders :
            order_ids.append(order.id)
        domain = [('id', 'in', order_ids)]
        return {
            'name': _('BP'),
            'domain': domain,
            'res_model': 'building.order',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form,kanban',
            'limit': 80
        }
    
    def attachment_tree_view(self):
        attachments = self.env['building.attachment'].search([('site_id', '=', self.id)])
        attachment_ids = []
        for attachment in attachments :
            attachment_ids.append(attachment.id)
        domain = [('id', 'in', attachment_ids)]
        return {
            'name': _('Attachements'),
            'domain': domain,
            'res_model': 'building.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'limit': 80
        }

    def details_site_report(self):
        self.env['building.site.report'].search([('site_id', '=', self.id)]).unlink()
        record_ca_cashed = {
            'site_id' : self.id,
            'r0': 'cashed',
            'amount' : self.cashed_amount,
            'prc_amount_per_invoiced' : (self.cashed_amount/self.invoiced_amount)*100 if self.invoiced_amount > 0 else 0,
            'prc_seuil':100
        }
        self.env['building.site.report'].create(record_ca_cashed)
        record_ca_excuted= {
            'site_id' : self.id,
            'r0': 'executed',
            'amount' : self.excuted_amount,
            'prc_amount_per_invoiced' : (self.excuted_amount/self.invoiced_amount)*100 if self.invoiced_amount > 0 else 0,
            'prc_seuil':100
        }
        self.env['building.site.report'].create(record_ca_excuted)
        
        record_ca_invoiced = {
            'site_id' : self.id,
            'r0': 'invoiced',
            'amount' : self.invoiced_amount,
            'prc_amount_per_invoiced' : 100 if self.invoiced_amount > 0 else 0,
            'prc_seuil':100
        }
        self.env['building.site.report'].create(record_ca_invoiced)

        # record_ca_inventory = {
        #     'site_id' : self.id,
        #     'r0': 'inventory',
        #     'amount' : self.inventory_value,
        #     'prc_amount_per_invoiced' : (self.inventory_value/self.invoiced_amount)*100 if self.invoiced_amount > 0 else 0
        # }
        # self.env['building.site.report'].create(record_ca_inventory)
        limit_control = self.env['building.limit.control.site'].search([('categ_site_id', '=', self.categ_marche_id.id), ('rubrique', '=', 'product')])
        prc_limit_control = 0
        if limit_control:
            prc_limit_control = limit_control.prc_limit

        record_ca_product = {
            'site_id' : self.id,
            'r0': 'product',
            'amount' : self.material_amount,
            'prc_amount_per_invoiced' : (self.material_amount/self.invoiced_amount)*100 if self.invoiced_amount > 0 else 0,
            'prc_seuil':prc_limit_control
        }
        self.env['building.site.report'].create(record_ca_product)

        limit_control = self.env['building.limit.control.site'].search([('categ_site_id', '=', self.categ_marche_id.id), ('rubrique', '=', 'product')])        
        prc_limit_control = 0
        if limit_control:
            prc_limit_control = limit_control.prc_limit

        record_ca_consu = {
            'site_id' : self.id,
            'r0': 'consu',
            'amount' : self.conso_amount,
            'prc_amount_per_invoiced' : (self.conso_amount/self.invoiced_amount)*100 if self.invoiced_amount > 0 else 0,
            'prc_seuil':prc_limit_control
        }
        self.env['building.site.report'].create(record_ca_consu)

        limit_control = self.env['building.limit.control.site'].search([('categ_site_id', '=', self.categ_marche_id.id), ('rubrique', '=', 'product')])        
        prc_limit_control = 0
        if limit_control:
            prc_limit_control = limit_control.prc_limit


        record_ca_diesel= {
            'site_id' : self.id,
            'r0': 'diesel',
            'amount' : self.diesel_amount,
            'prc_amount_per_invoiced' : (self.diesel_amount/self.invoiced_amount)*100 if self.invoiced_amount > 0 else 0,
            'prc_seuil':prc_limit_control
        }
        self.env['building.site.report'].create(record_ca_diesel)

        limit_control = self.env['building.limit.control.site'].search([('categ_site_id', '=', self.categ_marche_id.id), ('rubrique', '=', 'product')])        
        prc_limit_control = 0
        if limit_control:
            prc_limit_control = limit_control.prc_limit

        record_ca_pro_ser = {
            'site_id' : self.id,
            'r0': 'prov_serv',
            'amount' : self.service_provision_amount,
            'prc_amount_per_invoiced' : (self.service_provision_amount/self.invoiced_amount)*100 if self.invoiced_amount > 0 else 0,
            'prc_seuil':prc_limit_control
        }
        self.env['building.site.report'].create(record_ca_pro_ser)

        record_ca_subcontracting = {
            'site_id' : self.id,
            'r0': 'subcontracting',
            'amount' : self.subcontracting_amount,
            'prc_amount_per_invoiced' : (self.subcontracting_amount/self.invoiced_amount)*100 if self.invoiced_amount > 0 else 0,
            'prc_seuil':100
        }
        self.env['building.site.report'].create(record_ca_subcontracting)

        record_ca_dlm = {
            'site_id' : self.id,
            'r0': 'dlm',
            'amount' : self.dlm_amount,
            'prc_amount_per_invoiced' : (self.dlm_amount/self.invoiced_amount)*100 if self.invoiced_amount > 0 else 0,
            'prc_seuil':100
        }
        self.env['building.site.report'].create(record_ca_dlm)

        record_ca_rental_dlm = {
            'site_id' : self.id,
            'r0': 'dlm_rental',
            'amount' : self.rental_equipment_amount,
            'prc_amount_per_invoiced' : (self.rental_equipment_amount/self.invoiced_amount)*100 if self.invoiced_amount > 0 else 0,
            'prc_seuil':100
        }
        self.env['building.site.report'].create(record_ca_rental_dlm)

        limit_control = self.env['building.limit.control.site'].search([('categ_site_id', '=', self.categ_marche_id.id), ('rubrique', '=', 'product')])        
        prc_limit_control = 0
        if limit_control:
            prc_limit_control = limit_control.prc_limit

        record_ca_rh = {
            'site_id' : self.id,
            'r0': 'rh',
            'amount' : self.rh_amount,
            'prc_amount_per_invoiced' : (self.rh_amount/self.invoiced_amount)*100 if self.invoiced_amount > 0 else 0,
            'prc_seuil':prc_limit_control
        }
        self.env['building.site.report'].create(record_ca_rh)

        site_report = self.env['building.site.report'].search([('site_id', '=', self.id)])
        domain = [('id', 'in', site_report.ids)]
        return {
            'name': _('Details par Rubrique'),
            'domain': domain,
            'res_model': 'building.site.report',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,graph',
        }

    @api.model
    def create(self, values):
        if 'is_with_purchase_need' in values:
            if not values.get('is_with_purchase_need'):
                sequ = self.env['ir.sequence'].get('building.site') or '/'
                values['state'] = 'open'
                values['number'] = sequ
        res = super(building_site, self).create(values)
        return res
    # def analytic_tree_view(self):
    #     if self.id:
    #         analytics = self.env['account.analytic.account'].search([('site_id', '=', self.id)])
    #         analytic_ids = []
    #         for analytic in analytics :
    #             analytic_ids.append(analytic.id)
    #         domain = [('id', 'in', analytic_ids)]
    #         return {
    #             'name': _('Comptes analytiques'),
    #             'domain': domain,
    #             'res_model': 'account.analytic.account',
    #             'type': 'ir.actions.act_window',
    #             'view_id': False,
    #             'view_mode': 'tree,form',
    #              'limit': 80
    #         }
    #     return {}

    @api.onchange("state")
    def onchange_affaire_state(self):
        if self.state == "open":
            po = self.env["building.order"].search([("site_id", "=", self.id)], limit=1)
            po.write({"state": "approved"})

# class building_report(models.Model):

#     _name = 'building.report'
#     _description = "Building Dashboard"

#     def _compute_amount(self):
#         customers_due_invoices = self.env['account.invoice'].search([('state', '=','open'),('type', '=','out_invoice'),('date_due','<=',time.strftime('%Y-%m-%d'))])
#         customers_emitted_invoices = self.env['account.invoice'].search([('state', '=','open'),('type', '=','out_invoice'),('date_due','>',time.strftime('%Y-%m-%d'))])
#         supplier_invoice_to_pay = self.env['account.invoice'].search([('state', '=','open'),('type', '=','in_invoice')])

#         invoiced_due_amount = sum((inv.amount_to_paid for inv in customers_due_invoices if customers_due_invoices), 0.0)
#         invoiced_emitted_amount = sum((inv.amount_to_paid for inv in customers_emitted_invoices if customers_emitted_invoices), 0.0)
#         invoiced_to_pay_amount = sum((inv.amount_to_paid for inv in supplier_invoice_to_pay if supplier_invoice_to_pay), 0.0)
        
#         self.invoice_due_amount = invoiced_due_amount
#         self.invoiced_emitted_amount = invoiced_emitted_amount
#         self.supplier_invoice_to_pay_amount = invoiced_to_pay_amount

#     invoice_due_amount = fields.Integer(string='Factures Échues', readonly=False, compute='_compute_amount')
#     invoice_emitted_amount = fields.Integer(string='Factures Émises', readonly=False, compute='_compute_amount')
#     supplier_invoice_to_pay_amount = fields.Integer(string='Factures Fournisseurs à payer par mois', readonly=False, compute='_compute_amount')
    
    def get_building_purchase_need(self):
        building_purchase_need = self.env['building.purchase.need'].search([('site_id', '=', self.id)])
        if building_purchase_need:
            action_id = self.env.ref('building.building_purchase_need_readonly_action').read()[0]
            action_id['res_id'] = building_purchase_need.id

        return action_id

    def get_building_order(self):
        building_order = self.env['building.order'].search([('site_id', '=', self.id)])
        if building_order:
            action_id = self.env.ref('building.building_order_readonly_action').read()[0]
            action_id['res_id'] = building_order.id

        return action_id

class building_executed(models.Model):
    
    _name = 'building.executed'
    _description = "Execution"
    
    @api.depends('date_start', 'date_end')
    def _compute_day_end_month(self):
        for executed in self:
            if executed.date_start and executed.date_end:
                executed.day_end_month = (executed.date_end-executed.date_start).days
            else:
                executed.day_end_month = 0

    @api.depends('line_ids.amount_total', 'assigned_equipment_cost_ids.total_cost_equipment', 
        'assigned_mini_equipment_cost_ids.total_cost_equipment', 'assigned_equipment_site_install_cost_ids.total_cost_equipment', 
        'assigned_vehicule_cost_ids.total_cost_vehicule', 'assigned_ressource_cost_ids.total_cost_ressource', 
        'assigned_ressource_executor_cost_ids.total_cost_ressource', 'line_forcasted_ids.amount_total' )
    def _compute_amount(self):
        total = 0
        executed_amount = 0
        all_executed = self.env['building.executed'].search([('site_id', '=', self.site_id.id), ('state', '=', 'closing')])
        for executed in self:
            total = sum((line.amount_total for line in executed.line_ids), 0.0)
            forcast_amount_business = sum((line.amount_total for line in executed.line_forcasted_ids), 0.0)
            executed_amount = sum((build_exec.executed_amount_business for build_exec in all_executed), 0.0)
            total_cost_equipment = sum((line.total_cost_equipment for line in executed.assigned_equipment_cost_ids if not line.assignment_id.vehicle_id.is_rental), 0.0)
            total_cost_mini_equipment = sum((line.total_cost_equipment for line in executed.assigned_mini_equipment_cost_ids), 0.0)
            total_cost_site_install = sum((line.total_cost_equipment for line in executed.assigned_equipment_site_install_cost_ids), 0.0)
            total_cost_vehicule = sum((line.total_cost_vehicule for line in executed.assigned_vehicule_cost_ids), 0.0)
            total_cost_ressource = sum((line.total_cost_ressource for line in executed.assigned_ressource_cost_ids), 0.0)
            total_cost_exec_ressource = sum((line.total_cost_ressource for line in executed.assigned_ressource_executor_cost_ids), 0.0)
            total_cost_diesel_equipment = sum((line.diesel_consumption*line.assignment_id.vehicle_id.consumption for line in executed.assigned_equipment_cost_ids), 0.0)
            total_rental_cost_equipment = sum((line.total_cost_equipment for line in executed.assigned_equipment_cost_ids if line.assignment_id.vehicle_id.is_rental), 0.0)
            # total_cost_diesel_mini_equipment = sum((line.diesel_consumption*line.consumption for line in executed.assigned_mini_equipment_cost_ids), 0.0)
            total_cost_diesel_mini_equipment = 0
            executed.forcast_amount_business = forcast_amount_business
            executed.executed_amount_business = total
            executed.cumul_executed_amount_business = executed_amount
            executed.total_amount_equipment = total_cost_equipment
            executed.total_amount_rental_equipment = total_rental_cost_equipment
            executed.total_amount_vehicule = total_cost_vehicule
            executed.total_amount_ressource = total_cost_ressource
            executed.total_amount_site_install = total_cost_site_install
            executed.total_amount_mini_equipment = total_cost_mini_equipment
            executed.total_amount_executor_ressource = total_cost_exec_ressource
            executed.total_amount_diesel_consumption = total_cost_diesel_equipment + total_cost_diesel_mini_equipment
            executed.amount_indirect_load = total*3.78/100

            amount_exploitation_charges =  executed.total_amount_equipment + executed.total_amount_vehicule + executed.total_amount_ressource + executed.total_amount_site_install + executed.total_amount_mini_equipment + executed.total_amount_executor_ressource + executed.total_amount_diesel_consumption + executed.amount_indirect_load + executed.amount_consumables + executed.amount_supply_stock + executed.total_amount_rental_equipment
            executed.amount_result_executed = executed.executed_amount_business - amount_exploitation_charges
            executed.prc_result_executed = (executed.amount_result_executed/amount_exploitation_charges)*100 if amount_exploitation_charges > 0 else 0
            executed.amount_forcast_result = executed.forcast_amount_business - amount_exploitation_charges
            executed.prc_result_forcast = (executed.amount_forcast_result/amount_exploitation_charges)*100 if amount_exploitation_charges > 0 else 0

            need = self.env['building.purchase.need'].search([('site_id', '=', self.site_id.id), ('state', '=', 'approuved')])
            prc_margin_budget = 0
            if need:
                prc_margin_budget = (need.total_amount_margin/need.total_amount)*100
            self.prc_margin_budget = prc_margin_budget


    name = fields.Char('Numéro', required=False)
    opp_id = fields.Many2one('crm.lead', 'Apeel d''offre')
    site_id = fields.Many2one('building.site', 'Affaire')
    order_id = fields.Many2one('building.order', 'BP')
    state  = fields.Selection([('draft', 'Brouillon'), ('open', 'Ouvert'), ('closing', 'Cloturé')], string="status", default='draft')
    forcast_amount_business = fields.Float(string='CA Prévisionnel', readonly=False, store =True, compute='_compute_amount')
    provisional_amount_business = fields.Float(string='CA Prev', readonly=False, store =True, compute='_compute_amount')
    previous_day_amount_business = fields.Float(string='CA (J-1)')
    executed_amount_business = fields.Float(string='CA du mois', readonly=False, store =True, compute='_compute_amount')
    cumul_executed_amount_business = fields.Float(string='CA Cumulé', readonly=False, store =True, compute='_compute_amount')
    total_amount_site_install = fields.Float(string='Installation de chantier', readonly=False, store =True, compute='_compute_amount')
    total_amount_equipment = fields.Float(string='Matériels', readonly=False, store =True, compute='_compute_amount')
    total_amount_rental_equipment = fields.Float(string='Matériels Externe', readonly=False, store =True, compute='_compute_amount')
    total_amount_mini_equipment = fields.Float(string='Petit matériels', readonly=False, store =True, compute='_compute_amount')
    total_amount_vehicule = fields.Float(string='Charges vihécules', readonly=False, store =True, compute='_compute_amount')
    total_amount_ressource = fields.Float(string='Encadrement', readonly=False, store =True, compute='_compute_amount')
    total_amount_executor_ressource = fields.Float(string='Main-d’œuvre', readonly=False, store =True, compute='_compute_amount')
    total_amount_diesel_consumption = fields.Float(string='Gasoil', readonly=False, store =True, compute='_compute_amount')
    amount_indirect_load = fields.Float(string='Charges indirect', readonly=False, store =True, compute='_compute_amount')
    
    amount_consumables = fields.Float(string='Montant consommables')
    amount_supply_stock = fields.Float(string='Montant Fournitures')

    amount_result_executed = fields.Float(string='Résultat de l''exploitation', readonly=False, store =True, compute='_compute_amount')
    prc_result_executed = fields.Float(string='% Résultat de l''exploitation', readonly=False, store =True, compute='_compute_amount')
    amount_forcast_result = fields.Float(string='Résultat de l''exploitation prévisionnel', readonly=False, store =True, compute='_compute_amount')
    prc_result_forcast = fields.Float(string='% Résultat de l''exploitation prévisionnel', readonly=False, store =True, compute='_compute_amount')
    prc_margin_budget = fields.Float(string='% Marge appliqué')


    date_start = fields.Date(string='Date Début')
    date_end = fields.Date(string='Date Fin')
    line_ids = fields.One2many('building.executed.line', 'executed_id', 'Lignes', readonly=False, copy=True)
    # assigned_equipment_ids = fields.One2many('building.executed.equipment', 'executed_id', 'Lignes', readonly=False, copy=True)
    # assigned_ressource_ids = fields.One2many('building.executed.ressource', 'executed_id', 'Lignes', readonly=False, copy=True)

    assigned_equipment_site_install_cost_ids = fields.One2many('building.executed.equipment', 'executed_id', 'Lignes 0', readonly=False, copy=True, domain=[('categ_execution', '=', 'site_installation')])
    assigned_equipment_cost_ids = fields.One2many('building.executed.equipment', 'executed_id', 'Lignes 1', readonly=False, copy=True, domain=[('categ_execution', '=', 'equipment')])
    assigned_mini_equipment_cost_ids = fields.One2many('building.executed.equipment', 'executed_id', 'Lignes 2', readonly=False, copy=True, domain=[('categ_execution', '=', 'mini_equipment')])
    assigned_vehicule_cost_ids = fields.One2many('building.executed.vehicule', 'executed_id', 'Lignes 3', readonly=False, copy=True)
    assigned_ressource_cost_ids = fields.One2many('building.executed.ressource', 'executed_id', 'Lignes 4', readonly=False, copy=True, domain=[('categ_execution', '=', 'supervisor')])
    assigned_ressource_executor_cost_ids = fields.One2many('building.executed.ressource', 'executed_id', 'Lignes 5', readonly=False, copy=True, domain=[('categ_execution', '=', 'executor')])
    line_forcasted_ids = fields.One2many('building.executed.forcasted.line', 'executed_id', 'Lignes forcated', readonly=False, copy=True)
    assigned_diesel_cost_ids = fields.One2many('building.executed.diesel', 'executed_id', 'Lignes diesel', readonly=False, copy=True)

    day_end_month = fields.Integer("Fin du mois", store =True, compute='_compute_day_end_month')

    days_end_of_month = fields.Selection([
        ('28', '28'),
        ('29', '29'),
        ('30', '30'),], default=False)

    def action_open(self):
        sequ = self.env['ir.sequence'].get('building.executed') or '/'
        self.write({'state': 'open', 'name': sequ})
        return True

    def action_closing(self):
        self.write({'state':'closing'})
        return True

    def _get_product_last_price(self, site_id, product_id):
        move = self.env['stock.move'].search([('site_id', '=', site_id), ('product_id', '=', product_id), ('picking_type', '=', 'to_site'), ('state', '=', 'done')], order='id desc', limit=1)
        if move:
            return move.price_unit
        product = self.env['product.product'].search('id', '=', product_id)
        return product.product_tmpl_id.standard_price

    #a mettre dans le cron pour calcul charges conso et fournitures(4 frequences)
    def compute_amount_moves_to_customer(self):
        for executed in self:
            amount_consumables = 0
            amount_supply_stock = 0
            pickings = self.env['stock.picking'].search([('site_id', '=', executed.site_id.id), ('picking_type', '=', 'to_partner'), ('state', '=', 'done')])
            if pickings:
                for pick in pickings:
                    for mv in pick.move_ids_without_package:
                        last_price = self._get_product_last_price(executed.site_id.id, mv.product_id.id)
                        if mv.product_id.type == 'consu':
                            amount_consumables += last_price*mv.quantity_done
                        if mv.product_id.type == 'product':
                            amount_supply_stock += last_price*mv.quantity_done
            executed.amount_consumables = amount_consumables
            executed.amount_supply_stock = amount_supply_stock

    #a mettre dans le cron pour MAJ CA J-1
    def compute_previous_day_amount_business(self):
        for executed in self:
            previous_day_amount_business = 0
            if executed.state == 'open':
                date_day = datetime.datetime.now().date()
                attr_to_get = 'amount'+str(date_day.day-2)
                previous_day_amount_business = sum((getattr(line, attr_to_get) for line in executed.line_ids), 0.0)
            executed.previous_day_amount_business = previous_day_amount_business

    @api.model
    def create(self, vals):
        ouvrages = []
        forcasteds = []
        if 'order_id' in vals:
            order_id = vals['order_id']
            order = self.env['building.order'].browse(order_id)
            for line in order.order_line:
                if not line.display_type:
                    ouvrage_record = {
                        'price_id': line.id,
                        'name': line.price_number,
                        'uom_id': line.product_uom.id,
                        'price_unit': line.price_unit
                    }
                    ouvrages.append((0, 0, ouvrage_record))
                    forcasteds.append((0, 0, ouvrage_record))
        vals['line_ids'] = ouvrages
        vals['line_forcasted_ids'] = ouvrages

        ressources = []
        equipements = []
        vehicules = []
        exec_ressources = []
        mini_equipements = []
        site_install = []
        diesel = []
        if 'site_id' in vals:
            site_id = vals['site_id']
            assignments = self.env['building.assignment.line'].search([('site_id', '=', site_id), ('state', '=', 'open')])
            if assignments:
                for assignment in assignments:
                    assignments_record = {
                        'assignment_id': assignment.id,
                        'name': assignment.code,
                        'uom_id': assignment.uom_id.id,
                        'cost': assignment.cost
                    }
                    if assignment.type_assignment == 'emp' and assignment.categ_assignment == 'supervisor':
                        assignments_record['categ_execution'] = 'supervisor'
                        ressources.append((0, 0, assignments_record))
                    elif assignment.type_assignment == 'emp' and assignment.categ_assignment == 'executor':
                        assignments_record['categ_execution'] = 'executor'
                        exec_ressources.append((0, 0, assignments_record))
                    elif assignment.type_assignment == 'equipment' and assignment.categ_assignment == 'equipment':
                        disel_assignments_record = assignments_record.copy()
                        diesel.append((0, 0, disel_assignments_record))
                        assignments_record['categ_execution'] = 'equipment'
                        assignments_record['consumption_per_day'] = assignment.consumption
                        equipements.append((0, 0, assignments_record))                        
                    elif assignment.type_assignment == 'equipment' and assignment.categ_assignment == 'mini_equipment':
                        assignments_record['categ_execution'] = 'mini_equipment'
                        mini_equipements.append((0, 0, assignments_record))
                    elif assignment.type_assignment == 'equipment' and assignment.categ_assignment == 'site_installation':
                        assignments_record['categ_execution'] = 'site_installation'
                        site_install.append((0, 0, assignments_record))
                    # elif assignment.type_assignment == 'equipment' and assignment.categ_assignment == 'equipment':
                    #     assignments_record['cost'] = assignment.cost
                    #     diesel.append((0, 0, assignments_record))
        vals['assigned_ressource_cost_ids'] = ressources
        vals['assigned_equipment_cost_ids'] = equipements
        vals['assigned_vehicule_cost_ids'] = vehicules
        vals['assigned_equipment_site_install_cost_ids'] = site_install
        vals['assigned_mini_equipment_cost_ids'] = mini_equipements
        vals['assigned_ressource_executor_cost_ids'] = exec_ressources
        vals['assigned_diesel_cost_ids'] = diesel

        return super(building_executed, self).create(vals)


    def write(self, vals):        
        if 'order_id' in vals:
            ouvrages = []
            forcasteds = []
            self.env['building.executed.line'].search([('executed_id', '=', self.id)]).unlink()            
            self.env['building.executed.forcasted.line'].search([('executed_id', '=', self.id)]).unlink()            
            self.env['building.executed.diesel'].search([('executed_id', '=', self.id)]).unlink()
            order_id = vals['order_id']
            order = self.env['building.order'].browse(order_id)
            for line in order.order_line:
                if not line.display_type:
                    ouvrage_record = {
                        'price_id': line.id,
                        'name': line.price_number,
                        'uom_id': line.product_uom.id,
                        'price_unit': line.price_unit
                    }
                    ouvrages.append((0, 0, ouvrage_record))
                    forcasteds.append((0, 0, ouvrage_record))
            vals['line_ids'] = ouvrages
            vals['line_forcasted_ids'] = ouvrages
        
        if 'site_id' in vals:
            ressources = []
            equipements = []
            vehicules = []
            exec_ressources = []
            mini_equipements = []
            site_install = []
            diesel = []

            site_id = vals['site_id']
            self.env['building.executed.equipment'].search([('executed_id', '=', self.id)]).unlink()
            self.env['building.executed.ressource'].search([('executed_id', '=', self.id)]).unlink()
            assignments = self.env['building.assignment.line'].search([('site_id', '=', site_id), ('state', '=', 'open')])
            if assignments:
                for assignment in assignments:
                    assignments_record = {
                        'assignment_id': assignment.id,
                        'name': assignment.code,
                        'uom_id': assignment.uom_id.id,
                        'cost': assignment.cost
                    }
                    if assignment.type_assignment == 'emp' and assignment.categ_assignment == 'supervisor':
                        assignments_record['categ_execution'] = 'supervisor'
                        ressources.append((0, 0, assignments_record))
                    elif assignment.type_assignment == 'emp' and assignment.categ_assignment == 'executor':
                        assignments_record['categ_execution'] = 'executor'
                        exec_ressources.append((0, 0, assignments_record))
                    elif assignment.type_assignment == 'equipment' and assignment.categ_assignment == 'equipment':
                        assignments_record['categ_execution'] = 'equipment'
                        assignments_record['consumption_per_day'] = assignment.consumption
                        equipements.append((0, 0, assignments_record))
                    elif assignment.type_assignment == 'equipment' and assignment.categ_assignment == 'mini_equipment':
                        assignments_record['categ_execution'] = 'mini_equipment'
                        mini_equipements.append((0, 0, assignments_record))
                    elif assignment.type_assignment == 'equipment' and assignment.categ_assignment == 'site_installation':
                        assignments_record['categ_execution'] = 'site_installation'
                        site_install.append((0, 0, assignments_record))
                    elif assignment.type_assignment == 'equipment' and assignment.categ_assignment == 'equipment':
                        assignments_record['cost'] = assignment.cost
                        diesel.append((0, 0, assignments_record))

                vals['assigned_ressource_cost_ids'] = ressources
                vals['assigned_equipment_cost_ids'] = equipements
                vals['assigned_vehicule_cost_ids'] = vehicules
                vals['assigned_equipment_site_install_cost_ids'] = site_install
                vals['assigned_mini_equipment_cost_ids'] = mini_equipements
                vals['assigned_ressource_executor_cost_ids'] = exec_ressources
                vals['assigned_diesel_cost_ids'] = diesel
        return super(building_executed, self).write(vals)

    def compute_amount_moves_to_customer(self, date):
        for executed in self:
            amount_consumables = 0
            amount_supply_stock = 0
            pickings = self.env['stock.picking'].search([('site_id', '=', executed.site_id.id), ('picking_type', '=', 'to_partner'), ('state', '=', 'done'), ('date_validation', '=', date)])
            if pickings:
                for pick in pickings:
                    for mv in pick.move_ids_without_package:
                        last_price = self._get_product_last_price(executed.site_id.id, mv.product_id.id)
                        if mv.product_id.type == 'consu':
                            amount_consumables += last_price*mv.quantity_done
                        if mv.product_id.type == 'product':
                            amount_supply_stock += last_price*mv.quantity_done
        return amount_consumables, amount_supply_stock

    def actualize_executed_amounts_daily(self):
        self.env['building.executed.report'].search([('executed_id', '=', self.id), ('site_id', '=', self.site_id.id)]).unlink()
        self.env['building.executed.line.report'].search([('executed_id', '=', self.id), ('site_id', '=', self.site_id.id)]).unlink()
        self.env['building.executed.detail.report'].search([('executed_id', '=', self.id), ('site_id', '=', self.site_id.id)]).unlink()

        date_day = datetime.datetime.now().date()
        #a remmetre a pres la presentation
        # if (date_day > self.date_end) or (date_day < self.date_start):
        #     return True
        end_day = int(date_day.day)
        date_deb = self.date_start
        executed_line_report_ids = []
        for i in range(1, end_day + 1):
            
            previous_day_amount_business = 0
            last_date = date_deb - datetime.timedelta(days=1)
            last_executed_day = self.env['building.executed.report'].search([('date', '=', last_date), ('executed_id', '=', self.id), ('site_id', '=', self.site_id.id)])
            if last_executed_day:
                previous_day_amount_business = last_executed_day.executed_amount_business

            forcast_amount_business = sum((getattr(line, 'amount'+str(i)) for line in self.line_forcasted_ids), 0.0)
            executed_amount_business = sum((getattr(line, 'amount'+str(i)) for line in self.line_ids), 0.0)

            total_amount_equipment = sum((getattr(line, 'amount'+str(i)) for line in self.assigned_equipment_cost_ids if not line.assignment_id.vehicle_id.is_rental), 0.0)
            total_amount_rental_equipment = sum((getattr(line, 'amount'+str(i)) for line in self.assigned_equipment_cost_ids if line.assignment_id.vehicle_id.is_rental), 0.0)

            total_amount_diesel = sum((getattr(line, 'amount'+str(i))  for line in self.assigned_diesel_cost_ids), 0.0)
            total_amount_ressource = sum((getattr(line, 'amount'+str(i)) for line in self.assigned_ressource_cost_ids), 0.0)
            total_amount_site_install = sum((getattr(line, 'amount'+str(i)) for line in self.assigned_equipment_site_install_cost_ids), 0.0)
            total_amount_mini_equipment = sum((getattr(line, 'amount'+str(i)) for line in self.assigned_mini_equipment_cost_ids), 0.0)
            total_amount_executor_ressource = sum((getattr(line, 'amount'+str(i)) for line in self.assigned_ressource_executor_cost_ids), 0.0)
            
            amount_indirect_load = executed_amount_business*3.78/100
            amount_consumables, amount_supply_stock = self.compute_amount_moves_to_customer(date_deb)

            amount_exploitation_charges =  total_amount_equipment + total_amount_diesel + total_amount_ressource + total_amount_site_install + total_amount_mini_equipment + total_amount_executor_ressource + amount_indirect_load + amount_consumables + amount_supply_stock
            
            amount_result_executed = executed_amount_business - amount_exploitation_charges
            prc_result_executed = (amount_result_executed/executed_amount_business)*100 if executed_amount_business > 0 else 0
            amount_forcast_result = forcast_amount_business - amount_exploitation_charges
            prc_result_forcast = (amount_forcast_result/forcast_amount_business)*100 if forcast_amount_business > 0 else 0

            to_create = True
            record_ca_jj = {
                'date' : date_deb,
                'year': date_deb.year,
                'month': date_deb.month,
                'day': date_deb.day,
                'executed_id' : self.id,
                'site_id' : self.site_id.id,
                'forcast_amount_business' : forcast_amount_business,
                'previous_day_amount_business' : previous_day_amount_business,
                'executed_amount_business' : executed_amount_business,
                'amount_exploitation_charges' : amount_exploitation_charges,
                'amount_result_executed' : amount_result_executed,
                'prc_result_executed' : prc_result_executed,
                'amount_forcast_result' : amount_forcast_result,
                'prc_result_forcast' : prc_result_forcast
            }
            # executed_day = self.env['building.executed.report'].search([('date', '=', date_deb), ('executed_id', '=', self.id), ('site_id', '=', self.site_id.id)])
            # if executed_day:
            #     self.env['building.executed.report'].write(record_ca_jj)
            # else:
            executed_day = self.env['building.executed.report'].create(record_ca_jj)
            executed_line_report_ids.append(executed_day.id)
            record_ca_forcasted = {
                'date' : date_deb,
                'year': date_deb.year,
                'month': date_deb.month,
                'day': date_deb.day,
                'executed_id' : self.id,
                'report_exec_id': executed_day.id,
                'site_id' : self.site_id.id,
                'r0': 'forcated',
                'r1': 'forcated',
                'amount' : forcast_amount_business,
                'prc_amount_per_executed': 100
            }
            
            report_line = self.env['building.executed.line.report'].create(record_ca_forcasted)
            for line in self.line_forcasted_ids:
                if getattr(line, 'amount'+str(i)) > 0:
                    record_ca_details_forcasted = {
                        'date' : date_deb,
                        'year': date_deb.year,
                        'month': date_deb.month,
                        'day': date_deb.day,
                        'executed_id' : self.id,
                        'report_exec_id': executed_day.id,
                        'report_exec_line_id': report_line.id,
                        'site_id' : self.site_id.id,
                        'name': line.name,
                        'uom_id': line.uom_id.id,
                        'price_unit': line.price_unit,
                        'quantity': getattr(line, 'quantity'+str(i)),
                        'amount_total':getattr(line, 'amount'+str(i))
                    }
                    self.env['building.executed.detail.report'].create(record_ca_details_forcasted)

            record_ca_executed = {
                'date' : date_deb,
                'year': date_deb.year,
                'month': date_deb.month,
                'day': date_deb.day,
                'executed_id' : self.id,
                'report_exec_id': executed_day.id,
                'site_id' : self.site_id.id,
                'r0': 'executed',
                'r1': 'executed',
                'amount' : executed_amount_business,
                'prc_amount_per_executed': (executed_amount_business/executed_amount_business)*100 if executed_amount_business > 0 else 0
            }
            report_line = self.env['building.executed.line.report'].create(record_ca_executed)
            for line in self.line_ids:
                if getattr(line, 'amount'+str(i)) > 0:
                    record_ca_executed_details = {
                        'date' : date_deb,
                        'year': date_deb.year,
                        'month': date_deb.month,
                        'day': date_deb.day,
                        'executed_id' : self.id,
                        'report_exec_id': executed_day.id,
                        'report_exec_line_id': report_line.id,
                        'site_id' : self.site_id.id,
                        'name': line.name,
                        'uom_id': line.uom_id.id,
                        'price_unit': line.price_unit,
                        'quantity': getattr(line, 'quantity'+str(i)),
                        'amount_total':getattr(line, 'amount'+str(i)),
                    }
                    self.env['building.executed.detail.report'].create(record_ca_executed_details)

            record_load_equipment = {
                'date' : date_deb,
                'year': date_deb.year,
                'month': date_deb.month,
                'day': date_deb.day,
                'executed_id' : self.id,
                'report_exec_id': executed_day.id,
                'site_id' : self.site_id.id,
                'r0': 'load',
                'r1': 'equipment',
                'amount' : total_amount_equipment,
                'is_rental': False,
                'prc_amount_per_executed': (total_amount_equipment/executed_amount_business)*100 if executed_amount_business > 0 else 0
            }
            report_line = self.env['building.executed.line.report'].create(record_load_equipment)
            for line in self.assigned_equipment_cost_ids:
                if getattr(line, 'amount'+str(i)) > 0 and not line.assignment_id.vehicle_id.is_rental:
                    record_load_equipment_details = {
                        'date' : date_deb,
                        'year': date_deb.year,
                        'month': date_deb.month,
                        'day': date_deb.day,
                        'executed_id' : self.id,
                        'report_exec_id': executed_day.id,
                        'report_exec_line_id': report_line.id,
                        'site_id' : self.site_id.id,
                        'name': line.name,
                        'uom_id': line.uom_id.id,
                        'price_unit': line.cost,
                        'quantity': getattr(line, 'quantity'+str(i)),
                        'amount_total':getattr(line, 'amount'+str(i))
                    }
                    self.env['building.executed.detail.report'].create(record_load_equipment_details)

            record_load_rental_equipment = {
                'date' : date_deb,
                'year': date_deb.year,
                'month': date_deb.month,
                'day': date_deb.day,
                'executed_id' : self.id,
                'report_exec_id': executed_day.id,
                'site_id' : self.site_id.id,
                'r0': 'load',
                'r1': 'equipment',
                'amount' : total_amount_rental_equipment,
                'is_rental': True,
                'prc_amount_per_executed': (total_amount_rental_equipment/executed_amount_business)*100 if executed_amount_business > 0 else 0
            }
            report_line = self.env['building.executed.line.report'].create(record_load_rental_equipment)
            for line in self.assigned_equipment_cost_ids:
                if getattr(line, 'amount'+str(i)) > 0 and line.assignment_id.vehicle_id.is_rental:
                    record_load_rental_equipment_details = {
                        'date' : date_deb,
                        'year': date_deb.year,
                        'month': date_deb.month,
                        'day': date_deb.day,
                        'executed_id' : self.id,
                        'report_exec_id': executed_day.id,
                        'report_exec_line_id': report_line.id,
                        'site_id' : self.site_id.id,
                        'name': line.name,
                        'uom_id': line.uom_id.id,
                        'price_unit': line.cost,
                        'quantity': getattr(line, 'quantity'+str(i)),
                        'amount_total':getattr(line, 'amount'+str(i))
                    }
                    self.env['building.executed.detail.report'].create(record_load_rental_equipment_details)

            record_load_diesel = {
                'date' : date_deb,
                'year': date_deb.year,
                'month': date_deb.month,
                'day': date_deb.day,
                'executed_id' : self.id,
                'report_exec_id': executed_day.id,
                'site_id' : self.site_id.id,
                'r0': 'load',
                'r1': 'diesel',
                'amount' : total_amount_diesel,
                'prc_amount_per_executed': (total_amount_diesel/executed_amount_business)*100 if executed_amount_business > 0 else 0
            }
            report_line = self.env['building.executed.line.report'].create(record_load_diesel)
            for line in self.assigned_diesel_cost_ids:
                if getattr(line, 'amount'+str(i)) > 0:
                    record_load_diesel_details = {
                        'date' : date_deb,
                        'year': date_deb.year,
                        'month': date_deb.month,
                        'day': date_deb.day,
                        'executed_id' : self.id,
                        'report_exec_id': executed_day.id,
                        'report_exec_line_id': report_line.id,
                        'site_id' : self.site_id.id,
                        'name': line.name,
                        'uom_id': line.uom_id.id,
                        'price_unit': line.cost,
                        'quantity': getattr(line, 'quantity'+str(i)),
                        'amount_total':getattr(line, 'amount'+str(i))
                    }
                    self.env['building.executed.detail.report'].create(record_load_diesel_details)

            record_load_supervisor_ressource = {
                'date' : date_deb,
                'year': date_deb.year,
                'month': date_deb.month,
                'day': date_deb.day,
                'executed_id' : self.id,
                'report_exec_id': executed_day.id,
                'site_id' : self.site_id.id,
                'r0': 'load',
                'r1': 'supervisor_ressource',
                'amount' : total_amount_ressource,
                'prc_amount_per_executed': (total_amount_ressource/executed_amount_business)*100 if executed_amount_business > 0 else 0
            }
            
            report_line = self.env['building.executed.line.report'].create(record_load_supervisor_ressource)
            for line in self.assigned_ressource_cost_ids:
                if getattr(line, 'amount'+str(i)) > 0:
                    record_load_supervisor_ressource_details = {
                        'date' : date_deb,
                        'year': date_deb.year,
                        'month': date_deb.month,
                        'day': date_deb.day,
                        'executed_id' : self.id,
                        'report_exec_id': executed_day.id,
                        'report_exec_line_id': report_line.id,
                        'site_id' : self.site_id.id,
                        'name': line.assignment_id.name,
                        'uom_id': line.uom_id.id,
                        'price_unit': line.cost,
                        'quantity': getattr(line, 'quantity'+str(i)),
                        'amount_total':getattr(line, 'amount'+str(i))
                    }
                    self.env['building.executed.detail.report'].create(record_load_supervisor_ressource_details)

            record_load_site_install = {
                'date' : date_deb,
                'year': date_deb.year,
                'month': date_deb.month,
                'day': date_deb.day,
                'executed_id' : self.id,
                'report_exec_id': executed_day.id,
                'site_id' : self.site_id.id,
                'r0': 'load',
                'r1': 'site_install',
                'amount' : total_amount_site_install,
                'prc_amount_per_executed': (total_amount_site_install/executed_amount_business)*100 if executed_amount_business > 0 else 0
            }
            report_line = self.env['building.executed.line.report'].create(record_load_site_install)
            for line in self.assigned_equipment_site_install_cost_ids:
                if getattr(line, 'amount'+str(i)) > 0:
                    record_load_site_install_details = {
                        'date' : date_deb,
                        'year': date_deb.year,
                        'month': date_deb.month,
                        'day': date_deb.day,
                        'executed_id' : self.id,
                        'report_exec_id': executed_day.id,
                        'report_exec_line_id': report_line.id,
                        'site_id' : self.site_id.id,
                        'name': line.assignment_id.name,
                        'uom_id': line.uom_id.id,
                        'price_unit': line.cost,
                        'quantity': getattr(line, 'quantity'+str(i)),
                        'amount_total':getattr(line, 'amount'+str(i))
                    }
                    self.env['building.executed.detail.report'].create(record_load_site_install_details)

            record_load_mini_equipment = {
                'date' : date_deb,
                'year': date_deb.year,
                'month': date_deb.month,
                'day': date_deb.day,
                'executed_id' : self.id,
                'report_exec_id': executed_day.id,
                'site_id' : self.site_id.id,
                'r0': 'load',
                'r1': 'mini_equipment',
                'amount' : total_amount_mini_equipment,
                'prc_amount_per_executed': (total_amount_mini_equipment/executed_amount_business)*100 if executed_amount_business > 0 else 0
            }
            report_line = self.env['building.executed.line.report'].create(record_load_mini_equipment)
            for line in self.assigned_mini_equipment_cost_ids:
                if getattr(line, 'amount'+str(i)) > 0:
                    record_load_mini_equipment_details = {
                        'date' : date_deb,
                        'year': date_deb.year,
                        'month': date_deb.month,
                        'day': date_deb.day,
                        'executed_id' : self.id,
                        'report_exec_id': executed_day.id,
                        'report_exec_line_id': report_line.id,
                        'site_id' : self.site_id.id,
                        'name': line.assignment_id.name,
                        'uom_id': line.uom_id.id,
                        'price_unit': line.cost,
                        'quantity': getattr(line, 'quantity'+str(i)),
                        'amount_total':getattr(line, 'amount'+str(i))
                    }
                    self.env['building.executed.detail.report'].create(record_load_mini_equipment_details)

            record_load_executor_ressource = {
                'date' : date_deb,
                'year': date_deb.year,
                'month': date_deb.month,
                'day': date_deb.day,
                'executed_id' : self.id,
                'report_exec_id': executed_day.id,
                'site_id' : self.site_id.id,
                'r0': 'load',
                'r1': 'executor_ressource',
                'amount': total_amount_executor_ressource,
                'prc_amount_per_executed': (total_amount_executor_ressource/executed_amount_business)*100 if executed_amount_business > 0 else 0
            }
            report_line = self.env['building.executed.line.report'].create(record_load_executor_ressource)
            for line in self.assigned_ressource_executor_cost_ids:
                if getattr(line, 'amount'+str(i)) > 0:
                    record_load_executor_ressource_details = {
                        'date' : date_deb,
                        'year': date_deb.year,
                        'month': date_deb.month,
                        'day': date_deb.day,
                        'executed_id' : self.id,
                        'report_exec_id': executed_day.id,
                        'report_exec_line_id': report_line.id,
                        'site_id' : self.site_id.id,
                        'name': line.assignment_id.name,
                        'uom_id': line.uom_id.id,
                        'price_unit': line.cost,
                        'quantity': getattr(line, 'quantity'+str(i)),
                        'amount_total':getattr(line, 'amount'+str(i))
                    }
                    self.env['building.executed.detail.report'].create(record_load_executor_ressource_details)

            pickings = self.env['stock.picking'].search([('site_id', '=', self.site_id.id), ('picking_type', '=', 'to_partner'), ('state', '=', 'done'), ('date_validation', '=', date_deb)])

            record_load_consu = {
                'date' : date_deb,
                'year': date_deb.year,
                'month': date_deb.month,
                'day': date_deb.day,
                'executed_id' : self.id,
                'report_exec_id': executed_day.id,
                'site_id' : self.site_id.id,
                'r0': 'load',
                'r1': 'consu',
                'amount': amount_consumables,
                'prc_amount_per_executed': (amount_consumables/executed_amount_business)*100 if executed_amount_business > 0 else 0
            }
            report_line = self.env['building.executed.line.report'].create(record_load_consu)
            if pickings:
                for pick in pickings:
                    for mv in pick.move_ids_without_package:
                        last_price = self._get_product_last_price(executed.site_id.id, mv.product_id.id)
                        if mv.product_id.type == 'consu':
                            record_load_consu_details = {
                                'date' : date_deb,
                                'year': date_deb.year,
                                'month': date_deb.month,
                                'day': date_deb.day,
                                'executed_id' : self.id,
                                'report_exec_id': executed_day.id,
                                'report_exec_line_id': report_line.id,
                                'site_id' : self.site_id.id,
                                'name': mv.product_id.name,
                                'uom_id': mv.uom_id.id,
                                'price_unit': last_price,
                                'quantity': mv.quantity_done,
                                'amount_total':last_price*mv.quantity_done
                            }
                            self.env['building.executed.detail.report'].create(record_load_consu_details)

            record_load_product = {
                'date' : date_deb,
                'year': date_deb.year,
                'month': date_deb.month,
                'day': date_deb.day,
                'executed_id' : self.id,
                'report_exec_id': executed_day.id,
                'site_id' : self.site_id.id,
                'r0': 'load',
                'r1': 'product',
                'amount' : amount_supply_stock,
                'prc_amount_per_executed': (amount_supply_stock/executed_amount_business)*100 if executed_amount_business > 0 else 0
            }
            report_line = self.env['building.executed.line.report'].create(record_load_product)
            if pickings:
                for pick in pickings:
                    for mv in pick.move_ids_without_package:
                        last_price = self._get_product_last_price(executed.site_id.id, mv.product_id.id)
                        if mv.product_id.type == 'product':
                            record_load_product_details = {
                                'date' : date_deb,
                                'year': date_deb.year,
                                'month': date_deb.month,
                                'day': date_deb.day,
                                'executed_id' : self.id,
                                'report_exec_id': executed_day.id,
                                'report_exec_line_id': report_line.id,
                                'site_id' : self.site_id.id,
                                'name': mv.product_id.name,
                                'uom_id': mv.uom_id.id,
                                'price_unit': last_price,
                                'quantity': mv.quantity_done,
                                'amount_total':last_price*mv.quantity_done
                            }
                            self.env['building.executed.detail.report'].create(record_load_product_details)
            date_deb += datetime.timedelta(days=1)

        domain = [('id', 'in', executed_line_report_ids), ('site_id', '=', self.site_id.id), ('executed_id', '=', self.id)]
        search_view_id = self.env.ref('building.building_executed_report_action').id
        return {
            'name': _('Détails'),
            'domain': domain,
            'res_model': 'building.executed.report',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree',
            'search_view_id': search_view_id,
            'limit': 80
        }

class building_executed_line(models.Model):
    
    _name = 'building.executed.line'
    _description = "Lignes Excution"

    price_id = fields.Many2one('building.order.line', 'N° de Prix', domain=[('display_type', '=', False)])
    name = fields.Char('Description')
    quantity1 = fields.Float('J1', default=0)
    amount1 = fields.Float('J1', default=0)
    quantity2 = fields.Float('J2', default=0)
    amount2 = fields.Float('J2', default=0)
    quantity3 = fields.Float('J3', default=0)
    amount3 = fields.Float('J3', default=0)
    quantity4 = fields.Float('J4', default=0)
    amount4 = fields.Float('J4', default=0)
    quantity5 = fields.Float('J5', default=0)
    amount5 = fields.Float('J5', default=0)
    quantity6 = fields.Float('J6', default=0)
    amount6 = fields.Float('J6', default=0)
    quantity7 = fields.Float('J7', default=0)
    amount7 = fields.Float('J7', default=0)
    quantity8 = fields.Float('J8', default=0)
    amount8 = fields.Float('J8', default=0)
    quantity9 = fields.Float('J9', default=0)
    amount9 = fields.Float('J9', default=0)
    quantity10 = fields.Float('J10', default=0)
    amount10 = fields.Float('J10', default=0)
    quantity11 = fields.Float('J11', default=0)
    amount11 = fields.Float('J11', default=0)
    quantity12 = fields.Float('J12', default=0)
    amount12 = fields.Float('J12', default=0)
    quantity13 = fields.Float('J13', default=0)
    amount13 = fields.Float('J13', default=0)
    quantity14 = fields.Float('J14', default=0)
    amount14 = fields.Float('J14', default=0)
    quantity15 = fields.Float('J15', default=0)
    amount15 = fields.Float('J15', default=0)
    quantity16 = fields.Float('J16', default=0)
    amount16 = fields.Float('J16', default=0)
    quantity17 = fields.Float('J17', default=0)
    amount17 = fields.Float('J17', default=0)
    quantity18 = fields.Float('J18', default=0)
    amount18 = fields.Float('J18', default=0)
    quantity19 = fields.Float('J19', default=0)
    amount19 = fields.Float('J19', default=0)
    quantity20 = fields.Float('J20', default=0)
    amount20 = fields.Float('J20', default=0)
    quantity21 = fields.Float('J21', default=0)
    amount21 = fields.Float('J21', default=0)
    quantity22 = fields.Float('J22', default=0)
    amount22 = fields.Float('J22', default=0)
    quantity23 = fields.Float('J23', default=0)
    amount23 = fields.Float('J23', default=0)
    quantity24 = fields.Float('J24', default=0)
    amount24 = fields.Float('J24', default=0)
    quantity25 = fields.Float('J25', default=0)
    amount25 = fields.Float('J25', default=0)
    quantity26 = fields.Float('J26', default=0)
    amount26 = fields.Float('J26', default=0)
    quantity27 = fields.Float('J27', default=0)
    amount27 = fields.Float('J27', default=0)
    quantity28 = fields.Float('J28', default=0)
    amount28 = fields.Float('J28', default=0)
    quantity29 = fields.Float('J29', default=0)
    amount29 = fields.Float('J29', default=0)
    quantity30 = fields.Float('J30', default=0)
    amount30 = fields.Float('J30', default=0)
    quantity31 = fields.Float('J31', default=0)
    amount31 = fields.Float('J31', default=0)
    quantity = fields.Float('Quantité', readonly=False, store =True, compute='_compute_quantity')
    forcast_quantity = fields.Float('Quantité', readonly=False)
    uom_id = fields.Many2one('uom.uom', 'UdM')
    date = fields.Date(string='Date')
    price_unit = fields.Float(string='Prix Unitaire')
    amount_total = fields.Float(string='Total', readonly=False, store =True, compute='_compute_amount')
    amount_forcast = fields.Float(string='Total Prévisionnel', readonly=False, store =True, compute='_compute_amount')
    executed_id = fields.Many2one('building.executed', 'Ececute')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    sequence = fields.Integer(string='Sequence', default=10)

    @api.depends('price_unit', 'quantity')
    def _compute_amount(self):
        for line in self:
            line.amount_total = line.price_unit*line.quantity
            line.amount_forcast = line.price_unit*line.forcast_quantity

    @api.onchange('price_id')
    def _onchange_price_id(self):
        if self.price_id:
            self.name = self.price_id.price_number
            self.uom_id = self.price_id.product_uom.id
            self.price_unit = self.price_id.price_unit

    @api.depends('quantity1','quantity2','quantity3','quantity4','quantity5','quantity6','quantity7','quantity8','quantity9','quantity10','quantity11','quantity12','quantity13','quantity14','quantity15','quantity16','quantity17','quantity18','quantity19','quantity20','quantity21','quantity22','quantity23','quantity24','quantity25','quantity26','quantity27','quantity28','quantity29','quantity30','quantity31')      
    def _compute_quantity(self):
        for line in self:
            line.quantity = line.quantity1+line.quantity2+line.quantity3+line.quantity4+line.quantity5+line.quantity6+line.quantity7+line.quantity8+line.quantity9+line.quantity10+line.quantity11+line.quantity12+line.quantity13+line.quantity14+line.quantity15+line.quantity16+line.quantity17+line.quantity18+line.quantity19+line.quantity20+line.quantity21+line.quantity22+line.quantity23+line.quantity24+line.quantity25+line.quantity26+line.quantity27+line.quantity28+line.quantity29+line.quantity30+line.quantity31
            for i in range(1, 32):
                val_amount = getattr(line, 'quantity'+str(i))*line.price_unit
                setattr(line, 'amount'+str(i), val_amount)

class building_executed_forcasted_line(models.Model):
    
    _name = 'building.executed.forcasted.line'
    _description = "Lignes Excution"

    price_id = fields.Many2one('building.order.line', 'N° de Prix', domain=[('display_type', '=', False)])
    name = fields.Char('Description')
    quantity1 = fields.Float('J1', default=0)
    amount1 = fields.Float('J1', default=0)
    quantity2 = fields.Float('J2', default=0)
    amount2 = fields.Float('J2', default=0)
    quantity3 = fields.Float('J3', default=0)
    amount3 = fields.Float('J3', default=0)
    quantity4 = fields.Float('J4', default=0)
    amount4 = fields.Float('J4', default=0)
    quantity5 = fields.Float('J5', default=0)
    amount5 = fields.Float('J5', default=0)
    quantity6 = fields.Float('J6', default=0)
    amount6 = fields.Float('J6', default=0)
    quantity7 = fields.Float('J7', default=0)
    amount7 = fields.Float('J7', default=0)
    quantity8 = fields.Float('J8', default=0)
    amount8 = fields.Float('J8', default=0)
    quantity9 = fields.Float('J9', default=0)
    amount9 = fields.Float('J9', default=0)
    quantity10 = fields.Float('J10', default=0)
    amount10 = fields.Float('J10', default=0)
    quantity11 = fields.Float('J11', default=0)
    amount11 = fields.Float('J11', default=0)
    quantity12 = fields.Float('J12', default=0)
    amount12 = fields.Float('J12', default=0)
    quantity13 = fields.Float('J13', default=0)
    amount13 = fields.Float('J13', default=0)
    quantity14 = fields.Float('J14', default=0)
    amount14 = fields.Float('J14', default=0)
    quantity15 = fields.Float('J15', default=0)
    amount15 = fields.Float('J15', default=0)
    quantity16 = fields.Float('J16', default=0)
    amount16 = fields.Float('J16', default=0)
    quantity17 = fields.Float('J17', default=0)
    amount17 = fields.Float('J17', default=0)
    quantity18 = fields.Float('J18', default=0)
    amount18 = fields.Float('J18', default=0)
    quantity19 = fields.Float('J19', default=0)
    amount19 = fields.Float('J19', default=0)
    quantity20 = fields.Float('J20', default=0)
    amount20 = fields.Float('J20', default=0)
    quantity21 = fields.Float('J21', default=0)
    amount21 = fields.Float('J21', default=0)
    quantity22 = fields.Float('J22', default=0)
    amount22 = fields.Float('J22', default=0)
    quantity23 = fields.Float('J23', default=0)
    amount23 = fields.Float('J23', default=0)
    quantity24 = fields.Float('J24', default=0)
    amount24 = fields.Float('J24', default=0)
    quantity25 = fields.Float('J25', default=0)
    amount25 = fields.Float('J25', default=0)
    quantity26 = fields.Float('J26', default=0)
    amount26 = fields.Float('J26', default=0)
    quantity27 = fields.Float('J27', default=0)
    amount27 = fields.Float('J27', default=0)
    quantity28 = fields.Float('J28', default=0)
    amount28 = fields.Float('J28', default=0)
    quantity29 = fields.Float('J29', default=0)
    amount29 = fields.Float('J29', default=0)
    quantity30 = fields.Float('J30', default=0)
    amount30 = fields.Float('J30', default=0)
    quantity31 = fields.Float('J31', default=0)
    amount31 = fields.Float('J31', default=0)
    quantity = fields.Float('Quantité', readonly=False, store =True, compute='_compute_quantity')
    forcast_quantity = fields.Float('Quantité', readonly=False)
    uom_id = fields.Many2one('uom.uom', 'UdM')
    date = fields.Date(string='Date')
    price_unit = fields.Float(string='Prix Unitaire')
    amount_total = fields.Float(string='Total', readonly=False, store =True, compute='_compute_amount')
    amount_forcast = fields.Float(string='Total Prévisionnel', readonly=False, store =True, compute='_compute_amount')
    executed_id = fields.Many2one('building.executed', 'Ececute')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    sequence = fields.Integer(string='Sequence', default=10)

    @api.depends('price_unit', 'quantity')
    def _compute_amount(self):
        for line in self:
            line.amount_total = line.price_unit*line.quantity
            line.amount_forcast = line.price_unit*line.forcast_quantity

    @api.onchange('price_id')
    def _onchange_price_id(self):
        if self.price_id:
            self.name = self.price_id.price_number
            self.uom_id = self.price_id.product_uom.id
            self.price_unit = self.price_id.price_unit

    @api.depends('quantity1','quantity2','quantity3','quantity4','quantity5','quantity6','quantity7','quantity8','quantity9','quantity10','quantity11','quantity12','quantity13','quantity14','quantity15','quantity16','quantity17','quantity18','quantity19','quantity20','quantity21','quantity22','quantity23','quantity24','quantity25','quantity26','quantity27','quantity28','quantity29','quantity30','quantity31')      
    def _compute_quantity(self):
        for line in self:
            line.quantity = line.quantity1+line.quantity2+line.quantity3+line.quantity4+line.quantity5+line.quantity6+line.quantity7+line.quantity8+line.quantity9+line.quantity10+line.quantity11+line.quantity12+line.quantity13+line.quantity14+line.quantity15+line.quantity16+line.quantity17+line.quantity18+line.quantity19+line.quantity20+line.quantity21+line.quantity22+line.quantity23+line.quantity24+line.quantity25+line.quantity26+line.quantity27+line.quantity28+line.quantity29+line.quantity30+line.quantity31
            for i in range(1, 32):
                val_amount = getattr(line, 'quantity'+str(i))*line.price_unit
                setattr(line, 'amount'+str(i), val_amount)

class building_assignment(models.Model):
    
    _name = 'building.assignment'
    _description = "Affectation"
    
    name = fields.Char("Nom")
    site_id = fields.Many2one('building.site', 'Affaire')
    site_installation_ids = fields.One2many('building.assignment.line', 'assignment_id', 'Lignes', readonly=False, copy=True, domain=[('type_assignment', '=', 'equipment'), ('categ_assignment', '=', 'site_installation')])
    ressource_humain_supervisor_ids = fields.One2many('building.assignment.line', 'assignment_id', 'Lignes', readonly=False, copy=True, domain=[('type_assignment', '=', 'emp'), ('categ_assignment', '=', 'supervisor')])
    equipment_ids = fields.One2many('building.assignment.line', 'assignment_id', 'Lignes', readonly=False, copy=True, domain=[('type_assignment', '=', 'equipment'), ('categ_assignment', '=', 'equipment')])
    mini_equipment_ids = fields.One2many('building.assignment.line', 'assignment_id', 'Lignes', readonly=False, copy=True, domain=[('type_assignment', '=', 'equipment'), ('categ_assignment', '=', 'mini_equipment')])
    diesel_consumption_ids = fields.One2many('building.assignment.line', 'assignment_id', 'Lignes', readonly=False, copy=True, domain=[('type_assignment', '=', 'equipment'), ('categ_assignment', '=', 'diesel')])
    ressource_humain_executor_ids = fields.One2many('building.assignment.line', 'assignment_id', 'Lignes', readonly=False, copy=True, domain=[('type_assignment', '=', 'emp'), ('categ_assignment', '=', 'executor')])
    maintenance_request_id = fields.Many2one('maintenance.request.resource.material', 'Demande')

    @api.model
    def create(self, vals):
        sequ = self.env['ir.sequence'].get('building.assignment')
        vals['name'] = sequ
        return super(building_assignment, self).create(vals)

class building_assignment_line(models.Model):
    
    _name = 'building.assignment.line'
    _description = "Affectation"
    
    @api.depends('employee_id', 'equipment_id', 'vehicle_id', 'type_assignment')
    def _compute_name(self):
        for assignment in self:
            name = None
            if assignment.type_assignment == 'emp':
                name = assignment.employee_id.name
            elif assignment.type_assignment == 'equipment':
                name = assignment.vehicle_id.name
            if assignment.type_assignment == 'small_equipment':
                name = assignment.equipment_id.name
            assignment.name = name

    @api.depends('date_start', 'date_end')
    def _compute_assignment_time(self):
        for assignment in self:
            assignment.assignment_time = (assignment.date_end-assignment.date_start).days

    @api.depends('assignment_time', 'cost')
    def _compute_assignment_amount(self):
        for assignment in self:
            assignment.assignment_amount = assignment.assignment_time*assignment.cost

    name = fields.Char("Nom", compute='_compute_name')
    site_id = fields.Many2one('building.site', 'Affaire')
    assignment_id = fields.Many2one('building.assignAffectation ouvertement', 'Affectation')
    employee_id = fields.Many2one('hr.employee', string='Ressource')
    job_id = fields.Many2one('hr.job', string='Poste')
    categ_maintenance_id = fields.Many2one('maintenance.equipment.category', string='Catégorie')
    categ_fleet_id = fields.Many2one('maintenance.vehicle.category', string='Catégorie')
    equipment_id = fields.Many2one('product.product', string='Petit Matériel')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Matériel')
    attendance_type = fields.Selection([('daily', 'Journalier'), ('monthly', 'Mensuel')], string="Pointage")
    product_id = fields.Many2one('product.product', string='Article')
    code = fields.Char('Code', related='vehicle_id.code')
    uom_id = fields.Many2one('uom.uom', 'UdM')
    quantity =  fields.Float(string='Quantité', default=1)
    cost = fields.Float('Coût', related="vehicle_id.cost")
    date_start = fields.Date(string='Date Début')
    date_end = fields.Date(string='Date Fin')
    state  = fields.Selection([('open', 'Affectation ouverte'), ('closed', 'Affectation cloturé'), ('canceled', 'Annulée')], string="Status", default='open')
    type_assignment = fields.Selection([('emp', 'Ressource'), ('equipment', 'Matériel'), ('small_equipment', 'Petit Matériel'), ('product', 'Coffrage')], string="Type Affectation", default='')
    categ_assignment = fields.Selection([('site_installation', 'Installation de chantier'), ('supervisor', 'Encadrement'), ('executor', 'Main-d’œuvre'), ('equipment', 'Matériel'), ('mini_equipment', 'Outillage'), ('diesel', 'Gasoil'), ('product', 'Coffrage')], string="Catégorie Affectation", default='')
    duree =  fields.Float(string='Durée(Mois)', default=1)
    duree_j =  fields.Float(string='Durée(Jours)', default=1)
    duree_h =  fields.Float(string='Heures de travail/J', default=1)
    consumption = fields.Float(string='Consommation(L/J)')
    maintenance_request_id = fields.Many2one('maintenance.request.resource.material', 'Demande')
    assignment_time = fields.Integer("Durée d'affectation", compute='_compute_assignment_time')
    assignment_amount = fields.Integer("Montant d'affectation", compute='_compute_assignment_amount')
    maintenance_request_line_id = fields.Many2one('maintenance.request.resource.material.line', string='Ligne demande')

    def action_open_user_building_assignment_line(self, group):
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
            ('categ_assignment','=','equipment'),
            ('site_id', 'in', site_ids)
        ]

        tree_view = self.env.ref('building.building_assignment_vehicle_tree')
    
        if group in ['SOTASERV_OPC', 'SOTASERV_CHEF_PROJET', 'SOTASERV_CONDUCT_TRV', 'SOTASERV_DIRECTEUR_ZONE']:
            tree_view = self.env.ref('building.view_assignment_vehicle_tree_inherit')

        return {
            'name': 'Affectations',
            'type': 'ir.actions.act_window',
            'res_model': 'building.assignment.line',
            'view_mode': 'tree',
            'views': [(tree_view.id, 'tree')],
            'domain': domain,
            'context': context,
            'search_view_id': self.env.ref('building.building_assignment_line_filter').id,
        }

    def action_closing(self):
        for assignment in self:
            assignment.write({'state':'closed'})
            if assignment.type_assignment == 'emp':
                assignment.employee_id.state = 'available'
            if assignment.type_assignment == 'small_equipment':
                assignment.equipment_id.state = 'available'
            if assignment.type_assignment == 'equipment':
                assignment.vehicle_id.state = 'available'
                assignment.vehicle_id.old_location = assignment.site_id.name
        return True

    def open_cancel_confirm(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Confirmation d\'annulation'),
            'res_model': 'building.assignment.line',
            'view_mode': 'form',
            'view_id': self.env.ref('building.assigned_view_form_confirm_cancel').id,
            'res_id': self.id,
            'target': 'new',
        }
    
    def action_canceled(self):
        for assignment in self:
            assignment.write({'state':'canceled'})
            if assignment.type_assignment == 'emp':
                assignment.employee_id.state = 'available'
            elif assignment.type_assignment == 'small_equipment':
                assignment.equipment_id.state = 'available'
            if assignment.type_assignment == 'equipment':
                assignment.vehicle_id.state = 'available'
                assignment.vehicle_id.location = assignment.vehicle_id.old_location
        return True

    def cron_create_pointage(self):
        today = date.today()

        start_of_day = datetime.combine(today, time.min)
        end_of_day = datetime.combine(today, time.max)

        first_day_month = today.replace(day=1)
        last_day_month = (
            first_day_month + relativedelta(months=1) - relativedelta(days=1)
        )

        Incident = self.env['incident.materiel']
        WorkedHours = self.env['materials.worked.hours']

        daily_lines = self.search([
            ('attendance_type', '=', 'daily'),
            ('state', '=', 'open')
        ])

        for line in daily_lines:
            has_incident = Incident.search([
                ('fleet_id', '=', line.vehicle_id.id),
                ('date', '>=', start_of_day),
                ('date', '<=', end_of_day),
                ('state', 'in', ['approved', 'resolved'])
            ], limit=1)

            WorkedHours.create({
                'assignment_line_id': line.id,
                'site_id': line.site_id.id,
                'maintenance_request_id': line.maintenance_request_id.id,
                'maintenance_request_line_id': line.maintenance_request_line_id.id,
                'worked_date': today,
                'vehicle_id': line.vehicle_id.id,
                'worked_hours_by_vehicle': 0 if has_incident else 8,
            })

        if today == last_day_month:
            monthly_lines = self.search([
                ('attendance_type', '=', 'monthly'),
                ('state', '=', 'open')
            ])

            for line in monthly_lines:
                incident_count = Incident.search_count([
                    ('fleet_id', '=', line.vehicle_id.id),
                    ('date', '>=', datetime.combine(first_day_month, time.min)),
                    ('date', '<=', datetime.combine(last_day_month, time.max)),
                    ('state', 'in', ['approved', 'resolved'])
                ])

                worked_days = max(26 - incident_count, 0)

                WorkedHours.create({
                    'assignment_line_id': line.id,
                    'site_id': line.site_id.id,
                    'maintenance_request_id': line.maintenance_request_id.id,
                    'maintenance_request_line_id': line.maintenance_request_line_id.id,
                    'worked_date': today,
                    'vehicle_id': line.vehicle_id.id,
                    'worked_hours_by_vehicle': worked_days,
                })


class fleet_vehicle(models.Model):
    
    _inherit = 'fleet.vehicle'

    state  = fields.Selection([('available', 'Disponible'), ('assigned', 'Affecté')], string="status", default='available')
    old_location = fields.Char('Localisation')

class building_executed_vehicule(models.Model):
    
    _name = 'building.executed.vehicule'
    _description = "Excution vehicule"

    assignment_id = fields.Many2one('building.assignment.line', 'Affectation', domain=[('type_assignment', '=', 'vehicle')])
    name = fields.Char('Description')
    quantity1 = fields.Float('J1', default=0)
    amount1 = fields.Float('J1', default=0)
    quantity2 = fields.Float('J2', default=0)
    amount2 = fields.Float('J2', default=0)
    quantity3 = fields.Float('J3', default=0)
    amount3 = fields.Float('J3', default=0)
    quantity4 = fields.Float('J4', default=0)
    amount4 = fields.Float('J4', default=0)
    quantity5 = fields.Float('J5', default=0)
    amount5 = fields.Float('J5', default=0)
    quantity6 = fields.Float('J6', default=0)
    amount6 = fields.Float('J6', default=0)
    quantity7 = fields.Float('J7', default=0)
    amount7 = fields.Float('J7', default=0)
    quantity8 = fields.Float('J8', default=0)
    amount8 = fields.Float('J8', default=0)
    quantity9 = fields.Float('J9', default=0)
    amount9 = fields.Float('J9', default=0)
    quantity10 = fields.Float('J10', default=0)
    amount10 = fields.Float('J10', default=0)
    quantity11 = fields.Float('J11', default=0)
    amount11 = fields.Float('J11', default=0)
    quantity12 = fields.Float('J12', default=0)
    amount12 = fields.Float('J12', default=0)
    quantity13 = fields.Float('J13', default=0)
    amount13 = fields.Float('J13', default=0)
    quantity14 = fields.Float('J14', default=0)
    amount14 = fields.Float('J14', default=0)
    quantity15 = fields.Float('J15', default=0)
    amount15 = fields.Float('J15', default=0)
    quantity16 = fields.Float('J16', default=0)
    amount16 = fields.Float('J16', default=0)
    quantity17 = fields.Float('J17', default=0)
    amount17 = fields.Float('J17', default=0)
    quantity18 = fields.Float('J18', default=0)
    amount18 = fields.Float('J18', default=0)
    quantity19 = fields.Float('J19', default=0)
    amount19 = fields.Float('J19', default=0)
    quantity20 = fields.Float('J20', default=0)
    amount20 = fields.Float('J20', default=0)
    quantity21 = fields.Float('J21', default=0)
    amount21 = fields.Float('J21', default=0)
    quantity22 = fields.Float('J22', default=0)
    amount22 = fields.Float('J22', default=0)
    quantity23 = fields.Float('J23', default=0)
    amount23 = fields.Float('J23', default=0)
    quantity24 = fields.Float('J24', default=0)
    amount24 = fields.Float('J24', default=0)
    quantity25 = fields.Float('J25', default=0)
    amount25 = fields.Float('J25', default=0)
    quantity26 = fields.Float('J26', default=0)
    amount26 = fields.Float('J26', default=0)
    quantity27 = fields.Float('J27', default=0)
    amount27 = fields.Float('J27', default=0)
    quantity28 = fields.Float('J28', default=0)
    amount28 = fields.Float('J28', default=0)
    quantity29 = fields.Float('J29', default=0)
    amount29 = fields.Float('J29', default=0)
    quantity30 = fields.Float('J30', default=0)
    amount30 = fields.Float('J30', default=0)
    quantity31 = fields.Float('J31', default=0)
    amount31 = fields.Float('J31', default=0)
    quantity = fields.Float('Quantité', readonly=False, store =True, compute='_compute_quantity')
    uom_id = fields.Many2one('uom.uom', 'UdM')
    cost = fields.Float(string='Coût Unitaire')
    total_cost_vehicule = fields.Float(string='Total', readonly=False, store =True, compute='_compute_amount')
    executed_id = fields.Many2one('building.executed', 'Ececute')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    sequence = fields.Integer(string='Sequence', default=10)

    @api.depends('cost', 'quantity')
    def _compute_amount(self):
        for line in self:
            line.total_cost_vehicule = line.cost*line.quantity

    @api.onchange('assignment_id')
    def _onchange_assignment_id(self):
        if self.assignment_id:
            self.name = self.assignment_id.code
            self.uom_id = self.assignment_id.uom_id.id
            self.cost = self.assignment_id.cost

    @api.depends('quantity1','quantity2','quantity3','quantity4','quantity5','quantity6','quantity7','quantity8','quantity9','quantity10','quantity11','quantity12','quantity13','quantity14','quantity15','quantity16','quantity17','quantity18','quantity19','quantity20','quantity21','quantity22','quantity23','quantity24','quantity25','quantity26','quantity27','quantity28','quantity29','quantity30','quantity31')      
    def _compute_quantity(self):
        for line in self:
            line.quantity = line.quantity1+line.quantity2+line.quantity3+line.quantity4+line.quantity5+line.quantity6+line.quantity7+line.quantity8+line.quantity9+line.quantity10+line.quantity11+line.quantity12+line.quantity13+line.quantity14+line.quantity15+line.quantity16+line.quantity17+line.quantity18+line.quantity19+line.quantity20+line.quantity21+line.quantity22+line.quantity23+line.quantity24+line.quantity25+line.quantity26+line.quantity27+line.quantity28+line.quantity29+line.quantity30+line.quantity31
            for i in range(1, 32):
                val_amount = getattr(line, 'quantity'+str(i))*line.price_unit
                setattr(line, 'amount'+str(i), val_amount)

class building_executed_equipment(models.Model):
    
    _name = 'building.executed.equipment'
    _description = "Excution equipment"

    assignment_id = fields.Many2one('building.assignment.line', 'Affectation', domain=[('type_assignment', '=', 'equipment')])
    name = fields.Char('Description')
    quantity1 = fields.Float('J1', default=0)
    amount1 = fields.Float('J1', default=0)
    quantity2 = fields.Float('J2', default=0)
    amount2 = fields.Float('J2', default=0)
    quantity3 = fields.Float('J3', default=0)
    amount3 = fields.Float('J3', default=0)
    quantity4 = fields.Float('J4', default=0)
    amount4 = fields.Float('J4', default=0)
    quantity5 = fields.Float('J5', default=0)
    amount5 = fields.Float('J5', default=0)
    quantity6 = fields.Float('J6', default=0)
    amount6 = fields.Float('J6', default=0)
    quantity7 = fields.Float('J7', default=0)
    amount7 = fields.Float('J7', default=0)
    quantity8 = fields.Float('J8', default=0)
    amount8 = fields.Float('J8', default=0)
    quantity9 = fields.Float('J9', default=0)
    amount9 = fields.Float('J9', default=0)
    quantity10 = fields.Float('J10', default=0)
    amount10 = fields.Float('J10', default=0)
    quantity11 = fields.Float('J11', default=0)
    amount11 = fields.Float('J11', default=0)
    quantity12 = fields.Float('J12', default=0)
    amount12 = fields.Float('J12', default=0)
    quantity13 = fields.Float('J13', default=0)
    amount13 = fields.Float('J13', default=0)
    quantity14 = fields.Float('J14', default=0)
    amount14 = fields.Float('J14', default=0)
    quantity15 = fields.Float('J15', default=0)
    amount15 = fields.Float('J15', default=0)
    quantity16 = fields.Float('J16', default=0)
    amount16 = fields.Float('J16', default=0)
    quantity17 = fields.Float('J17', default=0)
    amount17 = fields.Float('J17', default=0)
    quantity18 = fields.Float('J18', default=0)
    amount18 = fields.Float('J18', default=0)
    quantity19 = fields.Float('J19', default=0)
    amount19 = fields.Float('J19', default=0)
    quantity20 = fields.Float('J20', default=0)
    amount20 = fields.Float('J20', default=0)
    quantity21 = fields.Float('J21', default=0)
    amount21 = fields.Float('J21', default=0)
    quantity22 = fields.Float('J22', default=0)
    amount22 = fields.Float('J22', default=0)
    quantity23 = fields.Float('J23', default=0)
    amount23 = fields.Float('J23', default=0)
    quantity24 = fields.Float('J24', default=0)
    amount24 = fields.Float('J24', default=0)
    quantity25 = fields.Float('J25', default=0)
    amount25 = fields.Float('J25', default=0)
    quantity26 = fields.Float('J26', default=0)
    amount26 = fields.Float('J26', default=0)
    quantity27 = fields.Float('J27', default=0)
    amount27 = fields.Float('J27', default=0)
    quantity28 = fields.Float('J28', default=0)
    amount28 = fields.Float('J28', default=0)
    quantity29 = fields.Float('J29', default=0)
    amount29 = fields.Float('J29', default=0)
    quantity30 = fields.Float('J30', default=0)
    amount30 = fields.Float('J30', default=0)
    quantity31 = fields.Float('J31', default=0)
    amount31 = fields.Float('J31', default=0)
    diesel_consumption = fields.Float(string='Gasoil')
    consumption_per_day = fields.Float(string='Gasoil(L/J)')
    quantity = fields.Float('Quantité', readonly=False, store =True, compute='_compute_quantity')
    uom_id = fields.Many2one('uom.uom', 'UdM')
    cost = fields.Float(string='Coût Unitaire')
    total_cost_equipment = fields.Float(string='Total', readonly=False, store =True, compute='_compute_amount')
    executed_id = fields.Many2one('building.executed', 'Ececute')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    sequence = fields.Integer(string='Sequence', default=10)
    categ_execution  = fields.Selection([('site_installation', 'Installation de chantier'), ('equipment', 'Matériel'), ('mini_equipment', 'Petit Matériel'), ('diesel', 'Gasoil')], string="Catégorie", default='')

    @api.depends('cost', 'quantity')
    def _compute_amount(self):
        for line in self:
            line.total_cost_equipment = line.cost*line.quantity

    @api.onchange('assignment_id')
    def _onchange_assignment_id(self):
        if self.assignment_id:
            self.name = self.assignment_id.code
            self.uom_id = self.assignment_id.uom_id.id
            self.cost = self.assignment_id.cost

    @api.depends('quantity1','quantity2','quantity3','quantity4','quantity5','quantity6','quantity7','quantity8','quantity9','quantity10','quantity11','quantity12','quantity13','quantity14','quantity15','quantity16','quantity17','quantity18','quantity19','quantity20','quantity21','quantity22','quantity23','quantity24','quantity25','quantity26','quantity27','quantity28','quantity29','quantity30','quantity31')      
    def _compute_quantity(self):
        for line in self:
            line.quantity = line.quantity1+line.quantity2+line.quantity3+line.quantity4+line.quantity5+line.quantity6+line.quantity7+line.quantity8+line.quantity9+line.quantity10+line.quantity11+line.quantity12+line.quantity13+line.quantity14+line.quantity15+line.quantity16+line.quantity17+line.quantity18+line.quantity19+line.quantity20+line.quantity21+line.quantity22+line.quantity23+line.quantity24+line.quantity25+line.quantity26+line.quantity27+line.quantity28+line.quantity29+line.quantity30+line.quantity31
            for i in range(1, 32):
                val_amount = getattr(line, 'quantity'+str(i))*line.cost
                setattr(line, 'amount'+str(i), val_amount)

class building_executed_ressource(models.Model):
    
    _name = 'building.executed.ressource'
    _description = "Excution Ressource"

    assignment_id = fields.Many2one('building.assignment.line', 'Affectation', domain=[('type_assignment', '=', 'emp')])
    attendance_id = fields.Many2one('hr.attendance', 'Présence')
    name = fields.Char('Description')
    quantity1 = fields.Float('J1', default=0)
    amount1 = fields.Float('J1', default=0)
    quantity2 = fields.Float('J2', default=0)
    amount2 = fields.Float('J2', default=0)
    quantity3 = fields.Float('J3', default=0)
    amount3 = fields.Float('J3', default=0)
    quantity4 = fields.Float('J4', default=0)
    amount4 = fields.Float('J4', default=0)
    quantity5 = fields.Float('J5', default=0)
    amount5 = fields.Float('J5', default=0)
    quantity6 = fields.Float('J6', default=0)
    amount6 = fields.Float('J6', default=0)
    quantity7 = fields.Float('J7', default=0)
    amount7 = fields.Float('J7', default=0)
    quantity8 = fields.Float('J8', default=0)
    amount8 = fields.Float('J8', default=0)
    quantity9 = fields.Float('J9', default=0)
    amount9 = fields.Float('J9', default=0)
    quantity10 = fields.Float('J10', default=0)
    amount10 = fields.Float('J10', default=0)
    quantity11 = fields.Float('J11', default=0)
    amount11 = fields.Float('J11', default=0)
    quantity12 = fields.Float('J12', default=0)
    amount12 = fields.Float('J12', default=0)
    quantity13 = fields.Float('J13', default=0)
    amount13 = fields.Float('J13', default=0)
    quantity14 = fields.Float('J14', default=0)
    amount14 = fields.Float('J14', default=0)
    quantity15 = fields.Float('J15', default=0)
    amount15 = fields.Float('J15', default=0)
    quantity16 = fields.Float('J16', default=0)
    amount16 = fields.Float('J16', default=0)
    quantity17 = fields.Float('J17', default=0)
    amount17 = fields.Float('J17', default=0)
    quantity18 = fields.Float('J18', default=0)
    amount18 = fields.Float('J18', default=0)
    quantity19 = fields.Float('J19', default=0)
    amount19 = fields.Float('J19', default=0)
    quantity20 = fields.Float('J20', default=0)
    amount20 = fields.Float('J20', default=0)
    quantity21 = fields.Float('J21', default=0)
    amount21 = fields.Float('J21', default=0)
    quantity22 = fields.Float('J22', default=0)
    amount22 = fields.Float('J22', default=0)
    quantity23 = fields.Float('J23', default=0)
    amount23 = fields.Float('J23', default=0)
    quantity24 = fields.Float('J24', default=0)
    amount24 = fields.Float('J24', default=0)
    quantity25 = fields.Float('J25', default=0)
    amount25 = fields.Float('J25', default=0)
    quantity26 = fields.Float('J26', default=0)
    amount26 = fields.Float('J26', default=0)
    quantity27 = fields.Float('J27', default=0)
    amount27 = fields.Float('J27', default=0)
    quantity28 = fields.Float('J28', default=0)
    amount28 = fields.Float('J28', default=0)
    quantity29 = fields.Float('J29', default=0)
    amount29 = fields.Float('J29', default=0)
    quantity30 = fields.Float('J30', default=0)
    amount30 = fields.Float('J30', default=0)
    quantity31 = fields.Float('J31', default=0)
    amount31 = fields.Float('J31', default=0)
    quantity = fields.Float('Quantité', readonly=False, store =True, compute='_compute_quantity')
    uom_id = fields.Many2one('uom.uom', 'UdM')
    cost = fields.Float(string='Coût Unitaire')
    total_cost_ressource = fields.Float(string='Total', readonly=False, store =True, compute='_compute_amount')
    executed_id = fields.Many2one('building.executed', 'Ececute')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    sequence = fields.Integer(string='Sequence', default=10)
    site_id = fields.Many2one('building.site', string='Affaire',related='assignment_id.site_id', store=True, readonly=True)
    categ_execution  = fields.Selection([('supervisor', 'Encadrement'), ('executor', 'Main-d’œuvre')], string="Catégorie", default='')

    @api.depends('cost', 'quantity')
    def _compute_amount(self):
        for line in self:
            line.total_cost_ressource = line.cost*line.quantity

    @api.onchange('assignment_id')
    def _onchange_assignment_id(self):
        if self.assignment_id:
            self.name = self.assignment_id.code
            self.uom_id = self.assignment_id.uom_id.id
            self.cost = self.assignment_id.cost

    @api.depends('quantity1', 'quantity2', 'quantity3', 'quantity4', 'quantity5', 'quantity6', 'quantity7', 'quantity8', 'quantity9', 'quantity10', 'quantity11', 'quantity12', 'quantity13', 'quantity14', 'quantity15', 'quantity16', 'quantity17', 'quantity18', 'quantity19', 'quantity20', 'quantity21', 'quantity22', 'quantity23', 'quantity24', 'quantity25', 'quantity26', 'quantity27', 'quantity28', 'quantity29', 'quantity30', 'quantity31')      
    def _compute_quantity(self):
        for line in self:
            line.quantity = line.quantity1+line.quantity2+line.quantity3+line.quantity4+line.quantity5+line.quantity6+line.quantity7+line.quantity8+line.quantity9+line.quantity10+line.quantity11+line.quantity12+line.quantity13+line.quantity14+line.quantity15+line.quantity16+line.quantity17+line.quantity18+line.quantity19+line.quantity20+line.quantity21+line.quantity22+line.quantity23+line.quantity24+line.quantity25+line.quantity26+line.quantity27+line.quantity28+line.quantity29+line.quantity30+line.quantity31                
            for i in range(1, 32):
                val_amount = getattr(line, 'quantity'+str(i))*line.cost
                setattr(line, 'amount'+str(i), val_amount)

# class building_executed_executor_ressource(models.Model):
    
#     _name = 'building.executed.executor.ressource'
#     _description = "Excution Ressource"

#     assignment_id = fields.Many2one('building.assignment.line', 'Affectation', domain=[('type_assignment', '=', 'emp')])


# class building_executed_supervisor_ressource(models.Model):
    
#     _name = 'building.executed.supervisor.ressource'
#     _description = "Excution Ressource"

#     assignment_id = fields.Many2one('building.assignment.line', 'Affectation', domain=[('type_assignment', '=', 'emp')])


class building_executed_diesel(models.Model):
    
    _name = 'building.executed.diesel'
    _description = "Excution diesel"

    assignment_id = fields.Many2one('building.assignment.line', 'Affectation', domain=[('type_assignment', '=', 'emp')])
    name = fields.Char('Description')
    quantity1 = fields.Float('J1', default=0)
    amount1 = fields.Float('J1', default=0)
    quantity2 = fields.Float('J2', default=0)
    amount2 = fields.Float('J2', default=0)
    quantity3 = fields.Float('J3', default=0)
    amount3 = fields.Float('J3', default=0)
    quantity4 = fields.Float('J4', default=0)
    amount4 = fields.Float('J4', default=0)
    quantity5 = fields.Float('J5', default=0)
    amount5 = fields.Float('J5', default=0)
    quantity6 = fields.Float('J6', default=0)
    amount6 = fields.Float('J6', default=0)
    quantity7 = fields.Float('J7', default=0)
    amount7 = fields.Float('J7', default=0)
    quantity8 = fields.Float('J8', default=0)
    amount8 = fields.Float('J8', default=0)
    quantity9 = fields.Float('J9', default=0)
    amount9 = fields.Float('J9', default=0)
    quantity10 = fields.Float('J10', default=0)
    amount10 = fields.Float('J10', default=0)
    quantity11 = fields.Float('J11', default=0)
    amount11 = fields.Float('J11', default=0)
    quantity12 = fields.Float('J12', default=0)
    amount12 = fields.Float('J12', default=0)
    quantity13 = fields.Float('J13', default=0)
    amount13 = fields.Float('J13', default=0)
    quantity14 = fields.Float('J14', default=0)
    amount14 = fields.Float('J14', default=0)
    quantity15 = fields.Float('J15', default=0)
    amount15 = fields.Float('J15', default=0)
    quantity16 = fields.Float('J16', default=0)
    amount16 = fields.Float('J16', default=0)
    quantity17 = fields.Float('J17', default=0)
    amount17 = fields.Float('J17', default=0)
    quantity18 = fields.Float('J18', default=0)
    amount18 = fields.Float('J18', default=0)
    quantity19 = fields.Float('J19', default=0)
    amount19 = fields.Float('J19', default=0)
    quantity20 = fields.Float('J20', default=0)
    amount20 = fields.Float('J20', default=0)
    quantity21 = fields.Float('J21', default=0)
    amount21 = fields.Float('J21', default=0)
    quantity22 = fields.Float('J22', default=0)
    amount22 = fields.Float('J22', default=0)
    quantity23 = fields.Float('J23', default=0)
    amount23 = fields.Float('J23', default=0)
    quantity24 = fields.Float('J24', default=0)
    amount24 = fields.Float('J24', default=0)
    quantity25 = fields.Float('J25', default=0)
    amount25 = fields.Float('J25', default=0)
    quantity26 = fields.Float('J26', default=0)
    amount26 = fields.Float('J26', default=0)
    quantity27 = fields.Float('J27', default=0)
    amount27 = fields.Float('J27', default=0)
    quantity28 = fields.Float('J28', default=0)
    amount28 = fields.Float('J28', default=0)
    quantity29 = fields.Float('J29', default=0)
    amount29 = fields.Float('J29', default=0)
    quantity30 = fields.Float('J30', default=0)
    amount30 = fields.Float('J30', default=0)
    quantity31 = fields.Float('J31', default=0)
    amount31 = fields.Float('J31', default=0)
    quantity = fields.Float('Quantité', readonly=False, store =True, compute='_compute_quantity')
    uom_id = fields.Many2one('uom.uom', 'UdM')
    cost = fields.Float(string='Coût Unitaire')
    amount_total= fields.Float(string='Total', readonly=False, store =True, compute='_compute_amount')
    executed_id = fields.Many2one('building.executed', 'Ececute')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    sequence = fields.Integer(string='Sequence', default=10)
    site_id = fields.Many2one('building.site', string='Affaire',related='assignment_id.site_id', store=True, readonly=True)

    @api.depends('cost', 'quantity')
    def _compute_amount(self):
        for line in self:
            line.amount_total = line.cost*line.quantity

    @api.onchange('assignment_id')
    def _onchange_assignment_id(self):
        if self.assignment_id:
            self.name = self.assignment_id.code
            self.uom_id = self.assignment_id.uom_id.id
            self.cost = self.assignment_id.cost

    @api.depends('quantity1', 'quantity2', 'quantity3', 'quantity4', 'quantity5', 'quantity6', 'quantity7', 'quantity8', 'quantity9', 'quantity10', 'quantity11', 'quantity12', 'quantity13', 'quantity14', 'quantity15', 'quantity16', 'quantity17', 'quantity18', 'quantity19', 'quantity20', 'quantity21', 'quantity22', 'quantity23', 'quantity24', 'quantity25', 'quantity26', 'quantity27', 'quantity28', 'quantity29', 'quantity30', 'quantity31')      
    def _compute_quantity(self):
        for line in self:
            line.quantity = line.quantity1+line.quantity2+line.quantity3+line.quantity4+line.quantity5+line.quantity6+line.quantity7+line.quantity8+line.quantity9+line.quantity10+line.quantity11+line.quantity12+line.quantity13+line.quantity14+line.quantity15+line.quantity16+line.quantity17+line.quantity18+line.quantity19+line.quantity20+line.quantity21+line.quantity22+line.quantity23+line.quantity24+line.quantity25+line.quantity26+line.quantity27+line.quantity28+line.quantity29+line.quantity30+line.quantity31                
            for i in range(1, 32):
                val_amount = getattr(line, 'quantity'+str(i))*line.cost
                setattr(line, 'amount'+str(i), val_amount)

class building_categ_site(models.Model):
    
    _name = 'building.categ.site'
    _description = "Categ Projet"

    code = fields.Char('Code')
    name = fields.Char('Nom')

class building_limit_control_site(models.Model):
    
    _name = 'building.limit.control.site'
    _description = "Seuil de controle"

    categ_site_id = fields.Many2one('building.categ.site', 'Categ Projet')
    rubrique  = fields.Selection([('product', 'Fournitures'), ('conso', 'Consommables'), ('rh', 'Main-d’œuvre'), ('diesel', 'Gasoil'), ('equipment', 'Matériels'), ('rental_equipment', 'Location Externe'), ('prov_serv', 'Prestations de service'), ('indirect_load', 'Charges Indirects')], string="Catégorie", default='')
    prc_limit = fields.Float(string='Seuil(%)')

