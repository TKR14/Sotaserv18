from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_repr
import time
import json
from lxml import etree

MAGIC_COLUMNS = ("id", "create_uid", "create_date", "write_uid", "write_date")


class building_order(models.Model):
    _name = "building.order"
    _description = "BP"
    _order = "id desc"

    @api.depends("order_line.price_subtotal", "order_line.tax_id.amount", "order_line.type_line")
    def _compute_amount(self):
        for order in self:
            amount_tax = 0
            amount_untaxed = 0
            for line in order.order_line:
                taxes = line.tax_id.compute_all(price_unit=line.price_unit, currency=line.company_id.currency_id,
                                                quantity=line.quantity, product=line.product_id,
                                                partner=line.order_id.partner_id)
                amount_untaxed += taxes["total_excluded"]
                amount_tax += sum(dtct_tax.get("amount") for dtct_tax in taxes["taxes"])

            order.amount_tax = amount_tax
            order.amount_untaxed = amount_untaxed
            order.amount_total = order.amount_untaxed + order.amount_tax

    def action_get_bp(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids

        return {
            "name": "Bordereau des Prix",
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "building.order",
            "views": [
                (self.env.ref("building.view_order_tree").id, "tree"),
                (self.env.ref("building.view_order_form").id, "form"),
                
            ],
        }
    def _default_company(self):
        company_id = self._context.get("company_id", self.env.user.company_id.id)
        return company_id

    def _default_currency(self):
        currency_id = self._context.get("currency_id", self.env.user.company_id.currency_id.id)
        return currency_id

    name = fields.Char("Référence", required=False, copy=False, readonly=True, states={"draft": [("readonly", False)]}, default="/")
    origin = fields.Char("Origine du Document")
    site_id = fields.Many2one("building.site", "Affaire", track_visibility="onchange")
    type_marche = fields.Selection(string="Type de marché", related="site_id.type_marche")
    origin_id = fields.Many2one("building.price.calculation", "Origine du Document", track_visibility="onchange")
    ref_tendering = fields.Char("Référence appel d\"offres", required=False)
    ref_project = fields.Char("Référence Marché", required=False)
    # state = fields.Selection([
    #     ("draft", "Brouillon"),
    #     ("sent", "Soumissionné"),
    #     ("lost", "Perdu"),
    #     ("gained", "Gagné"),
    #     ("cancelled", "Annulé"),
    #     ("done", "Terminé"),
    # ], "Statut", readonly=True, index=True, change_default=True, default="draft", track_visibility="always")
    state = fields.Selection([
        ("draft", "Brouillon"),
        ("validated", "Validé "),
        ("approved", "Approuvé "),
        ("reset ", "Remettre "),
    ], "Statut", readonly=True, index=True, change_default=True, default="draft", track_visibility="always")
    create_date = fields.Datetime("Date de création", readonly=False, select=True)
    date_lost = fields.Date("Date de perte du marché", readonly=False, copy=False)
    date_gained = fields.Date("Date de gagne du marché", readonly=False, copy=False)
    user_id = fields.Many2one("res.users", "Commercial", track_visibility="onchange")
    partner_id = fields.Many2one("res.partner", "Client", readonly=False, required=True, change_default=True,
                                 track_visibility="always")
    partner_invoice_id = fields.Many2one("res.partner", "Adresse de Facturation", readonly=False, required=False)
    partner_invoice_address = fields.Char("Adresse de Facturation", copy=False)
    order_line = fields.One2many("building.order.line", "order_id", "Lignes du BP", readonly=False, copy=True)
    invoiced = fields.Boolean(string="Facturé", readonly=True)
    shipped = fields.Boolean(string="Livré", readonly=True)
    note = fields.Text("Description")
    amount_untaxed = fields.Float(string="Montant global Hors Taxes", store=True, readonly=True,
                                  compute="_compute_amount", track_visibility="always")
    amount_tax = fields.Float(string="Montant de la TVA", store=True, readonly=True, compute="_compute_amount")
    amount_total = fields.Float(string="Montant global TVA Comprise", store=True, readonly=True,
                                compute="_compute_amount")
    company_id = fields.Many2one("res.company", "Société", default=_default_company)
    currency_id = fields.Many2one("res.currency", string="Devise", required=True, readonly=True,
                                  default=_default_currency, track_visibility="always")
    product_id = fields.Many2one("product.product", string="Produit", related="order_line.product_id", store=True,
                                 readonly=True)
    commercial_id = fields.Many2one("res.users", string="Commercial", track_visibility="onchange", readonly=False,
                                    required=True)
    origin_dqe_id = fields.Many2one("building.order", "Origine Avenant", readonly=False, required=False)
    amendment = fields.Boolean(string="Avenant ?", readonly=True, default=False)
    is_first_attachment = fields.Boolean(string="Premier Attachment ?", readonly=True, default=True)
    first_attachment_amendment = fields.Boolean(string="Premier Attachment ?", readonly=True)
    is_first_subcontracting = fields.Boolean(string="Premier contrat ?", readonly=True, default=True)
    tax_id = fields.Many2one("account.tax", string="Taxe sur Vente", domain=[("type_tax_use", "=", "sale")], required=True)
    # tender_document_id = fields.Many2one("administrative.tender.document", string="Document", readonly=False,
    # required=False)
    competitors = fields.One2many("building.competitor", "order_id", "Concurents", readonly=False, copy=True)
    opp_id = fields.Many2one("crm.lead", string="AO", readonly=False, required=False, ondelete="cascade",
                             domain=[("is_building_order_created", "=", False), ("stage_id", "not in", ["Gagné", "Abandonnée", "Annulé ou raté"])])

    def action_display_id_order(self):

        ir_model_data = self.env["ir.model.data"].search(
            [("res_id", "=", self.id), ("model", "=", "building.order"), ("module", "=", "__export__")])
        if not ir_model_data:
            ir_model_data = self.env["ir.model.data"].create(
                {"name": "building_order_%s" % self.id, "module": "__export__", "model": "building.order",
                 "res_id": self.id})
        return {
            "name": _("Affichage ID du Bordereau"),
            "view_mode": "tree",
            "res_model": "ir.model.data",
            "type": "ir.actions.act_window",
            "nodestroy": True,
            "domain": [("id", "=", ir_model_data.id)]
        }
    
    def action_display_id_order_read_only(self):

        ir_model_data = self.env["ir.model.data"].search(
            [("res_id", "=", self.id), ("model", "=", "building.order"), ("module", "=", "__export__")])
        if not ir_model_data:
            ir_model_data = self.env["ir.model.data"].create(
                {"name": "building_order_%s" % self.id, "module": "__export__", "model": "building.order",
                 "res_id": self.id})
        return {
            "name": _("Affichage ID du Bordereau"),
            "view_mode": "tree",
            "res_model": "ir.model.data",
            "type": "ir.actions.act_window",
            "nodestroy": True,
            "domain": [("id", "=", ir_model_data.id)],
            "context": { "create": False, "delete": False, "edit": False },
        }

    @api.onchange("opp_id")
    def _onchange_opp_id(self):
        if self.opp_id:
            self.ref_tendering = self.opp_id.num_ao
            self.partner_id = self.opp_id.partner_id.id
            self.commercial_id = self.opp_id.user_id.id

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            partner_invoice_address = False
            partner_invoice_id = ""

            dedicated_salesman = self.partner_id.user_id and self.partner_id.user_id.id or self.env.user.id
            if self.partner_id.child_ids:
                for contact in self.partner_id.child_ids:
                    if contact.type == "invoice":
                        partner_invoice_id = contact.id
                        partner_invoice_address = contact.contact_address
                    else:
                        partner_invoice_id = self.partner_id.id
                        partner_invoice_address = self.partner_id.contact_address
            else:
                partner_invoice_id = self.partner_id.id
                partner_invoice_address = self.partner_id.contact_address

            self.user_id = dedicated_salesman
            self.partner_invoice_address = partner_invoice_address
            self.partner_invoice_id = partner_invoice_id

    def button_dummy(self):
        return True

    def action_sent(self):
        sequ = self.env["ir.sequence"].next_by_code("building.order") or "/"
        self.write({"state": "sent", "name": sequ})
        return True

    def action_lost(self):
        caution_obj = self.env["building.caution"]
        date_lost = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        self.write({"state": "lost", "date_lost": date_lost})
        # if self.tender_document_id :
        #     self.tender_document_id.write({"state":"lost"})
        return True

    def action_gained(self):
        date_gained = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        self.write({"state": "approved", "date_gained": date_gained})

    def action_cancel(self):
        self.write({"state": "cancelled"})
        return True
    # New status
    def action_validate(self):
        if self.state != 'draft':
            raise UserError("Seul le statut Brouillon peut être validé.")
        self.write({'state': 'validated'})

    def action_approve(self):
        if self.state != 'validated':
            raise UserError("Seul un BP validé peut être approuvé.")
        if not self.name or self.name == "/":
            sequ = self.env["ir.sequence"].next_by_code("building.order")
        else:
            sequ = self.name
        self.write({"state": "approved", "name": sequ})

    def action_reset(self):
        attachment = self.env['building.attachment'].search([
            ('order_id', '=', self.id),
            ('type_attachment', '=', 'sale'),
            ('state', '=', 'done')
        ], limit=1)
        
        if attachment:
            raise UserError("Impossible de remettre ce BP en Brouillon car un attachement client est déjà en cours.")
        
        self.write({'state': 'draft'})

    @api.model
    def create(self, vals):
        if "tax_id" in vals.keys() and vals["tax_id"]:
            if vals.get("order_line", []):
                for l in vals.get("order_line", []):
                    l[2]["tax_id"] = [(6, 0, [vals["tax_id"]])]

        stage_won = self.env["crm.stage"].search([("is_won", "=", True)], limit=1).id
        if vals.get("opp_id"):
            self.env["crm.lead"].browse(vals.get("opp_id")).write({"is_building_order_created": True, "stage_id": stage_won})

        return super(building_order, self).create(vals)

    def write(self, vals):
        res = super(building_order, self).write(vals)
        if "tax_id" in vals.keys():
            for order in self:
                for line in order.order_line:
                    line.write({"tax_id": [(6, 0, [vals["tax_id"]])]})

        stage_won = self.env["crm.stage"].search([("is_won", "=", True)], limit=1).id
        if vals.get("opp_id"):
            if self.opp_id:
                self.opp_id.write({"is_building_order_created": False})
            self.env["crm.lead"].browse(vals.get("opp_id")).write({"is_building_order_created": True, "stage_id": stage_won})
        return res

    def unlink(self):
        for order in self:
            if order.site_id and order.site_id.state != "created":
                raise UserError(_("Vous ne pouvez pas supprimer un BP lié à une Affaire en cours."))
            no_bp_stage = self.env["crm.stage"].search([("name", "=", "Manque BP")], limit=1).id
            if order.opp_id:
                order.opp_id.write({"is_building_order_created": False, "stage_id": no_bp_stage})
        return super(building_order, self).unlink()
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        result = super(building_order, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        
        arch = etree.fromstring(result["arch"])
        arch.set("delete", "false")

        if not (self.env.user.has_group('building_plus.sotaserv_directrice_technique') or self.env.user.has_group('building.group_update_crm_bp')) and view_type == 'form':
            arch.set("edit", "false")
            arch.set("create", "false")

        context = self.env.context

        if context.get('no_open_fields'):
            for field in arch.xpath("//field"):
                if field.get('name') in ['commercial_id', 'currency_id', 'partner_id', 'site_id', 'opp_id']:
                    field.set('readonly', '1')
                    field.set('options', '{"no_open": true}')

        result["arch"] = etree.tostring(arch, encoding='unicode')

        return result
    

class building_competitor(models.Model):
    _name = "building.competitor"
    _description = "competitors"

    competitor = fields.Char("Concurent", required=False)
    price_competitor = fields.Float(string="Prix du Concurent")
    order_id = fields.Many2one("building.order", "Référence Bordereau", required=True, ondelete="cascade",
                               readonly=True)


class building_order_line(models.Model):
    _name = "building.order.line"
    _description = "Lignes de Bordereau"
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = "id"

    def _default_quantity(self):
        return self.quantity

    @api.depends("price_unit", "tax_id", "quantity", "product_id", "order_id.partner_id", "company_id")
    def _compute_price(self):
        for line in self:
            price = line.price_unit
            taxes = line.tax_id.compute_all(price_unit=price, currency=line.company_id.currency_id,
                                            quantity=line.quantity, product=line.product_id,
                                            partner=line.order_id.partner_id)
            line.price_subtotal = taxes["total_included"]

    order_id = fields.Many2one("building.order", "Référence Bordereau", required=True, ondelete="cascade",
                               readonly=False)
    name = fields.Text("Description", required=False, readonly=False)
    product_id = fields.Many2one("product.product", "Produit", domain=[("sale_ok", "=", True)], change_default=True,
                                 readonly=False, ondelete="restrict")
    price_unit = fields.Float(string="Prix Unitaire", required=True)
    price_subtotal = fields.Float(string="Montant", store=True, readonly=True, compute="_compute_price")
    tax_id = fields.Many2many("account.tax", "building_order_line_tax", "order_line_id", "tax_id", "Taxes",readonly=False, compute="_compute_tax_id")
    # tax_id = fields.Many2one("account.tax", compute="_compute_tax_id", store=True)
    quantity = fields.Float(string="Quantité", required=True, default=1)
    product_uom = fields.Many2one("uom.uom", "Unité de mésure ", required=False, readonly=False)
    salesman_id = fields.Many2one("res.users", string="Commercial", related="order_id.user_id", store=True,
                                  readonly=True)
    order_partner_id = fields.Many2one("res.partner", string="Client", related="order_id.partner_id", store=True,
                                       readonly=True)
    company_id = fields.Many2one("res.company", string="Société", related="order_id.company_id", store=True,
                                 readonly=True)
    code = fields.Char("Code", required=False)
    weighted_average_cost = fields.Float("Cout moyen pondéré", digits=(16, 3), readonly=True)
    calculated_sales_price = fields.Float("Prix de vente calculé", digits=(16, 3), readonly=True)
    type_line = fields.Selection([("chapter", "Chapitre"), ("component", "Composant"), ("price", "Prix")],
                                 string="Type de la ligne", required=False)
    origin_id = fields.Many2one("building.price.calculation.line", "Réf ligne BP")
    parent_path = fields.Char(index=True)
    parent_id = fields.Many2one("building.order.line", "Parent")
    child_ids = fields.One2many("building.order.line", "parent_id", "Childs")
    # analytic_id = fields.Many2one("account.analytic.account", "Compte analytique")
    display_type = fields.Selection([
        ("line_chapter", "Chapitre"),
        ("line_sub_chapter", "Sous Chapitre"),
        ("line_section", "Section"),
        ("line_note", "Note")], default=False)
    sequence = fields.Integer(string="Sequence", default=10)

    @api.depends("order_id")
    def _compute_tax_id(self):
        for record in self:
            record.tax_id = record.order_id.tax_id

    @api.onchange("product_id")
    def onchange_product_id(self):
        if self.product_id:
            self.tax_id = self.env["account.fiscal.position"].map_tax(self.product_id.taxes_id)
            self.product_uom = self.product_id.uom_id.id
            self.price_unit = self.product_id.list_price

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        result = super(building_order_line, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        
        arch = etree.fromstring(result["arch"])
        arch.set("delete", "false")
        result["arch"] = etree.tostring(arch)

        return result
        