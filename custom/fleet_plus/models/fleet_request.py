from odoo import models, fields, api

from datetime import datetime


class FleetRequest(models.Model):
    _name = "fleet.request"
    _description = "Demande de matériels"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    state = fields.Selection(string="Statut", default="draft", selection=[
        ("draft", "Brouillon"),
        ("validated", "Validée"),
        ("approved", "À affecter"),
        ("in_progress", "Affection en cours"),
        ("done", "Traitée"),
        ("closed", "Close"),
        ("rejected", "Rejetée"),
    ])
    name = fields.Char("Référence", default="/")
    type = fields.Selection(string="Type", default="equipment", selection=[
        ("equipment", "Matériels"),
        ("small", "Petits matériels"),
    ])
    requested_by = fields.Many2one("res.users", string="Demandée par", default=lambda self: self.env.user.id)
    requested_on = fields.Date("Demandée le")
    site_id = fields.Many2one("building.site")
    is_line_ids_set = fields.Boolean("", compute="_compute_is_line_ids_set")
    line_ids = fields.One2many("fleet.request.line", "request_id", string="Lignes")
    note = fields.Text("Note", default="")

    equipment_ids = fields.Many2many("maintenance.vehicle.category", string="Matériels")
    small_equipment_ids = fields.Many2many("fleet.vehicle", string="Petits matériels")

    @api.onchange("line_ids")
    def _onchange_is_line_ids_set(self):
        self._compute_is_line_ids_set()

    @api.depends("line_ids")
    def _compute_is_line_ids_set(self):
        for record in self:
            record.is_line_ids_set = bool(record.line_ids)

    def _get_need(self):
        need = self.env["building.purchase.need"].search([("site_id", "=", self.site_id.id)], limit=1)
        return need

    @api.onchange("site_id", "type", "line_ids")
    def _set_domain(self):
        need = self._get_need()
        self.equipment_ids = self.small_equipment_ids = None
        if need:
            if self.type == "equipment":
                self.equipment_ids = need.equipment_ids.mapped("equipment_id") - self.line_ids.mapped("equipment_id")
            elif self.type == "small":
                self.small_equipment_ids = need.small_equipment_ids.mapped("equipment_id") - self.line_ids.mapped("small_equipment_id")

    def button_draft(self):
        self.state = "draft"

    def button_validated(self):
        self.state = "validated"
        self.requested_on = self.requested_on or datetime.today()
        if self.name == "/":
            self.name = self.env["ir.sequence"].next_by_code("fleet.request")


class FleetRequestLine(models.Model):
    _name = "fleet.request.line"

    state = fields.Selection(string="Statut", default="draft", compute="_compute_state", store=True, selection=[
        ("draft", "Brouillon"),
        ("validated", "Validée"),
        ("approved", "À affecter"),
        ("in_progress", "Affection en cours"),
        ("done", "Traitée"),
        ("closed", "Close"),
        ("rejected", "Rejetée"),
    ])
    request_id = fields.Many2one("fleet.request", string="Demande", ondelete="cascade")
    requested_by = fields.Many2one("res.users", string="Demandé par", related="request_id.requested_by", store=True)
    requested_on = fields.Date("Demandé le", related="request_id.requested_on", store=True)
    site_id = fields.Many2one("building.site", string="Affaire", related="request_id.site_id", store=True)
    type = fields.Selection(string="Type", related="request_id.type", store=True)

    equipment_id = fields.Many2one("maintenance.vehicle.category", "Matériel")
    small_equipment_id = fields.Many2one("fleet.vehicle", "Petit matériel")
    small_id = fields.Many2one("product.product", "Petit matériel")
    resource = fields.Char("Resource")

    quantity = fields.Float("Quantité")
    quantity_available = fields.Float("Qté dispo.", compute="_compute_available")
    quantity_assigned = fields.Float("Qté affectée", compute="_compute_quantity_assigned")
    quantity_remaining = fields.Float("Qté restante", compute="_compute_quantity_remaining")
    duration = fields.Float("Durée")
    duration_available = fields.Float("Durée LDB", compute="_compute_available")
    uom_id = fields.Many2one("uom.uom", "UDM", compute="_compute_available")
    price_available = fields.Float("PU LDB")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    estimated_cost = fields.Monetary(string="Coût estimé", currency_field="currency_id")
    is_assignable = fields.Boolean(compute="_compute_is_assignable")

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        result = super(FleetRequestLine, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        arch = etree.fromstring(result["arch"])
        arch.set("delete", "false")
        if view_type == "list" and not self.env.context.get("show_action_assign"):
            button_element = arch.find('.//button')
            if button_element is not None: arch.remove(button_element)
        result["arch"] = etree.tostring(arch, pretty_print=True, encoding='unicode')
        return result

    def _compute_quantity_assigned(self):
        for line in self:
            line.quantity_assigned = self.env["fleet.assignment.line"].search_count([("request_line_id", "=", line.id)])

    @api.onchange("quantity", "duration", "price_available")
    def _onchange_quantity(self):
        self.estimated_cost = self.quantity * self.duration * self.price_available

    def _get_need_line(self):
        try:
            is_equipment = self.nature == "equipment"
            model = "building.purchase.need." + ("equipment" if is_equipment else "small.equipment")
            equipment_id = self.equipment_id.id if is_equipment else self.small_id.id
            need_line = self.env[model].search([
                ("need_id", "=", self.env["building.purchase.need"].search([("site_id", "=", self.site_id.id)], limit=1).id),
                ("equipment_id", "=", equipment_id),
                ("equipment_id", "!=", False),
            ], limit=1)            
            return need_line.available_quantity, need_line.duree_j if is_equipment else need_line.duree, need_line.price_unit, need_line.uom_id.id
        except Exception as e:            
            _logger.error(f"Error while fetching need_line data: {e}")
            return 0, 0, 0, False

    @api.depends("equipment_id", "small_id")
    def _compute_available(self):
        for line in self:
            quantity_available, duration_available, price_unit, uom_id = line._get_need_line()            
            line.quantity_available = quantity_available
            line.duration_available = duration_available
            line.price_available = price_unit
            line.uom_id = uom_id

    @api.depends("quantity", "quantity_assigned")
    def _compute_quantity_remaining(self):
        for line in self:
            line.quantity_remaining = line.quantity - line.quantity_assigned

    @api.depends("request_id.state", "quantity_assigned")
    def _compute_is_assignable(self):
        for line in self:
            line.is_assignable = line.request_id.state == "approved" and line.quantity_assigned < line.quantity

    @api.onchange("nature")
    def _onchange_nature(self):
        self.equipment_id = self.small_id = self.quantity = self.duration = False
        if self.nature == "small":
            self.quantity = 1

    @api.onchange("equipment_id", "small_id")
    def _onchange_resource(self):
        self.resource = self.nature == "equipment" and self.equipment_id.name or self.nature == "small" and self.small_id.name or ""

    def action_assign(self):
        return {
            "name": f"Affectation",
            "type": "ir.actions.act_window",
            "res_model": "fleet.assignment.wizard",
            # "res_id": self.id,
            "view_mode": "form",
            # "views": [
            #     (self.env.ref("fleet_plus.fleet_request_view_form_reject").id, "form")
            # ],
            "context": {
                "default_request_line_id": self.id,
            },
            "target": "new",
        }

    def update_state(self):
        if self.quantity_assigned < self.quantity and self.quantity_assigned > 0:
            self.state = "in_progress"
        if self.quantity_assigned == self.quantity:
            self.state = "done"


class FleetRequestLog(models.Model):
    _name = "fleet.request.log"
    _order = "create_date desc"

    request_id = fields.Many2one("fleet.request", string="Demande", ondelete="cascade")
    comment = fields.Text("Commentaire")


class FleetAssignmentLine(models.Model):
    _name = "fleet.assignment.line"

    request_line_id = fields.Many2one("fleet.request.line", string="Ligne demande", ondelete="cascade")
    request_id = fields.Many2one("fleet.request", string="Demande", related="request_line_id.request_id")
    site_id = fields.Many2one("building.site", string="Affaire", related="request_line_id.site_id")
    resource_id = fields.Many2one("fleet.vehicle", "Resource")
    date_start = fields.Date("Date de début")
    date_end = fields.Date("Date de fin")
    state = fields.Selection(string="Statut", store=True, compute="_compute_state", selection=[
        ("planned", "Prévue"),
        ("open", "En cours"),
        ("done", "Clôturée"),
        ("canceled", "Annulée"),
    ])
    timeclock_ids = fields.One2many("fleet.timeclock.line", "assignment_line_id", string="Pointages")

    @api.depends("date_start", "date_end")
    def _compute_state(self):
        for line in self:
            line.state = False
            if line.date_start:
                today = datetime.today().date()
                if today < line.date_start:
                    line.state = "planned"
                if today >= line.date_start:
                    line.state = "open"
                if line.date_end and today > line.date_end:
                    line.state = "done"


class FleetTimeclockLine(models.Model):
    _name = "fleet.timeclock.line"

    assignment_line_id =  fields.Many2one("fleet.assignment.line", string="Affectation", ondelete="cascade")
    site_id = fields.Many2one("building.site", string="Affaire", related="assignment_line_id.site_id")
    resource_id = fields.Many2one("fleet.vehicle", string="Resource", related="assignment_line_id.resource_id")
    date = fields.Date("Date")
    hours = fields.Float("Heures d'opération")
    operator_id = fields.Many2one("hr.employee", string="Opérateur")
    consumption = fields.Float("Consommation")

    def _generate_today(self):
        today = datetime.today().date() + timedelta()
        open_assignments = self.env["fleet.assignment.line"].search([("state", "=", "open")])
        to_clock = open_assignments.filtered(lambda assignment: not any(timeclock.date == today for timeclock in assignment.timeclock_ids))
        self.create([{"assignment_line_id": assignment.id, "date": today} for assignment in to_clock])
