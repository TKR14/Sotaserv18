from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError

from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import json
from lxml import etree
from collections import Counter

class purchase_price_comparison(models.Model):
    
    _name = 'purchase.price.comparison'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Comparaison des offres de prix"
    _rec_name = "purchase_order_code"

    name =  fields.Char('Nom', size=150, tracking=True)
    purchase_order_code = fields.Char("Référence", tracking=True)
    date_comparison =  fields.Date('Date de création', tracking=True)
    date_decision =  fields.Date('Date de decision', tracking=True)
    state = fields.Selection(string="Statut", default="draft", tracking=True, selection=[
        ("draft", "Brouillon"),
        ("dg_validation", "Validation DG"),
        ("purchase_validation", "Validée"),
        ("po_canceled", "BC annulé")
    ])
    po_ids = fields.One2many('purchase.order', 'price_comparison_id', 'Demandes', readonly=False, copy=True)
    po_lines = fields.One2many('purchase.order.line', 'price_comparison_id', 'Lignes', readonly=False, copy=True)
    recommendations = fields.One2many('purchase.price.comparison.recommendation', 'price_comparison_id', 'recommendations', readonly=False, copy=True)
    year =  fields.Char('Année', size=4)
    order_id = fields.Many2one('purchase.order', 'Offre Sélectionné')
    partners = fields.Many2many('res.partner', string='Fournisseurs', compute='_compute_partners')
    dg_validated = fields.Boolean("Validé par DG?", default=False)
    action_buyer_validated_visible = fields.Boolean(compute="_compute_visiblity_fields")
    reason = fields.Char(string="Motif", tracking=True)

    @api.depends("state", "dg_validated")
    def _compute_visiblity_fields(self):
        if self.state == "draft" or self.state == "dg_validation" and self.dg_validated:
            self.action_buyer_validated_visible = True
        else:
            self.action_buyer_validated_visible = False

    @api.depends('po_lines')
    def _compute_partners(self):
        list_partners = []
        for line in self.po_lines:
            if line.partner_id.id and line.partner_id.id not in list_partners:
                list_partners.append(line.partner_id.id)
        self.partners = list_partners

    def get_lines(self):
        partners = self.get_partners()
        lines = {}
        for line in self.po_lines:
            if line.product_id.id not in lines:
                lines[line.product_id.id] = {}
                lines[line.product_id.id]['name'] = line.product_id.name
                lines[line.product_id.id]['qty'] = line.product_qty
                lines[line.product_id.id]['note'] = line.note
                for partner_id in partners:
                    lines[line.product_id.id][partner_id] = 'PAS DE RETOUR'
            lines[line.product_id.id][line.partner_id.id] = line.price_unit
        return lines

    def get_partners(self):
        partners = {}
        for line in self.po_lines:
            if line.partner_id.id not in partners:
                partners[line.partner_id.id] = {}
            partners[line.partner_id.id] = line.partner_id.name
        return partners
    
    def get_comment(self):
        partners = self.get_partners()
        dict_comment = {}
        for partner_id in partners:
            if partner_id not in dict_comment:
                dict_comment[partner_id] = {}
            order = self.env['purchase.order'].search([('partner_id', '=', partner_id), ('state', '=', 'draft'), ('price_comparison_id', '=', self.id)])
            dict_comment[partner_id]['total'] = order.amount_untaxed
            dict_comment[partner_id]['payment'] = '-'
            dict_comment[partner_id]['delivery'] = '-'
            dict_comment[partner_id]['guaranty'] = '-'
            dict_comment[partner_id]['available'] = '-'
            dict_comment[partner_id]['delay'] = '-'
            dict_comment[partner_id]['validity'] = '-'

            if order.payment_method_id:
                dict_comment[partner_id]['payment'] = order.payment_method_id.name
                if order.payment_term_id:
                    dict_comment[partner_id]['payment'] = dict_comment[partner_id]['payment'] + 'a ' + order.payment_term_id.name
            else:
                if order.payment_term_id:
                    dict_comment[partner_id]['payment'] = order.payment_term_id.name
            if order.delivery_method:
                dict_comment[partner_id]['delivery'] = order.delivery_method
            if order.guaranty_str:
                dict_comment[partner_id]['guaranty'] = order.guaranty_str
            if order.available_str:
                dict_comment[partner_id]['available'] = order.available_str
            if order.delivery_time:
                dict_comment[partner_id]['delay'] = order.delivery_time
            if order.offer_validity:
                dict_comment[partner_id]['validity'] = order.offer_validity
        return dict_comment

    def get_recommendations(self):
        partners = self.get_partners()
        recommendations = {}
        for rec in self.recommendations:
            if rec.name not in recommendations:
                recommendations[rec.name] = {}
                for partner_id in partners:
                    recommendations[rec.name][partner_id] = '-'
            recommendations[rec.name][rec.partner_id.id] = rec.description
        return recommendations

    def action_purchase_cancel(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Assistant d'Annulation",
            "res_model": "cancellation.reason",
            "view_mode": "form",
            "target": "new",
        }

    def action_purchase_validated(self):
        if 0 in self.po_lines.mapped("price_unit"):
            raise UserError("Assurez-vous de saisir les prix unitaires des lignes.")

        if not bool(self.order_id):
            raise UserError("Merci de sélectionner une offre.")

        # Cancel all price requests other than the selected offer
        for order in self.po_ids:
            if order.id != self.order_id.id:
                order.button_cancel()

        self.state = "purchase_validation"
        self.date_decision = datetime.today()
        self.order_id.button_validate()


class purchase_price_comparison_recommendation(models.Model):
    
    _name = 'purchase.price.comparison.recommendation'
    _description = "recommendation decision"

    @api.depends('price_comparison_id')
    def _domain_partner(self):
        price_comparison = None
        if self._context.get('params', False):
            price_comparison = self.env['purchase.price.comparison'].browse(self._context.get('params', False)['id'])
        else:
            price_comparison = self.price_comparison_id
        partners = price_comparison.get_partners()
        list_partners = []
        for part in partners:
            list_partners.append(part)
        domain = [('id', 'in', list_partners)]
        return domain

    name =  fields.Char('Nom')
    price_comparison_id = fields.Many2one('purchase.price.comparison', 'Comparaison')
    partner_id = fields.Many2one('res.partner', 'Fornisseur')
    description = fields.Char('Description')


class purchase_order(models.Model):
    
    _inherit = 'purchase.order'

    delivery_method =  fields.Char('Mode de livraison')
    guaranty =  fields.Selection([('yes','Oui'),('no','Non')], string="Garantie",default='')
    guaranty_str =  fields.Char('Garantie')
    delivery_time = fields.Char('Délai de livraison')
    available =  fields.Selection([('yes','Oui'),('no','Non')], string="Disponibilité",default='')
    available_str =  fields.Char('Disponibilité')
    offer_validity = fields.Char('Validité de l''offre')
    price_comparison_id = fields.Many2one('purchase.price.comparison', 'Comparaison')
    payment_method_id = fields.Many2one('account.payment.method', 'Moyen de paiement')

    contact_id = fields.Many2one('hr.employee', 'Contact')
    commercial_id = fields.Many2one('res.partner', 'Commercial')

    @api.onchange('partner_id')
    def _commercial_id_domain(self):
        return {"domain": {"commercial_id": [("id", "in", self.partner_id.child_ids.ids)]}}

    def report_purchase_order(self):
        lines_count = len(self.order_line)
        first_page = 37
        line_per_page = 51

        pages = math.ceil((lines_count - first_page) / line_per_page)
        add_page = False
        add_second_page = False
        if pages > 0:
            if (lines_count - first_page) % line_per_page > 28 or (lines_count - first_page) % line_per_page == 0:
                add_page = True
                pages += 1
        else:
            if lines_count > 14:
                add_second_page = True

        data = {
            "name": self.name,
            "date_approve": self.date_approve and self.date_approve.strftime('%d/%m/%Y') or False,
            "date_planned": self.date_planned and self.date_planned.strftime('%d/%m/%Y') or False,

            "contact_name": self.contact_id.name,
            "contact_work_phone": self.contact_id.work_phone,
            "contact_work_email": self.contact_id.work_email,
            "site_name": self.site_id.name,

            "partner_name": self.partner_id.name,
            "commercial_name": self.commercial_id.name,
            "commercial_address": self.commercial_id.contact_address,
            "commercial_phone": self.commercial_id.phone,
            "commercial_email": self.commercial_id.email,
            "partner_ref": self.partner_ref,

            "lines": [],

            "amount_untaxed": self.amount_untaxed,
            "amount_tax": self.amount_tax,
            "amount_total": self.amount_total,

            "lines_count": lines_count,
            "first_page": first_page,
            "line_per_page": line_per_page,
            "pages": pages,
            "add_page": add_page,
            "add_second_page": add_second_page,
        }

        for line in self.order_line:
            data["lines"].append({
                "default_code": line.product_id.default_code,
                "product": line.product_id.name,
                "name": line.name,
                "uom": line.product_uom.name,
                "quantity": line.product_qty,
                "price_unit": line.price_unit,
                "price_subtotal": line.price_subtotal,
            })

        return data


class purchase_order_line(models.Model):
    
    _inherit = 'purchase.order.line'
    _order = 'product_id desc, partner_id desc'

    is_available =  fields.Selection([('yes','Oui'),('no','Non')], string="Disponible ?",default='')
    note = fields.Char('Remarque')
    with_technical_sheet = fields.Selection([('yes','Oui'),('no','Non')], string="Fiche technique disponible ?",default='')
    price_comparison_id = fields.Many2one('purchase.price.comparison', 'Comparaison')
    regime_imposition = fields.Selection(
        related='order_id.partner_id.regime_imposition',
    )


class stock_picking(models.Model):
    
    _inherit = 'stock.picking'

    is_compliant =  fields.Selection([('compliant','Conforme'),('notcompliant','Non Conforme')], string="Conformité", default='compliant', compute='_compute_compliant', store=True)
    picking_supplier_numer =  fields.Char("N° BL")
    certification_state = fields.Selection([('certification', 'Attente Certification'), ('certified', 'Certifié'), ('invoiced', 'Facturé')], default="certification")

    def open_cancellation_reason_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Assistant de Retour",
            "res_model": "cancellation.reason",
            "view_mode": "form",
            "target": "new",
        }

    def action_return_certification(self, reason=None):
        self.write({"certification_state": "certification"})
        body = f"""
        <ul>
          <li>Motif de Retour: {reason}</li>
        <ul/>
        """
        self.message_post(body=body)
        
    def action_return_cg(self, reason=None):
        stock_id = self
        stock_moves = self.env["stock.move"].search([("picking_id", "=", stock_id.id)])
        stock_move_lines = self.env["stock.move.line"].search([("picking_id", "=", stock_id.id)])
        
        stock_id.sudo().write({"state":"assigned", "amount_advance_deduction": 0,})
        stock_id.sudo().write({"state":"assigned"})
        stock_moves.sudo().write({"state":"assigned"})
        stock_move_lines.sudo().write({"state":"assigned"})
        self.purchase_id.sudo().write({"state": "purchase"})
        self.purchase_id.sudo().button_done()

        body = f"""
        <ul>
          <li>Motif de Retour: {reason}</li>
        <ul/>
        """
        self.message_post(body=body)

    def action_view_purchase_order(self):    
        if self.origin:
            action = self.env.ref('purchase.purchase_rfq').read()[0]
            view_id = 'account_plus.purchase_order_form_readonly'
            action['views'] = [(self.env.ref(view_id).id, 'form')]
            action['res_id'] = self.env["purchase.order"].search(['|', ("name", "=", self.origin), ('pr_ref', '=', self.origin)], limit=1).id
            return action
    
    @api.depends('move_ids_without_package.is_compliant')
    def _compute_compliant(self):
        is_compliant = 'compliant'
        for pick in self:
            for mv in pick.move_ids_without_package:
                if mv.is_compliant == 'notcompliant':
                    is_compliant = 'notcompliant'
            pick.is_compliant = is_compliant

class StockMove(models.Model):
    _inherit = "stock.move"

    is_compliant =  fields.Selection([("compliant", "Conforme"), ("notcompliant", "Non Conforme")], string="Conformité", default="compliant")


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    to_reject = fields.Boolean(compute="_compute_to_reject")
    is_siege_pr = fields.Boolean(compute="_compute_is_siege_pr")

    @api.depends("site_id")
    def _compute_is_siege_pr(self):
        for pr in self:
            if pr.site_id.number == "000":
                pr.is_siege_pr = True
            else:
                pr.is_siege_pr = False

    @api.depends("state")
    def _compute_to_reject(self):
        ceo_ids = self.env["hr.employee"].sudo().search([("job_title", "=", "DIRECTEUR GENERAL")]).mapped("user_id").ids
        for purchase_request in self:
            to_reject = False
            if purchase_request.state == "to_approve" or self.env.user.id in ceo_ids and purchase_request.state == "approved" and all(line.state == "approved" for record in purchase_request for line in record.line_ids):
                to_reject = True
            purchase_request.to_reject = to_reject

    @api.model
    def default_get(self, fields):
        result = super(PurchaseRequest, self).default_get(fields)

        if self._context.get("is_siege"):
            building_site = self.env["building.site"].sudo()

            siege_pr = building_site.search([("number", "=", "000")], limit=1)
            siege_fg = building_site.search([("number", "=", "001")], limit=1)
            siege_lg = building_site.search([("number", "=", "002")], limit=1)

            if not siege_pr:
                siege_pr = building_site.create({
                    "name": "SIÈGE",
                    "number": "000",
                })
                siege_pr._create_warehouse()

            if not siege_fg:
                siege_fg = building_site.create({
                    "name": "FRAIS GÉNÉRAUX",
                    "number": "001",
                })
                siege_fg._create_warehouse()

            if not siege_lg:
                siege_lg = building_site.create({
                    "name": "LOGISTIQUE",
                    "number": "002",
                })
                siege_lg._create_warehouse()

            if self._context.get("is_siege_pr"):
                result["site_id"] = siege_pr.id
            if self._context.get("is_siege_fg"):
                result["site_id"] = siege_fg.id
            if self._context.get("is_siege_lg"):
                result["site_id"] = siege_lg.id

        return result

    def _site_id_domain(self):
        approved_needs = self.env["building.purchase.need"].search([("state", "=", "approuved")])
        site_ids = approved_needs.mapped("site_id").filtered(lambda site: site.state == "open").ids

        if self._context.get("group"):
            profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", self._context.get("group"))])
            user_site_ids = profile_ids.mapped("site_id").ids
            site_ids = approved_needs.mapped("site_id").filtered(lambda site: site.state == "open" and site.id in user_site_ids).ids
        elif self._context.get("is_siege"):
            user = self.env.user

            codes = []
            if user.has_group('purchase_igaser.group_siege_pr'):
                codes.append("000")

            if user.has_group('purchase_igaser.group_siege_fg'):
                codes.append("001")

            if user.has_group('purchase_igaser.group_siege_lg'):
                codes.append("002")

            return [("number", "in", codes)]

        return [("id", "in", site_ids)]

    def _state_selection(self):
        return [("draft", "Brouillon"), ("to_approve", "Validée"), ("approved", "Approuvée"), ("done", "Terminée"), ("rejected", "Rejetée"), ("canceled", "Annulée")]
    state = fields.Selection(selection=_state_selection, string="Statut", default="draft", tracking=True)
    state_write_uids = fields.Char("Statut dernière màj. par")
    site_id = fields.Many2one("building.site", string="Affaire", domain=_site_id_domain)
    order_id = fields.Many2one("building.order", string="Bordereau des prix")
    vehicle_id =  fields.Many2one("fleet.vehicle", string="STE")
    need_product_ids = fields.Many2many("product.product", string="Product")
    note = fields.Text("Note", tracking=True)
    date_approval = fields.Date(string="Date d'approbation", readonly=True)

    def _check_cancel(self):
        if any(state != "canceled" for state in self.line_ids.mapped("state")):
            return
        self.state = "canceled"

    @api.onchange("site_id")
    def _onchange_site_id(self):
        self.line_ids = [(3, line.id) for line in self.line_ids]
        self._compute_need_product_ids()
        if self.site_id:
            self.picking_type_id = self.site_id.warehouse_id.in_type_id.id

    @api.onchange("line_ids")
    def _compute_need_product_ids(self):
        domain = []
        if self.site_id and not self._context.get("is_siege"):
            def _available_quantity(line):
                requested_lines = self.env["purchase.request.line"].search([("site_id", "=", self.site_id.id), ("product_id", "=", line.product_id.id), ("state", "!=", "canceled")])
                requested_quantity = sum(requested_lines.mapped("product_qty"))
                available_quantity = line.quantity - requested_quantity
                return available_quantity > 0 and line.price_unit > 0

            def _available_products(lines):
                return [line.product_id.id for line in lines if _available_quantity(line)]

            need = self.env["building.purchase.need"].search([("site_id", "=", self.site_id.id)])
            need_line_ids = _available_products(need.line_ids)
            need_service_provision_ids = _available_products(need.service_provision_ids)
            need_mini_equipment_ids = _available_products(need.mini_equipment_ids)
            fuel_ids = _available_products(need.fuel_ids)

            include = need_line_ids + need_service_provision_ids + need_mini_equipment_ids + fuel_ids
            exclude = self.line_ids.mapped("product_id").ids

            domain.append(("id", "in", [id for id in include if id not in exclude]))
        elif self.site_id and self._context.get("is_siege"):
            exclude = self.line_ids.mapped("product_id").ids
            domain.append(("id", "not in", exclude))
        self.need_product_ids = self.env["product.product"].search(domain)

    def button_draft(self):
        button = super(PurchaseRequest, self).button_draft()
        self.note = ""
        self.state_write_uids = ""
        self.line_ids.state = "draft"
        return button

    def button_to_approve(self):
        button = super(PurchaseRequest, self).button_to_approve()
        self.state_write_uids = f"{self.env.user.id},"
        self.line_ids.state = "validated"
        return button

    def _check_step_2(self, button):
        uids = self.state_write_uids.split(",")
        user = self.env["res.users"].browse(int(uids[0]))
        approval_chain_line = self.env["approval.chain.line"].search([(f"step_1", "=", user.id), ("parent_id.model_id", "=", self._name)])
        allowed_uids = approval_chain_line.mapped("step_2")

        if self.env.user not in allowed_uids:
            raise ValidationError(f"Vous n'êtes pas autorisé à {button} cette demande.\n\nAucune chaîne d'approbation ne ressemble à celle-ci:\n{user.name} ─ Vous")

    def button_approved(self):
        button = super(PurchaseRequest, self).button_approved()
        self._check_step_2("approuver")
        self.state_write_uids += f"{self.env.user.id},"
        self.line_ids.state = "approved"
        self.date_approval = datetime.today()
        if self.site_id.number == "000":
            self.line_ids.state = "purchase_validated"
        return button

    def button_rejected(self):
        button = super(PurchaseRequest, self).button_rejected()
        self._check_step_2("rejeter")
        self.state_write_uids += f"{self.env.user.id},"
        self.line_ids.state = "rejected"
        return button
    
    def _action_note(self, state):
        return {
            "name": "Motif du refus",
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "view_mode": "form",
            "res_id": self.id,
            "views": [(self.env.ref("purchase_igaser.purchase_request_view_form_note").id, "form")],
            "target": "new",
            "context": {f"{state}": True},
        }
    
    def button_reject(self):
        return self._action_note("rejected")
    
    def button_note(self):
        return self._action_note("draft")

    @api.constrains("line_ids")
    def _constrains_product_qty(self):
        if not self._context.get("is_siege") and not self._context.get("is_logistic"):
            message = "Assurez-vous que la quantité demandée soit supérieure à 0 et inférieure à la celle disponible.\n\n"
            lines = []
            for line in self.line_ids:
                # raise Exception(line.product_qty, line.available_quantity, line.available_quantity - line.product_qty)
                if line.available_quantity < 0 or line.product_qty == 0:
                    lines.append(line.product_id.name)
            if len(lines) > 0:
                if len(lines) > 1:
                    message += "Lignes:"
                    for line in lines:
                        message += f"\n\t- {line}"
                else:
                    message += f"Ligne: {lines[0]}"
                raise UserError(message)

    def action_view_purchase_request_line(self):
        return {
            "name": "Lignes de demande d'achat",
            "type": "ir.actions.act_window",
            "view_mode": "list",
            "res_model": "purchase.request.line",
            "views": [(self.env.ref("purchase_igaser.purchase_request_line_view_tree").id, "list")],
            "domain": [("id", "in", self.line_ids.ids)],
            "context": {
                "create": False,
                "edit": False,
                "delete": False,
            }
        }


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    available_quantity = fields.Float("Quantité disponible", compute="_compute_available_quantity")
    site_id = fields.Many2one("building.site", string="Affaire", related="request_id.site_id", store=True)
    product_category_id = fields.Many2one("product.category", string="Catégorie d'article", related="product_id.categ_id", store=True)
    assigned_to = fields.Many2one(compute="_compute_assigned_to")
    state = fields.Selection(
        selection=[
            ("draft", "Brouillon"),
            ("validated", "Demande Validée"),
            ("approved", "Demande Approuvée"),
            ("rejected", "Demande Rejetée"),

            ("purchase_validated", "Achat Validé"),
            ("order_established", "Commande Établie"),
            ("order_done", "Commande Clôturée"),

            ("transfer_validated", "Transfert Validé"),
            ("transfer_established", "Transfert Établi"),
            ("transfer_done", "Transfert Clôturé"),

            ("canceled", "Annulée"),
            ("trash", "Retirée"),

            ("closed", "Clôturée"),
            ("receiving", "Réception en Cours"),
            ("received", "Réception Faite"),
            ("no_reception", "Pas de Réception"),
            ("invoiced", "Facture Établie"),
            ("invoice_paid", "Facture Payée"),
            ("price_request_established", "Demande de Prix Établie"),
        ],
        string="Statut",
        default="draft",
        help="""Brouillon > Validée > Approuvée > Achat Validé ou Transfert Validé
1. Achat Validé > Demande de Prix Établie > Commande Établie > Réception en Cours > Réception Faite ou Pas de Réception
2. Transfert Validé > Transfert Établi > Transfert Clôturé"""
    )
    cost = fields.Float(string="Coût", related="product_id.reference_price")
    has_pr = fields.Boolean("A une PD", default=False)
    date_approval = fields.Date(string="Date d'approbation", readonly=True, related="request_id.date_approval")

    def _get_need_line(self):
        filter = lambda line: line.product_id.id == self.product_id.id
        need = self.env["building.purchase.need"].search([("site_id", "=", self.site_id.id)], limit=1)  
        need_line = need.line_ids.filtered(filter)

        if not need_line:
            need_line = need.service_provision_ids.filtered(filter)
        if not need_line:
            need_line = need.mini_equipment_ids.filtered(filter)
        if not need_line:
            need_line = need.fuel_ids.filtered(filter)

        return need_line

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if not self.product_id:
            self.name = None
            self.product_qty = 0
            self.product_uom_id = None

    @api.onchange("product_qty")
    def _onchange_product_qty(self):
        self.estimated_cost = 0
        if self.product_id:
            need_line = self._get_need_line()
            self.estimated_cost = self.product_qty * need_line.price_unit

    @api.depends("product_id")
    def _compute_available_quantity(self):
        for line in self:
            line.available_quantity = 0
            if line.product_id:
                need_line = line._get_need_line()
                if len(need_line):
                    line.available_quantity = need_line[0].available_quantity

    @api.depends("product_category_id", "product_category_id.buyer_ids", "product_category_id.buyer_ids.is_supervisor")
    def _compute_assigned_to(self):
        for line in self:
            buyers = line.product_category_id.buyer_ids.filtered(lambda buyer: not buyer.is_supervisor)
            buyer_id = buyers and buyers[0].user_id.id or False
            if not buyer_id:
                buyers = line.product_category_id.secondary_buyer_ids
                buyer_id = buyers and buyers[0].id or False
            line.assigned_to = buyer_id


class ResGroups(models.Model):
    _inherit = "res.groups"

    def get_access_rights(self):
        model_access = ""
        for access in self.model_access:
            id = f"sotaserv_chef_projet_{'_'.join(access.model_id.model.split('.'))}"
            name = access.model_id.model
            group = "building_plus.sotaserv_chef_projet"
            model_id = access.model_id.get_xml_id()[access.model_id.id]
            perm_read = access.perm_read and 1 or 0
            perm_write = access.perm_write and 1 or 0
            perm_create = access.perm_create and 1 or 0
            perm_unlink = access.perm_unlink and 1 or 0

            model_access += f"{id},{name},{group},{model_id},{perm_read},{perm_write},{perm_create},{perm_unlink}\n"

        raise UserError(model_access)


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        result = super(ProductProduct, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if view_type == "list":
            doc = etree.XML(result["arch"])
            for field in doc.xpath("//field"):
                field_name = field.attrib.get("name")
                if field_name not in ["name", "uom_id"]:
                    field.getparent().remove(field)     
            result["arch"] = etree.tostring(doc)

        return result


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.depends(
        'product_variant_ids',
        'product_variant_ids.stock_move_ids.product_qty',
        'product_variant_ids.stock_move_ids.state',
    )
    @api.depends_context('company', 'location', 'warehouse')
    def _compute_quantities(self):
        res = self._compute_quantities_dict()
        for template in self:
            quants = template.action_open_quants()
            quants = self.env["stock.quant"].search(quants["domain"])
            qty_available = sum(quants.filtered(lambda q: bool(q.company_id)).mapped("quantity"))
            
            template.qty_available = qty_available
            template.virtual_available = res[template.id]['virtual_available']
            template.incoming_qty = res[template.id]['incoming_qty']
            template.outgoing_qty = res[template.id]['outgoing_qty']