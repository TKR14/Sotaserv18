from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, datetime
import json
from lxml import etree


class CrmLead(models.Model):
    _inherit = "crm.lead"

    @api.model
    @api.depends("stage_id")
    def _compute_state_by_stage(self):
        for lead in self:
            state_by_stage = "unset"
            if lead.stage_id.is_lost:
                state_by_stage = "is_lost"
            if lead.stage_id.is_won:
                state_by_stage = "is_won"
            if lead.stage_id.is_sent_to_client:
                state_by_stage = "is_sent_to_client"
            if lead.stage_id.is_cancel:
                state_by_stage = "is_cancel"
            lead.state_by_stage = state_by_stage

    owner = fields.Char("Maître d'ouvrage")
    city = fields.Char("Ville")
    num_ao = fields.Char("Numéro d'appel d'Offre")
    date_open_ao = fields.Datetime("Date d'ouverture")
    deadline = fields.Datetime("Date Limite")
    delai = fields.Integer("Delai")
    deposit_envelopes = fields.Selection([("electronique", "Électronique"), ("physical", "Physique")],
                                         string="Depot des plis", required=False, default="")
    is_requested_class = fields.Boolean("Classe demandée ?")
    # requested_class = fields.Selection([("1", "1"), ("2", "2"), ("3", "3"), ("4", "3"), ("5", "3")], index=True,
    # required=True, tracking=15, default=lambda self: "1")
    requested_class_ids = fields.One2many("crm.lead.class.line", "opp_id", string="Class", copy=True)
    is_qualification_requested = fields.Boolean("Qualification demandée ?")
    # qualification_requested = fields.Many2one("crm.lead.qualification", string="Qualification demandée")
    qualification_requested_ids = fields.One2many("crm.lead.qualification.line", "opp_id", string="Qualification", copy=True)
    site_visit = fields.Boolean("Visite de lieux")
    date_site_visit = fields.Datetime("Date visite de lieux")
    is_samples = fields.Boolean("Échantillon")
    date_samples = fields.Date("Date des échantillons")
    date_sales_department = fields.Date("Date de remise à la Direction Commerciale")
    date_office_study = fields.Date("Date de remise de l'offre au BET")
    date_response_prev_office_study = fields.Date("Date prévu de réponse sur l'offre (1) pour BET")
    date_response_reel_office_study = fields.Date("Date réelle de réponse sur  l'offre (2) pour BET")
    date_dg = fields.Date("Date d'envoie de l'Etude au DG")
    date_response_dg = fields.Date("Date de Réponse du DG")
    date_submission = fields.Date("Date de Soumission")
    is_deposit = fields.Boolean("Avec Caution ?")
    dg_decision = fields.Char("Décision DG")
    caution_ids = fields.One2many("account.caution", "opp_id", string="Cautions", copy=True)
    is_building_order_created = fields.Boolean("BP cree ?", default=False)
    is_purchase_need_created = fields.Boolean("Liste de besoins cree ?", default=False)
    typ_marche = fields.Selection([("public", "Public"), ("private", "Privé")], string="Type Marché", required=False,
                                  default="")
    state_by_stage = fields.Selection([("unset", "Non défini"), ("is_sent_to_client", "Envoyé Client"),
                                       ("is_won", "Gagné"), ("is_lost", "Perdu"), ("is_cancel", "Annulé")],
                                      string="Status", required=False,
                                      store=True, compute="_compute_state_by_stage")
    stage_ids = fields.Many2many("crm.stage", compute="_compute_stage_ids")
    user_ids = fields.Many2many("res.users", string="Chargés d'affaire", required=False,
                                default=lambda self: self.env.user)
    is_validate_visible = fields.Boolean("Valider visible?", default=False, compute="_compute_visibility")
    is_return_visible = fields.Boolean("Remettre visible?", default=False, compute="_compute_visibility")
    is_convert_to_project = fields.Boolean("Convertir en Affaire?", default=False,
                                           compute="_compute_is_convert_to_project")
    nav_controlls = fields.Boolean("Controles de navigation?", compute="_compute_nav_controlls")
    reason = fields.Text("Motif", required=True, tracking=True)

    give_up = fields.Boolean(string="Abandonnée", default=False)

    def action_get_pipeline(self, group):
        profile_ids = self.env["building.profile.assignment"].search([
            ("user_id", "=", self.env.user.id),
            ("group_id.name", "=", group)
        ])
        site_ids = profile_ids.mapped("site_id").ids

        return {
            "name": "Pipeline",
            "type": "ir.actions.act_window",
            "view_mode": "kanban,tree,form",
            "res_model": "crm.lead",
            "views": [
                (self.env.ref("crm.crm_case_kanban_view_leads").id, "kanban"),
                (self.env.ref("crm.crm_case_tree_view_oppor").id, "list"),
                (self.env.ref("crm.crm_lead_view_form").id, "form"),
                (self.env.ref("crm.crm_case_calendar_view_leads").id, "calendar"),
                (self.env.ref("crm.crm_lead_view_pivot").id, "pivot"),
                (self.env.ref("crm.crm_lead_view_graph").id, "graph"),
                (self.env.ref("crm.crm_lead_view_activity").id, "activity"),
            ],
            "context": {
                "create": True,
                "edit": True,
                "delete": False,
            },
        }
    def _compute_nav_controlls(self):
        for lead in self:
            lead.nav_controlls = True
            if lead.is_building_order_created and lead.is_purchase_need_created and lead.stage_id.is_won or self.stage_id.name == "Manque BP":
                lead.nav_controlls = False

    def _compute_is_convert_to_project(self):
        for lead in self:
            site_id = self.env["building.site"].search([("opp_id", "=", lead.id)])
            if lead.stage_id.is_won and lead.is_building_order_created and not site_id:
                lead.is_convert_to_project = True
            else:
                lead.is_convert_to_project = False

    def _compute_visibility(self):
        for lead in self:
            is_validate_visible = False
            is_return_visible = False

            if lead.stage_id.sequence > 0:
                is_return_visible = True
            if lead.stage_id.sequence < len(self.env["crm.stage"].search([])) - 1:
                is_validate_visible = True

            if lead.state_by_stage == "is_sent_to_client":
                is_validate_visible = False

            if lead.state_by_stage == "is_lost":
                is_validate_visible = False

            if lead.state_by_stage == "is_cancel":
                is_return_visible = False

            lead.is_validate_visible = is_validate_visible
            lead.is_return_visible = is_return_visible

    def _compute_stage_ids(self):
        for lead in self:
            lead.stage_ids = self.env["crm.stage"].search(["|", "&",("team_id", "=", self.team_id.id), ("team_id", "=", False), ("name", "not in", ["Manque BP"])])

    def action_set_won_rainbowman(self):
        res = super(CrmLead, self).action_set_won_rainbowman()
        for caution in self.caution_ids:
            if caution.type_caution == "tender_caution":
                caution.state_caution = "released"
                caution.caution_provisional_recovery_date = datetime.now().date()
        # record_trc = {
        #     "partner_id": self.partner_id.id,
        #     "name": self.name,
        #     "duration_work": self.delai
        # }
        # self.env["crm.trc"].create(record_trc)
        order = self.env["building.order"].search([("opp_id", "=", self.id), ("state", "=", "sent")])
        if order:
            order.action_gained()
        return res

    def action_set_lost(self, **additional_values):
        res = super(CrmLead, self).action_set_lost(**additional_values)
        for caution in self.caution_ids:
            if caution.type_caution == "tender_caution":
                caution.state_caution = "released"
                caution.caution_provisional_recovery_date = datetime.now().date()
        order = self.env["building.order"].search([("opp_id", "=", self.id), ("state", "=", "sent")])
        if order:
            order.action_lost()
        stage_lost = self.env["crm.stage"].search([("is_lost", "=", True)])
        if stage_lost:
            self.stage_id = stage_lost.id
        return res

    def action_set_tender(self):
        order = self.env["building.order"].search([("opp_id", "=", self.id), ("state", "=", "draft")])
        if not order:
            raise UserError(_("Attention!: Il y a pas un Bordereau des prix pour ce marché! : Merci de le definir."))
        order.action_sent()
        stage_tender = self.env["crm.stage"].search([("is_tender", "=", True)])
        if stage_tender:
            self.stage_id = stage_tender.id

    def action_set_cancel(self):
        for caution in self.caution_ids:
            if caution.type_caution == "tender_caution":
                caution.state_caution = "released"
                caution.caution_provisional_recovery_date = datetime.now().date()
        order = self.env["building.order"].search([("opp_id", "=", self.id)])
        if order:
            order.action_cancel()
        stage_cancel = self.env["crm.stage"].search([("is_cancel", "=", True)])
        if stage_cancel:
            self.stage_id = stage_cancel.id

    def action_create_building_order(self):
        self.is_building_order_created = True
        record_building_order = {
            "partner_id": self.partner_id.id,
            "commercial_id": self.user_id.id,
            "ref_tendering": self.num_ao,
            "opp_id": self.id,
            "opening_date": self.date_open_ao,
            "deadline": self.delai,
            "is_caution": self.is_deposit
        }
        building_order = self.env["building.order"].create(record_building_order)
        domain = [("id", "=", building_order.id)]
        return {
            "name": _("BP à compléter"),
            "domain": domain,
            "res_model": "building.order",
            "type": "ir.actions.act_window",
            "view_id": False,
            "view_mode": "list,form",
        }

    def action_validate(self):
        current_sequence = self.stage_id.sequence
        step = 1
        next_stage = self.env["crm.stage"].search([("sequence", "=", current_sequence + step)])
        flags = ["is_lost", "is_won"]

        if self.state_by_stage in flags and (next_stage.is_won or next_stage.is_lost):
            step = 2  # 2 steps back

        next_stage = self.env["crm.stage"].search([("sequence", "=", current_sequence + step)])

        if next_stage:
            self.stage_id = next_stage.id

    def action_return(self):
        current_sequence = self.stage_id.sequence
        step = 1
        previous_stage = self.env["crm.stage"].search([("sequence", "=", current_sequence - step)])
        flags = ["is_lost", "is_won"]

        if self.state_by_stage in flags and (previous_stage.is_won or previous_stage.is_lost):
            step = 2  # 2 steps back

        previous_stage = self.env["crm.stage"].search([("sequence", "=", current_sequence - step)])

        if previous_stage:
            self.stage_id = previous_stage.id

    def action_set_abandoned(self):
        if self.stage_id.is_won:
            raise ValueError("Une opportunité gagnée ne peut pas être abandonnée.")

        abandoned_stage = self.env['crm.stage'].search([('name', '=', 'Abandonnée')], limit=1)

        if abandoned_stage:
            self.stage_id = abandoned_stage.id
            self.give_up = True


    def action_mark_as_won(self):
        stage_id = self.env["crm.stage"].search([("is_won", "=", True)], limit=1).id

        if not self.is_building_order_created:
            stage_id = self.env["crm.stage"].search([("name", "=", "Manque BP")], limit=1).id

        self.stage_id = stage_id
    def action_mark_as_lost(self):
        self.stage_id = self.env["crm.stage"].search([("is_lost", "=", True)], limit=1).id

    def action_mark_as_cancel(self):
        self.stage_id = self.env["crm.stage"].search([("is_cancel", "=", True)], limit=1).id

    def action_restore(self):
        self.stage_id = self.env["crm.stage"].search([], order="sequence", limit=1).id

    def action_convert_to_project(self):
        record_site = {
            "partner_id": self.partner_id.id,
            "name": self.name,
            "opp_id": self.id
        }

        site = self.env["building.site"].sudo().create(record_site)

        building_order = self.env["building.order"].search([("opp_id", "=", self.id)])
        if building_order:
            building_order.write({"site_id": site.id})

        context = dict(self.env.context)
        context["form_view_initial_mode"] = "edit"
        return {
            "name": _("Affaire à compléter"),
            "res_model": "building.site",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_id": site.id,
            "context": context,
            "target": "current",
        }

    def action_call_crm_lead_return_wizard(self):
        return {
            "name": _("Remettre"),
            "res_model": "crm.lead.return.wizard",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }
    @api.model
    def fields_view_get(self, view_id=None, view_type="form", toolbar=False, submenu=False):
        result = super(CrmLead, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result["arch"])

        if view_type == "form":
            for node in doc.xpath("//field"):
                domain = [("state_by_stage", "=", "is_won")]
                if node.attrib.get("modifiers"):
                    attr = json.loads(node.attrib.get("modifiers"))
                    if attr.get("readonly"):
                        value_readonly = attr.get("readonly")
                        if str(attr.get("readonly")) != "True":
                            value_readonly.insert(0, "|")
                            domain = value_readonly + domain
                    attr["readonly"] = domain
                    node.set("modifiers", json.dumps(attr))
        result["arch"] = etree.tostring(doc)
        arch = etree.fromstring(result["arch"])
        arch.set("delete", "false")
        result["arch"] = etree.tostring(arch)

        return result


class CrmStage(models.Model):
    _inherit = "crm.stage"

    # is_follow = fields.Boolean("Étape de suivi ?", default=True)
    # is_qualif = fields.Boolean("Qualification DG ?")
    # is_tender = fields.Boolean("Envoyé au client ?")
    is_lost = fields.Boolean("Est en étape perdue?")
    is_sent_to_client = fields.Boolean("Est envoyé au client?")
    is_cancel = fields.Boolean("Est en étape annulé?")


class CrmLeadSector(models.Model):
    _name = "crm.lead.sector"

    code = fields.Char("Code")
    name = fields.Char("Nom")


class CrmLeadQualification(models.Model):
    _name = "crm.lead.qualification"

    sector_id = fields.Many2one("crm.lead.sector", string="Secteur")
    code = fields.Char("Code")
    name = fields.Char("Nom")


class CrmLeadClassification(models.Model):
    _name = "crm.lead.classification"

    name = fields.Char("Nom")
    start_date = fields.Date("Date de début")
    end_date = fields.Date("Date de fin")
    is_active = fields.Boolean("Active ?", default=True)
    nb_days = fields.Integer("Nombres de jours", defaul=0)

    def _update_is_active_cron(self):
        for classification in self.search([("is_active", "=", True)]):
            date_now = date.today()
            if classification.end_date < date_now:
                classification.is_active = False
            if classification.end_date > date_now:
                nb_days = (classification.end_date - date_now).days
                classification.nb_days = nb_days


class CrmLeadQualificationLine(models.Model):
    _name = "crm.lead.qualification.line"

    sector = fields.Many2one("crm.lead.sector", string="Secteur")
    qualification_requested = fields.Many2one("crm.lead.qualification", string="Qualification demandée")
    requested_class = fields.Selection([("s", "S"), ("1", "1"), ("2", "2"), ("3", "3"), ("4", "3"), ("5", "3")],
                                       index=True, required=True, tracking=15, default=lambda self: "1")
    classi = fields.Many2one("crm.lead.classification", string="Classe", domain=[("is_active", "=", True)])
    opp_id = fields.Many2one("crm.lead", string="Opp")


class CrmLeadClassline(models.Model):
    _name = "crm.lead.class.line"

    requested_class = fields.Selection([("1", "1"), ("2", "2"), ("3", "3"), ("4", "3"), ("5", "3")], index=True,
                                       required=True, tracking=15, default=lambda self: "1")
    classi = fields.Many2one("crm.lead.classification", string="Classe", domain=[("is_active", "=", True)])
    opp_id = fields.Many2one("crm.lead", string="Opp")


class AccountCaution(models.Model):
    _name = "account.caution"

    ligne_id = fields.Many2one("account.caution.line", string="Ligne de caution", required=False, readonly=False,
                               domain=[("state", "=", "open")])
    bank_id = fields.Many2one("res.bank", string="Banque", required=False, readonly=False)
    ref = fields.Char("N° de référence")
    caution_deposit_date = fields.Date("Date de dépot")
    caution_provisional_recovery_date = fields.Date("Date prévisionnelle de récupération")
    caution_recovery_date = fields.Date("Date de récupération réel")
    type_caution = fields.Selection([("tender_caution", "CP"), ("definitif_caution", "CD"), ("rg_caution", "RG")],
                                    string="Type", required=False, default="tender_caution")
    state_caution = fields.Selection(
        [("caution_request", "Demandée"), ("caution_to_diposed", "À déposer"), ("caution_diposed", "Déposée"),
         ("released", "À récupérer"), ("retrieved_caution", "Récupérée")], string="Status", required=False,
        default="caution_request")
    opp_id = fields.Many2one("crm.lead", string="Dossier", required=False, readonly=False)
    deposit = fields.Float("Montant")
    partner_id = fields.Many2one("res.partner", string="Client", required=False, readonly=False,
                                 related="opp_id.partner_id")
    nb_days = fields.Integer("Nombres de jours", store=True, readonly=True, compute="_compute_nb_days")
    responsible_id = fields.Many2one("hr.employee", "Responsable")
    interest_amount = fields.Float("Interets", store=True, readonly=True, compute="_compute_interest_amount")
    # type_caution_cp = fields.Integer("Type caution", store=True, readonly=True, compute="_compute_type_caution_str")
    # type_caution_cd = fields.Integer("Type caution", store=True, readonly=True, compute="_compute_type_caution_str")
    # type_caution_gr = fields.Integer("Type caution", store=True, readonly=True, compute="_compute_type_caution_str")
    type_caution_str = fields.Char("Type caution")
    nb_days_after_released = fields.Integer("Nombres de jours pour récupuration", store=True, readonly=True,
                                            compute="_compute_nb_days_after_released")
    is_readonly = fields.Boolean("Readonly?", defaut=False)

    @api.model
    @api.depends("caution_provisional_recovery_date")
    def _compute_nb_days_after_released(self):
        for caution in self:
            if caution.caution_provisional_recovery_date and caution.state_caution == "released":
                date_now = date.today()
                nb_days_after_released = (date_now - caution.caution_provisional_recovery_date).days
                caution.nb_days_after_released = nb_days_after_released

    # @api.model
    # @api.depends("type_caution")
    # def _compute_type_caution_str(self):
    #     for caution in self:
    #         type_caution_cp = 0
    #         type_caution_cd = 0
    #         type_caution_gr = 0
    #         if caution.type_caution == "tender_caution":
    #             type_caution_cp = 1
    #         if caution.type_caution == "definitif_caution":
    #             type_caution_cd = 1
    #         if caution.type_caution == "rg_caution":
    #             type_caution_gr = 1
    #         caution.type_caution_cp = type_caution_cp
    #         caution.type_caution_cd = type_caution_cd
    #         caution.type_caution_gr = type_caution_gr

    def unlink(self):
        if self.state_caution in ["caution_diposed", "released", "retrieved_caution"]:
            raise UserError(_("Vous ne pouvez pas effectuer cette action sur une caution déposée."))
        return super(AccountCaution, self).unlink()

    @api.onchange("type_caution")
    def _onchnge_type_caution(self):
        caution = self
        type_caution_str = ""
        if caution.type_caution == "tender_caution":
            type_caution_str = "cp"
        if caution.type_caution == "definitif_caution":
            type_caution_str = "cd"
        if caution.type_caution == "rg_caution":
            type_caution_str = "gr"
        caution.type_caution_str = type_caution_str

    def action_to_diposed(self):
        self.state_caution = "caution_to_diposed"

    def action_diposed(self):
        if not self.caution_deposit_date:
            raise UserError(_("Attention Date de dépot est vide"))
        if not self.caution_provisional_recovery_date:
            raise UserError(_("Attention Date prévisionnelle de récupération est vide"))
        self.state_caution = "caution_diposed"

    def action_retrieved(self):
        if not self.caution_recovery_date:
            raise UserError(_("Attention Date de récupération réel est vide"))
        self.state_caution = "retrieved_caution"

    @api.onchange("ligne_id")
    def _onchnge_ligne_caution(self):
        for caution in self:
            caution.bank_id = caution.ligne_id.bank_id.id

    @api.model
    @api.depends("caution_deposit_date")
    def _compute_nb_days(self):
        for caution in self:
            if caution.caution_deposit_date and caution.state_caution == "caution_diposed":
                date_now = date.today()
                nb_days = (date_now - caution.caution_deposit_date).days
                caution.nb_days = nb_days

    @api.model
    @api.depends("nb_days", "deposit")
    def _compute_interest_amount(self):
        for caution in self:
            interest_amount = (caution.deposit * caution.nb_days * 0.0025) / 365
            caution.interest_amount = interest_amount

    @api.model
    @api.onchange("deposit", "ligne_id")
    def _onchnge_deposit_ligne_caution(self):
        for caution in self:
            if caution.deposit > caution.ligne_id.amount_available:
                raise UserError(_("Attention dépassement montant disponible dans la lingne de caution %s!!!!") % (
                    caution.ligne_id.name))

    def _update_nb_days_from_cron(self):
        cautions = self.env["account.caution"].search([("state_caution", "in", ["caution_diposed", "released"])])
        for caution in cautions:
            date_now = date.today()
            if caution.caution_deposit_date and caution.state_caution == "caution_diposed":
                nb_days = (date_now - caution.caution_deposit_date).days
                caution.nb_days = nb_days
            if caution.caution_provisional_recovery_date and caution.state_caution == "released":
                nb_days_after_released = (date_now - caution.caution_provisional_recovery_date).days
                caution.nb_days_after_released = nb_days_after_released


class AccountCautionLine(models.Model):
    _name = "account.caution.line"

    name = fields.Char("Réf Ligne Caution")
    bank_id = fields.Many2one("res.bank", string="Banque", required=False, readonly=False)
    amount = fields.Float("Montant")
    amount_available = fields.Float("Montant disponible", store=True, readonly=True,
                                    compute="_compute_amount_available")
    state = fields.Selection([("draft", "Brouillon"), ("open", "Ouverte"), ("closed", "Fermée")], string="Status",
                             required=False, default="draft")
    caution_ids = fields.One2many("account.caution", "ligne_id", string="Cautions", copy=True)
    is_cp = fields.Boolean("Caution Provisoire")
    is_cd = fields.Boolean("Caution Définitive")
    is_gr = fields.Boolean("Caution Garantie")
    pratical_amount = fields.Float("Montant Consommé", store=True, readonly=True, compute="_compute_amount_available")
    type_caution = fields.Char("Type caution", store=True, readonly=True, compute="_compute_type_caution")
    is_reset_draft = fields.Boolean("A remmetre en brouillon", store=True, readonly=True,
                                    compute="_compute_is_reset_draft")
    date_deadline = fields.Date("Date d'échéance")

    def unlink(self):
        if len(self.caution_ids) >= 1:
            raise UserError(_("Vous ne pouvez pas effectuer cette action sur une ligne qui contient des cautions."))
        return super(AccountCautionLine, self).unlink()

    @api.model
    @api.depends("caution_ids")
    def _compute_is_reset_draft(self):
        for caution in self:
            is_reset_draft = False
            if len(caution.caution_ids) >= 1:
                is_reset_draft = True
            caution.is_reset_draft = is_reset_draft

    @api.model
    @api.depends("is_cp", "is_cd", "is_gr")
    def _compute_type_caution(self):
        for caution in self:
            type_caution = ""
            if caution.is_cp:
                if type_caution == "":
                    type_caution = "cp"
                else:
                    type_caution = type_caution + "_cp"
            if caution.is_cd:
                if type_caution == "":
                    type_caution = "cd"
                else:
                    type_caution = type_caution + "_cd"
            if caution.is_gr:
                if type_caution == "":
                    type_caution = "gr"
                else:
                    type_caution = type_caution + "_gr"
            caution.type_caution = type_caution

    def action_open(self):
        self.state = "open"
        self.amount_available = self.amount
        self.pratical_amount = 0

        ##recalcul disponible
        for l in self:
            for caution in l.caution_ids:
                if caution.state_caution == "caution_diposed":
                    l.amount_available = l.amount_available - caution.deposit
                    l.pratical_amount = l.pratical_amount + caution.deposit

    def action_close(self):
        self.state = "closed"

    def action_remette_draft(self):
        self.state = "draft"

    @api.model
    @api.depends("caution_ids", "caution_ids.state_caution", "caution_ids.deposit")
    def _compute_amount_available(self):
        for l in self:
            for caution in l.caution_ids:
                if caution.state_caution == "caution_diposed":
                    l.amount_available = l.amount_available - caution.deposit
                    l.pratical_amount = l.pratical_amount + caution.deposit

                if caution.state_caution == "retrieved_caution":
                    l.amount_available = l.amount_available + caution.deposit
                    l.pratical_amount = l.pratical_amount - caution.deposit


class CrmTrc(models.Model):
    _name = "crm.trc"
    _inherit = ["portal.mixin", "mail.thread", "mail.activity.mixin", "utm.mixin"]

    # code = fields.Char("Num TRC")
    partner_id = fields.Many2one("res.partner", string="Client", domain=[("customer_rank", ">", 0)], required=False,
                                 readonly=False)
    name = fields.Char("Designation")
    duration_work = fields.Float("Délai d'exécution")
    cps_is_signed = fields.Boolean("CPS Signé ?")
    os_is_available = fields.Boolean("OS ?")
    line_ids = fields.One2many("crm.trc.line", "trc_id", string="Dates TRC", copy=True)


class CrmTrcLine(models.Model):
    _name = "crm.trc.line"

    trc_id = fields.Many2one("crm.trc", string="TRC", required=False, readonly=False)
    partner_id = fields.Many2one("res.partner", string="Client", required=False, readonly=False,
                                 related="trc_id.partner_id")
    name = fields.Char("Designation", related="trc_id.name")
    ref = fields.Char("Réf")
    duration_work = fields.Float("Délai d'exécution", related="trc_id.duration_work")
    cps_is_signed = fields.Boolean("CPS Signé ?", related="trc_id.cps_is_signed")
    os_is_available = fields.Boolean("OS ?", related="trc_id.os_is_available")
    start_date = fields.Date("Date de début")
    end_date = fields.Date("Date de fin")
    is_active = fields.Boolean("Active ?", default=True)
    nb_days = fields.Char("Nombres de jours", default=0)
    is_warn = fields.Boolean("Warning ?", default=False)

    def _update_trc_is_active_cron(self):
        for trc in self.search([("is_active", "=", True)]):
            date_now = date.today()
            is_warn = False
            is_active = True
            if trc.end_date < date_now:
                is_active = False
            if trc.end_date > date_now:
                nb_days = (trc.end_date - date_now).days
                trc.nb_days = nb_days
                if nb_days <= 5:
                    is_warn = True
            trc.is_warn = is_warn
            trc.is_active = is_active

# class CrmLeadLost(models.TransientModel):
#     _inherit = "crm.lead.lost"

#     def action_lost_reason_apply(self):
#         res = super(CrmLeadLost, self).action_lost_reason_apply()
#         for caution in self.caution_ids:
#             if caution.type_caution == "tender_caution":
#                 caution.state_caution = "released"
#                 caution.caution_provisional_recovery_date = datetime.now().date()
#         order = self.env["building.order"].search([("opp_id", "=", self.id), ("state", "=", "sent")])
#         if order:
#             order.action_lost()

#         return res
