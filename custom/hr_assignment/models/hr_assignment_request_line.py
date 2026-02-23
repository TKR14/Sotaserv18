from odoo import models, fields, api
from odoo.exceptions import ValidationError

from datetime import datetime


class HrAssignmentJobCategory(models.Model):
    _name = "hr.assignment.job.category"

    name = fields.Char("Nom")
    code = fields.Char("Code")


class HrAssignmentRequestLine(models.Model):
    _name = "hr.assignment.request.line"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def name_get(self):
        return [(line.id, f"{line.request_id.name}/{line.job_id.name}" if line.request_id.name != "/" else line.job_id.name) for line in self]

    def _get_need_line(self):
        need = self.env["building.purchase.need"].search([("site_id", "=", self.site_id.id)])
        need_line = need.ressource_humain_ids.filtered(lambda line: line.job_id.id == self.job_id.id)
        return need_line

    @api.depends("job_id")
    def _compute_uom_id(self):
        for line in self:
            need_line = line._get_need_line()
            line.uom_id = need_line.uom_id.id if line.job_id else None

    @api.depends("job_id", "assignment_line_ids.timeclock_line_ids.hours")
    def _compute_details(self):
        for line in self:
            if line.job_id:
                need_line = line._get_need_line()
                line.budget = need_line.duree_j
                line.clocked = need_line.volume_clocked
                line.pct_consumed = need_line.duree_j > 0 and (need_line.volume_clocked * 100 / need_line.duree_j) or 0
            else:
                line.budget = 0
                line.clocked = 0
                line.pct_consumed = 0

    @api.onchange("assignment_line_ids")
    def _compute_employee_ids(self):
        exclude = self.assignment_line_ids.filtered(lambda line: line.state not in ["done", "canceled"]).mapped("employee_id").ids
        self.employee_ids = self.env["hr.employee"].search([("id", "not in", exclude), ("is_assigned", "=", False), ("job_id", "=", self.job_id.id)])

    @api.depends("assignment_line_ids")
    def _compute_number_assigned(self):
        for line in self:
            line.number_assigned = len(line.assignment_line_ids)

    @api.constrains("assignment_line_ids")
    def _check_assignment_line_ids(self):
        def _check_number():
            for line in self:
                if len(line.assignment_line_ids) > line.number_requested:
                    raise ValidationError("Vous ne pouvez pas affecter plus que le nombre demandé.")
        
        def _check_date_start():
            for line in self:
                for l in self.assignment_line_ids:
                    if l.date_start < line.date_requested:
                        raise ValidationError("La date de début ne doit pas être antérieure à celle demandée.")
                    # if l.date_start < datetime.today().date():
                    #     raise ValidationError("La date de début ne doit pas être antérieure à celle d'aujourd'hui.")

        _check_number()
        _check_date_start()

    @api.depends("request_id", "request_id.state", "number_assigned", "assignment_line_ids", "assignment_line_ids.state", "assignment_line_ids.date_end")
    def _compute_state(self):
        for line in self:
            if line.request_id.state not in ["draft", "validated", "rejected"]:
                if line.number_assigned == 0:
                    line.state = "approved"
                elif line.number_requested == line.number_assigned:
                    line.state = "done"
                elif line.number_assigned > 0:
                    line.state = "in_progress"
            else:
                line.state = line.request_id.state

            date_ends = line.assignment_line_ids.mapped("date_end")
            if False not in date_ends and len(date_ends) > 0:
                line.state = "closed"

        for request in self.mapped("request_id"):
            states = list(set(request.line_ids.mapped("state")))
            if len(states) == 1:
                request.state = states[0]
            else:
                request.state = "in_progress"

            if len(states) == 2 and set(["done", "closed"]).issubset(set(states)):
                request.state = "done"


    state = fields.Selection(string="Statut", default="draft", compute="_compute_state", store=True, tracking=True, selection=[
        ("draft", "Brouillon"),
        ("validated", "Validée"),
        ("approved", "À affecter"),
        ("in_progress", "Affection en cours"),
        ("done", "Traitée"),
        ("closed", "Close"),
        ("rejected", "Rejetée"),
    ])
    request_id = fields.Many2one("hr.assignment.request", string="Demande", ondelete="cascade")
    requested_by = fields.Many2one("res.users", string="Demandé par", related="request_id.requested_by", store=True)
    requested_on = fields.Date("Demandé le", related="request_id.requested_on", store=True)
    site_id = fields.Many2one("building.site", string="Affaire", related="request_id.site_id", store=True, tracking=True)

    job_category_id = fields.Many2one("hr.assignment.job.category", string="Catégorie", tracking=True)
    job_id = fields.Many2one("hr.job", string="Poste", tracking=True)
    uom_id = fields.Many2one("uom.uom", string="Unité", compute="_compute_uom_id", store=True)

    budget = fields.Integer("Budget", compute="_compute_details", store=True)
    clocked = fields.Integer("Pointé", compute="_compute_details", store=True)
    pct_consumed = fields.Integer("% Consommé", compute="_compute_details", store=True)

    number_requested = fields.Integer("Nombre demandé")
    number_assigned = fields.Integer("Nombre affecté", compute="_compute_number_assigned", store=True)
    date_requested = fields.Date("Date demandée", default=lambda _: datetime.today())

    employee_ids = fields.Many2many("hr.employee", string="Employés disponibles", compute="_compute_employee_ids")
    assignment_line_ids = fields.One2many("hr.assignment.line", "request_line_id", string="Lignes affectées")

    def open_cancellation_reason_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Assistant de Retour avec Motif",
            "res_model": "cancellation.reason",
            "view_mode": "form",
            "target": "new",
        }

    def action_back_to_validated(self, reason=None):
        for line in self:
            old_state = line.state

            line.with_context(mail_notrack=True).sudo().write({'state': 'validated'})

            line.message_post(body=f"""
                <ul>
                    <li>Statut: {dict(line._fields['state'].selection).get(old_state, old_state)} ➞ {dict(line._fields['state'].selection).get(line.state, line.state)}</li>
                    <li><strong>Motif:</strong> {reason}</li>
                </ul>
            """)

    @api.onchange("job_id")
    def _onchange_job_id(self):
        if self.job_id:
            self.job_category_id = self.env["hr.assignment.job.category"].search([("code", "=", self.job_id.categ_job)], limit=1).id

    @api.onchange("job_category_id")
    def _onchange_job_category_id(self):
        if self.job_category_id:
            if self.job_id.categ_job != self.job_category_id.code:
                self.job_id = False
            return {"domain": {"job_id":  [("id", "in", self.request_id.job_ids.ids), ("categ_job", "=", self.job_category_id.code)]}}

    def action_get_user_hr_assignment_request_lines(self, group):
        if not group:
            return

        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids
        not_supervisor = group not in ["SOTASERV_SUPERVISEUR_SITE", "SOTASERV_RH", "SOTASERV_DG"]

        return {
            "name": "Lignes des demandes",
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "hr.assignment.request.line",
            "views": [
                (self.env.ref("hr_assignment.hr_assignment_request_line_view_tree").id, "tree"),
                (self.env.ref("hr_assignment.hr_assignment_request_line_view_form").id, "form"),
            ],
            "search_view_id": (self.env.ref("hr_assignment.hr_assignment_request_line_view_search").id, "search"),
            "domain": [("site_id", "in", site_ids)] if not_supervisor else [],
            "context": {
                "search_default_group_by_site_id": True,
                "delete": False,
                "create": False,
                "edit": True if group == "SOTASERV_RH" else False,
            },
        }