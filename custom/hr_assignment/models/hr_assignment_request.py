from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

from datetime import datetime
from lxml import etree


class HrAssignmentRequest(models.Model):
    _name = "hr.assignment.request"
    _description = "Demande d'affectation"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    def unlink(self):
        for request in self:
            if request.state != "draft":
                raise UserError("Assurez-vous que la demande est en Brouillon.")
        return super(HrAssignmentRequest, self).unlink()

    def _site_id_domain(self):
        need_ids = self.env["building.purchase.need"].search([("state", "=", "approuved")])
        site_ids = [0]

        group = self._context.get("group")

        if group:
            profile_ids = self.env["building.profile.assignment"].search([
                ("user_id", "=", self.env.user.id),
                ("group_id.name", "=", group)
            ])
            user_site_ids = profile_ids.mapped("site_id").ids

            if group == "SOTASERV_DG":
                site_ids = need_ids.mapped("site_id").filtered(
                    lambda site: site.state == "open"
                ).ids

                extra_sites = self.env["building.site"].search([
                    ("id", "in", [122, 123]),
                ])
                site_ids += extra_sites.ids
            else:
                site_ids = need_ids.mapped("site_id").filtered(
                    lambda site: site.state == "open" and site.id in user_site_ids
                ).ids

                profile_site_ids = self.env["building.profile.assignment"].search([
                    ("user_id", "=", self.env.user.id),
                    ("site_id", "in", [122, 123])
                ]).mapped("site_id").ids

                extra_sites = self.env["building.site"].search([
                    ("id", "in", profile_site_ids),
                ])
                site_ids += extra_sites.ids

        site_ids = list(set(site_ids))

        return [("id", "in", site_ids)]

    @api.onchange("site_id")
    def _onchange_site_id(self):
        self.line_ids = [(3, line.id) for line in self.line_ids]
        self._compute_job_ids()

    @api.onchange("line_ids")
    def _compute_job_ids(self):
        domain = []
        if self.site_id and self.site_id.id not in [122, 123]:
            need = self.env["building.purchase.need"].search([("site_id", "=", self.site_id.id)])
            available_posts = need.ressource_humain_ids.filtered(lambda line: line.volume_available > 0).mapped("job_id").ids
            exclude = self.line_ids.mapped("job_id").ids

            domain.append(("id", "in", [id for id in available_posts if id not in exclude]))
        self.job_ids = self.env["hr.job"].search(domain)

        def _name(category): return dict(self.job_ids._fields["categ_job"].selection).get(category)
        categories = list(set(self.job_ids.mapped("categ_job")))
        old_categories = self.env["hr.assignment.job.category"].search([("code", "in", categories)])
        new_categories = self.env["hr.assignment.job.category"].create([{"name": _name(category), "code": category} for category in categories if category not in old_categories.mapped("code")])
        self.job_category_ids = old_categories + new_categories

    @api.constrains("line_ids")
    def _check_line_ids(self):
        def _raise(message, lines):
            if len(lines) == 1:
                message += f"Ligne: {lines[0]}"
            if len(lines) > 1:
                message += "Lignes:"
                for line in lines:
                    message += f"\n\t- {line}"
            if len(lines) > 0:
                raise UserError(message)

        def _check_date():
            message = "La date doit être postérieure ou égale à la date d'aujourd'hui.\n\n"
            lines = [line.job_id.name for line in self.line_ids if line.date_requested < datetime.today().date()]
            _raise(message, lines)

        def _check_quantity():
            message = "Le nombre doit être supérieur à 0.\n\n"
            lines = [line.job_id.name for line in self.line_ids if line.number_requested <= 0]
            _raise(message, lines)

        _check_date()
        _check_quantity()

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
    requested_by = fields.Many2one("res.users", string="Demandée par", default=lambda self: self.env.user.id)
    requested_on = fields.Date("Demandée le")
    site_id = fields.Many2one("building.site", string="Affaire", domain=_site_id_domain)
    line_ids = fields.One2many("hr.assignment.request.line", "request_id", string="Lignes")
    job_category_ids = fields.Many2many("hr.assignment.job.category", string="Catégories disponibles", compute="_compute_job_ids")
    job_ids = fields.Many2many("hr.job", string="Postes disponibles", compute="_compute_job_ids")
    note = fields.Text("Note", default="")

    def button_note(self):
        return {
            "name": "Motif du refus",
            "type": "ir.actions.act_window",
            "res_model": "hr.assignment.request",
            "view_mode": "form",
            "res_id": self.id,
            "views": [(self.env.ref("hr_assignment.hr_assignment_request_view_form_note").id, "form")],
            "target": "new",
            "context": {self.state: True},
        }

    def button_reset_note(self):
        self.note = ""

    def update_log(self, items=""):
        def _state_string(): return dict(self._fields["state"].selection)[self.state]
        self.message_post(body=f"""
            <ul>
                <li>Statut: <b>{_state_string()}</b></li>
                {items}
            </ul>
        """)

    def button_draft(self):
        self.state = self.line_ids.state = "draft"
        self.update_log()

    def action_return_to_validated(self):
        for line in self:
            if line.state == 'approved':
                line.state = 'validated'
            else:
                raise ValidationError("Cette action n'est possible que depuis l'état 'À affecter'.")

    def button_validated(self):
        self.state = self.line_ids.state = "validated"
        self.requested_on = self.requested_on or datetime.today()
        if self.name == "/": self.name = self.env["ir.sequence"].next_by_code("hr.assignment.request")

        def _format_date(date): return datetime.strftime(date, "%d/%m/%Y")
        def _line(line): return f"<li>{line.number_requested}x {line.job_id.name} dès le {_format_date(line.date_requested)}</li>"
        lines = [_line(line) for line in self.line_ids]
        lines = f"<ul>{''.join(lines)}</ul>"

        self.update_log(f"""
            <li>Affaire: {self.site_id.name}</li>
            <li>Lignes: {lines}</li>
        """)

    def _check_step_2(self, button):
        user = self.env["res.users"].browse(self.write_uid.id)
        approval_chain_line = self.env["approval.chain.line"].search([("step_1", "=", user.id), ("parent_id.model_id", "=", self._name)])
        allowed_uids = approval_chain_line.mapped("step_2")

        if self.env.user not in allowed_uids:
            raise ValidationError(f"Vous n'êtes pas autorisé à {button} cette demande.\n\nAucune chaîne d'approbation ne ressemble à celle-ci:\n{user.name} ─ Vous")

    def button_approved(self):
        self._check_step_2("approuver")
        self.state = self.line_ids.state = "approved"
        self.update_log()

    def button_rejected(self):
        self._check_step_2("rejeter")
        self.state = self.line_ids.state = "rejected"
        self.update_log(self.note and f"<li>Motif: {self.note}</li>" or "")

    def button_canceled(self):
        self.state = self.line_ids.state = "canceled"
        self.update_log()

    def action_get_user_hr_assignment_requests(self, group):
        SUPERVISOR_GROUPS = ["SOTASERV_SUPERVISEUR_SITE", "SOTASERV_DG"]
        VISUALIZATION_GROUP = "RH_VISUALISATION"
        
        user = self.env.user
        profiles = self.env["building.profile.assignment"].search([
            ("user_id", "=", user.id),
            ("group_id.name", "=", group)
        ])
        
        site_ids = profiles.mapped("site_id").ids
        is_supervisor = group in SUPERVISOR_GROUPS

        context = {
            "search_default_filter_requested_by_uid": True,
            "group": group,
            "is_supervisor": is_supervisor,
        }

        if group == "SOTASERV_SUPERVISEUR_SITE" or group == "RH_VISUALISATION":
            context.update({"create": False, "edit": False, "delete": False})

        domain = []
        if not is_supervisor and group != VISUALIZATION_GROUP:
            domain.append(("site_id", "in", site_ids))

        return {
            "name": "Demandes",
            "type": "ir.actions.act_window",
            "res_model": "hr.assignment.request",
            "view_mode": "list,form",
            "views": [
                (self.env.ref("hr_assignment.hr_assignment_request_view_tree").id, "list"),
                (self.env.ref("hr_assignment.hr_assignment_request_view_form").id, "form"),
            ],
            "domain": domain,
            "context": context,
        }

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        result = super(HrAssignmentRequest, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self.env.context.get("is_supervisor") == True:
            if view_type == "form":
                doc = etree.XML(result["arch"])
                for button in doc.xpath("//header/button"):
                    button.getparent().remove(button)
                result["arch"] = etree.tostring(doc)

        return result