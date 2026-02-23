from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta

from datetime import datetime, time
from dateutil.relativedelta import relativedelta


class HrAssignment(models.Model):
    _name = "hr.assignment"
    _rec_name = "site_id"
    
    def _compute_undone_line_ids(self):
        for record in self:
            record.undone_line_ids = record.line_ids.filtered(lambda line: line.state in ["planned", "open"])

    def _compute_count(self):
        for record in self:
            record.count_lines = len(record.line_ids)
            record.count_open_lines = len(record.line_ids.filtered(lambda line: line.state == "open"))
            record.count_planned_lines = len(record.line_ids.filtered(lambda line: line.state == "planned"))

    site_id = fields.Many2one("building.site", string="Affaire")
    line_ids = fields.One2many("hr.assignment.line", "assignment_id", string="Lignes")
    undone_line_ids = fields.One2many("hr.assignment.line", string="Lignes", compute="_compute_undone_line_ids")
    count_lines = fields.Integer("Nombre d'affectations", compute="_compute_count")
    count_open_lines = fields.Integer("En cours", compute="_compute_count")
    count_planned_lines = fields.Integer("Prévues", compute="_compute_count")

    def action_get_user_hr_assignments(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids
        not_supervisor = group not in ["SOTASERV_SUPERVISEUR_SITE", "SOTASERV_RH", "SOTASERV_DG", "SOTASERV_POINTAGE_RH"]
        form_view = "hr_assignment.hr_assignment_view_form" if group != "SOTASERV_MAGASINIER_CHANTIER" else "hr_assignment.hr_assignment_view_form_magasinier"

        domain = []

        if group in ["SOTASERV_OPC", "RH_VISUALISATION"]:
            if group == "RH_VISUALISATION":
                domain.append(("state", "in", ["open", "done", "rejected"]))
            elif group == "SOTASERV_OPC":
                domain = [("site_id", "in", site_ids)]
                
            return {
                "name": "Affectations",
                "type": "ir.actions.act_window",
                "view_mode": "tree",
                "res_model": "hr.assignment.line",
                "views": [
                    (self.env.ref("hr_assignment.hr_assignment_line_view_tree").id, "tree"),
                ],
                "domain": domain,
                "context": {
                    "delete": False,
                    "create": False,
                    "edit": False,
                    "group": group,
                },
            }
        
        if not_supervisor:
            domain = [("site_id", "in", site_ids)]

        return {
            "name": "Affectations",
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "hr.assignment",
            "views": [
                (self.env.ref("hr_assignment.hr_assignment_view_tree").id, "tree"),
                (self.env.ref(form_view).id, "form"),
            ],
            "domain": domain,
            "context": {
                "delete": False,
                "create": False,
                "edit": False,
                "group": group,
            },
        }

    def action_get_line_ids(self):
        group = self._context.get("group")
        can_edit = group in ["SOTASERV_CHEF_PROJET", "SOTASERV_DIRECTEUR_ZONE", "SOTASERV_CONDUCT_TRV", "SOTASERV_RH"]
        return {
            "name": "Lignes affectées",
            "type": "ir.actions.act_window",
            "view_mode": "tree",
            "res_model": "hr.assignment.line",
            "views": [
                (self.env.ref("hr_assignment.hr_assignment_line_view_tree").id, "tree"),
            ],
            "domain": [("assignment_id", "=", self.id)],
            "context": {
                "delete": False,
                "create": False,
                "edit": can_edit,
                "search_default_group_by_job_category_id": True,
                "search_default_group_by_job_id": True,
                "search_default_group_by_employee_id": True,
                "search_default_filter_planned": True,
                "search_default_filter_open": True,
            },
        }

    def action_timeclock(self):
        return {
            "name": "Pointages",
            "type": "ir.actions.act_window",
            "view_mode": "tree",
            "res_model": "hr.assignment.timeclock.line",
            "views": [
                (self.env.ref("hr_assignment.hr_assignment_timeclock_line_view_tree").id, "tree"),
            ],
            "domain": [("timeclock_id.assignment_id", "=", self.id)],
            "context": {
                "delete": False,
                "create": False,
                "edit": False,
                "search_default_group_by_job_category_id": True,
                "search_default_group_by_job_id": True,
                "search_default_group_by_employee_id": True,
            },
        }
    
    def action_recent_timeclock(self):
        two_days_ago = fields.Date.today() - timedelta(days=2)
        return {
            "name": "Pointages",
            "type": "ir.actions.act_window",
            "view_mode": "tree",
            "res_model": "hr.assignment.timeclock.line",
            "views": [
                (self.env.ref("hr_assignment.hr_assignment_timeclock_line_recent_view_tree").id, "tree"),
            ],
            "domain": [
                # ("date", ">=", two_days_ago),
                ("state", "=", "draft"),
            ],
            "context": {
                "delete": False,
                "create": False,
                "edit": False,
                "search_default_group_by_job_category_id": True,
                "search_default_group_by_job_id": True,
                "search_default_group_by_employee_id": True,
            },
        }

    def temp_action_get_user_hr_assignments(self):
        return {
            "name": "Affectations",
            "type": "ir.actions.act_window",
            "view_mode": "tree",
            "res_model": "hr.assignment",
            "views": [
                (self.env.ref("hr_assignment.hr_assignment_view_tree_temp").id, "tree"),
            ],
            "domain": [],
            "context": {
                "delete": False,
            },
        }

    def button_add_timeclock_lines(self):
        if len(self.ids) > 1:
            raise UserError("Sélectionnez une seule affaire.")

        parent_id = self.env["hr.assignment.wizard"].create({}).id

        return {
            "name": "Pointages",
            "type": "ir.actions.act_window",
            "view_mode": "tree",
            "res_model": "hr.assignment.wizard.line",
            "views": [
                (self.env.ref("hr_assignment.hr_assignment_wizard_line_view_tree").id, "tree"),
            ],
            "context": {
                "parent_id": parent_id,
                "default_parent_id": parent_id,
                "assignment_id": self.id,
            },
            "domain": [("parent_id", "=", parent_id)],
            "target": "new",
        }

    def action_timeclock_am(self):
        self.env["hr.assignment.line"].action_update()

        current_time = datetime.now().time()
        lock_time = time(9, 30)
        # if current_time > lock_time:
        #     raise UserError("Il semble que vous essayez d'accéder à la feuille de présence après 9h30.")

        timeclock = self.env["hr.assignment.timeclock"].search([("date", "=", datetime.today().date()), ("assignment_id", "=", self.id)], limit=1)
        if not bool(timeclock):
            timeclock = self.env["hr.assignment.timeclock"].create({
                "date": datetime.today().date(),
                "assignment_id": self.id,
            })

        def _new_timeclock(line):
            return {
                "timeclock_id": timeclock.id,
                "assignment_line_id": line.id,
            }
        lines_open = self.line_ids.filtered(lambda line: line.state == "open" and line.id not in timeclock.line_ids.mapped("assignment_line_id").ids)
        new_timeclock_lines = [_new_timeclock(line) for line in lines_open]
        timeclock.line_ids += self.env["hr.assignment.timeclock.line"].create(new_timeclock_lines)

        return {
            "name": "Pointage AM",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "hr.assignment.timeclock",
            "res_id": timeclock.id,
            "views": [
                (self.env.ref("hr_assignment.hr_assignment_timeclock_view_form_am").id, "form"),
            ],
            "context": {
                "delete": False,
                "create": False,
                "edit": False,
                "am": True,
            },
        }

    def action_timeclock_pm(self):
        timeclock = self.env["hr.assignment.timeclock"].search([("date", "=", datetime.today().date()), ("assignment_id", "=", self.id)], limit=1)

        return {
            "name": "Pointage PM",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "hr.assignment.timeclock",
            "res_id": timeclock.id,
            "views": [
                (self.env.ref("hr_assignment.hr_assignment_timeclock_view_form_pm").id, "form"),
            ],
            "context": {
                "delete": False,
                "create": False,
                "edit": True,
                "pm": True,
            },
        }

    # <record id="hr_assignment_action_print" model="ir.actions.server">
    #     <field name="name">Rapport Excel</field>
    #     <field name="model_id" ref="model_hr_assignment_wizard"/>
    #     <field name="binding_model_id" ref="model_hr_assignment"/>
    #     <field name="binding_view_types">list</field>
    #     <field name="state">code</field>
    #     <field name="code">action = model.new_wizard()</field>
    # </record>
    def button_excel_report_wizard(self):
        self.env["hr.assignment.wizard.year"].initialize(self.ids)
        self.env["hr.assignment.wizard.month"].initialize()
        
        # year = _year.search([("name", "=", datetime.today().year)], limit=1)
        # month = _month.search([("number", "=", datetime.today().month)], limit=1)

        # new_wizard = self.create({
        #     "year": bool(year) and year.id or False,
        #     "month": bool(year) and month.ids or False
        # })

        return {
            "name": "Suivi — Excel",
            "type": "ir.actions.act_window",
            "res_model": "hr.assignment.wizard",
            # "res_id": new_wizard.id,
            "view_mode": "form",
            "views": [
                (self.env.ref("hr_assignment.hr_assignment_wizard_view_form").id, "form"),
            ],
            "context": {
                "active_ids": self._context.get("active_ids"),
            },
            "target": "new",
        }


class HrAssignmentLine(models.Model):
    _name = "hr.assignment.line"

    @api.model
    def create(self, values):
        result = super(HrAssignmentLine, self).create(values)
        self.action_update()
        return result

    def write(self, values):
        result = super(HrAssignmentLine, self).write(values)
        if values.get("date_start") or values.get("employee_id"):
            if self.create_date.date() != datetime.today().date():
                raise UserError(f"Vous ne pouvez pas modifier la ligne: {self.employee_id.name}.")
        self.action_update()
        return result

    def unlink(self):
        for line in self:
            if line.create_date.date() != datetime.today().date():
                raise UserError(f"Vous ne pouvez pas supprimer la ligne: {line.employee_id.name}.")
        self.action_update()
        return super(HrAssignmentLine, self).unlink()

    @api.depends("timeclock_line_ids.hours")
    def _compute_volume_clocked(self):
        for line in self:
            if line.type == "daily":
                if line.is_clockable:
                    line.volume_clocked = sum(line.timeclock_line_ids.mapped("hours"))
                else:
                    line.volume_clocked = 0

    @api.depends("request_line_id")
    def _compute_assignment_id(self):
        for line in self:
            if not bool(line.assignment_id):
                assignment = self.env["hr.assignment"].search([("site_id", "=", line.request_line_id.site_id.id)], limit=1)
                if not bool(assignment):
                    assignment = self.env["hr.assignment"].create({
                        "site_id": line.request_line_id.site_id.id,
                    })
                line.assignment_id = assignment.id

    @api.depends("uom_id")
    def _compute_type(self):
        for line in self:
            line.type = "daily" if line.uom_id.name == "heures" else "monthly"

    assignment_id = fields.Many2one("hr.assignment", string="Réf. affectation", ondelete="cascade", compute="_compute_assignment_id", store=True)
    site_id = fields.Many2one("building.site", string="Affaire", related="assignment_id.site_id")
    request_line_id = fields.Many2one("hr.assignment.request.line", string="Ligne demande")
    job_category_id = fields.Many2one("hr.assignment.job.category", string="Catégorie", related="request_line_id.job_category_id", store=True)
    job_id = fields.Many2one("hr.job", string="Poste", related="request_line_id.job_id", store=True)
    uom_id = fields.Many2one("uom.uom", string="Unité", related="request_line_id.uom_id", store=True)

    volume_clocked = fields.Integer("Volume pointé", compute="_compute_volume_clocked", store=True)
    employee_id = fields.Many2one("hr.employee", string="Employé", ondelete="restrict")
    date_start = fields.Date("Date de début")
    date_end = fields.Date("Date de fin")
    state = fields.Selection(string="Statut", default="planned", selection=[
        ("planned", "Prévue"),
        ("open", "En cours"),
        ("done", "Terminée"),
        ("canceled", "Annulée"),
        ("rejected", "Rejetée"),
    ])
    type = fields.Selection(string="Type", compute="_compute_type", store=True, selection=[
        ("daily", "Quotidien"),
        ("monthly", "Mensuel"),
    ])
    timeclock_line_ids = fields.One2many("hr.assignment.timeclock.line", "assignment_line_id", string="Pointages")
    is_clockable = fields.Boolean("Pointable", default=True)

    date_first_timeclock = fields.Date("Date premier pointage")
    date_last_timeclock = fields.Date("Date dernier pointage")
    rejection_reason = fields.Text("Motif de rejet")

    def open_reject_reason_wizard(self):
        already_rejected = self.filtered(lambda r: r.state == "rejected")
        if already_rejected:
            raise UserError("Vous ne pouvez pas rejeter des lignes déjà rejetées.")

        invalid_records = self.filtered(lambda r: r.volume_clocked != 0)
        if invalid_records:
            if len(self) == 1:
                raise UserError("Le rejet est impossible : le volume pointé de cette ligne doit être nul.")
            else:
                raise UserError("Le rejet est impossible : certaines lignes présentent un volume pointé différent de zéro.")

        return {
            "name": "Assistant de rejet de ligne d'affectation",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "hr.assignment.line.reject.reason.wizard",
            "target": "new",
        }

    def get_rejection_reason(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Motif de rejet',
            'res_model': 'hr.assignment.line',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': self.env.ref('hr_assignment.view_hr_assignment_line_reject_reason_readonly_form').id,
            'target': 'new',
            'context': {
                'default_rejection_reason': self.rejection_reason,
            }
        }

    def action_reject(self):
        invalid_records = self.filtered(lambda r: r.volume_clocked != 0)
        if invalid_records:
            if len(self) == 1:
                raise UserError(
                    "Le rejet est impossible : le volume pointé de cette ligne doit être nul."
                )
            else:
                raise UserError(
                    "Le rejet est impossible : certaines lignes présentent un volume pointé différent de zéro."
                )
        self.write({'state': 'rejected'})

    def action_update(self):
        for line in self.search([("type", "=", "monthly"), ("is_clockable", "=", True)]):
            if line.date_start + relativedelta(months=line.volume_clocked + 1) == datetime.today().date() and line.state == "open":
                line.volume_clocked += 1

        lines_planned = self.search([("state", "=", "planned"), ("date_start", "<=", datetime.today().date())])
        lines_planned.state = "open"

        lines_done = self.search([("state", "=", "done"), ("date_end", ">", datetime.today().date())])
        lines_done.state = "open"

        lines_open = self.search([("state", "=", "open"), ("date_start", ">", datetime.today().date())])
        lines_open.state = "planned"

        lines_open = self.search([("state", "=", "open"), ("date_end", "<=", datetime.today().date())])
        lines_open.state = "done"

    def button_canceled(self):
        self.state = "canceled"

class HrAssignmentTimeclock(models.Model):
    _name = "hr.assignment.timeclock"

    def name_get(self):
        def _name_get(record):
            period = self._context.get("am") and " · AM" or self._context.get("pm") and " · PM" or ""
            return f"{record.date.strftime('%d/%m/%Y')}{period}"

        return [(record.id, _name_get(record)) for record in self]

    date = fields.Date("Date", default=lambda _: datetime.today())
    assignment_id = fields.Many2one("hr.assignment", string="Affectation")
    site_id = fields.Many2one("building.site", string="Affaire", related="assignment_id.site_id")
    line_ids = fields.One2many("hr.assignment.timeclock.line", "timeclock_id", string="Lignes")


class HrAssignmentTimeclock(models.Model):
    _name = "hr.assignment.timeclock.line"

    timeclock_id = fields.Many2one("hr.assignment.timeclock", string="Parent", ondelete="cascade")
    assignment_line_id = fields.Many2one("hr.assignment.line", string="Ligne d'affectation", ondelete="cascade")
    site_id = fields.Many2one("building.site", string="Affaire", related="assignment_line_id.site_id")
    date = fields.Date("Date", related="timeclock_id.date", store=True)
    job_category_id = fields.Many2one("hr.assignment.job.category", string="Catégorie", related="assignment_line_id.job_category_id", store=True)
    job_id = fields.Many2one("hr.job", string="Poste", related="assignment_line_id.job_id", store=True)
    employee_id = fields.Many2one("hr.employee", string="Employé", related="assignment_line_id.employee_id", store=True, ondelete="restrict")
    is_present = fields.Boolean("Présent(e)", default=True)
    hours = fields.Integer("Heures travaillées")
    has_surpassed_8 = fields.Boolean("> 8")
    reason = fields.Text("Motif")
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Validé'),
        ('canceled', 'Annulé')
    ], string="État", default='draft')
    decision = fields.Selection(
        selection=[
            ('pending', ' '),
            ('canceled', 'Annulation'),
            ('modified', 'Modification'),
        ],
        string='Decision',
        default='pending',
    )

    def action_validate(self):
        if self.state == 'canceled':
            raise UserError("Vous ne pouvez pas valider un pointage annulé.")
        elif self.decision == 'canceled':
            raise UserError("Une demande d'annulation a été soumise. Elle doit d'abord être validée par le Directeur Général avant toute validation finale.")
        elif self.decision == 'modified' and self.state != 'canceled':
            raise UserError("Une demande de modification a été soumise. Elle doit d'abord être validée par le Directeur Général avant toute validation finale.")
        elif self.state == 'validated':
            raise UserError("VALIDATION NON AUTORISÉE : Le pointage est déjà validé.")
        else:
            self.state = "validated"

    def action_cancel(self):
        if self.state != "validated" and self.decision != "canceled" and self.decision != "modified":
            return {
                'type': 'ir.actions.act_window',
                'name': 'Assistant d\'annulation du pointage',
                'res_model': 'hr.assignment.timeclock.line.updated',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_line_id': self.id,
                    'default_state': 'canceled',
                    'default_readonly_hours': True,
                }
            }
        elif self.decision == "canceled" and self.state != "canceled":
            raise ValidationError("ANNULATION NON AUTORISÉE : Une demande d'annulation a déjà été soumise et est en attente de validation par Mr le Directeur Général.")
        elif self.decision == "modified":
            raise ValidationError("ANNULATION NON AUTORISÉE : Une demande de modification a déjà été soumise et est en attente de validation par Mr le Directeur Général.")
        elif self.decision == "canceled" and self.state == "canceled":
            raise ValidationError("ANNULATION NON AUTORISÉE : Le pointage est déjà Annulé.")
        else:
            raise ValidationError("ANNULATION NON AUTORISÉE : Le pointage est déjà validé.")

    def action_update_timeclock(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assistant de modification du pointage',
            'res_model': 'hr.assignment.timeclock.line.updated',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
                'default_hours': self.hours,
                'default_state': 'updated',
                'default_readonly_hours': False,
            }
        }

    @api.constrains('hours')
    def _check_hours(self):
        for record in self:
            if record.hours < 0 or record.hours > 12:
                raise ValidationError(f"Les heures travaillées doivent être comprises entre 0 et 12.\n{record.employee_id.name}")

    @api.onchange('hours')
    def _onchange_hours(self):
        for record in self:
            if record.hours > 8:
                record.has_surpassed_8 = True
            else:
                record.has_surpassed_8 = False
                record.reason = None

    def button_is_present(self):
        self.is_present = not self.is_present

class HrAssignmentTimeClockLineUpdated(models.Model):
    _name = "hr.assignment.timeclock.line.updated"

    line_id = fields.Many2one('hr.assignment.timeclock.line')
    line_site_id = fields.Many2one('building.site', string='Affaire', related='line_id.site_id', store=True, index=True)
    line_job_id = fields.Many2one('hr.job', string='Poste', related='line_id.job_id', store=True, index=True)
    line_employee_id = fields.Many2one('hr.employee', string='Employé', related='line_id.employee_id', store=True, index=True)
    line_hours = fields.Integer(string='Anciennes Heures Travaillées', related='line_id.hours', store=True, index=True)
    hours = fields.Integer(string='Nouvelles Heures Travaillées')
    reason = fields.Text(string="Motif", required=True)
    state = fields.Selection([
        ('updated', 'Modification'),
        ('validated', 'Validation'),
        ('canceled', 'Annulation'),
    ], string='Type de Demande', default='draft')
    decision = fields.Selection([
        ('requested', 'Demandé'),
        ('validated', 'Validé'),
        ('rejected', 'Rejeté'),
    ], string='État', default='requested')

    readonly_hours = fields.Boolean(default=False)

    @api.constrains('hours')
    def _check_hours(self):
        for record in self:
            if record.hours < 0 or record.hours > 12:
                raise ValidationError(f"Les heures travaillées doivent être comprises entre 0 et 12.\n{record.line_employee_id.name}")
    
    def action_confirm(self):
        existing_record = self.env['hr.assignment.timeclock.line.updated'].search([
            ('line_id', '=', self.line_id.id),
            ('state', '=', self.state)
        ], limit=1)

        if not existing_record:
            self.create({
                'line_id': self.line_id.id,
                'hours': self.hours,
                'reason': self.reason,
                'state': self.state,
            })

        if self.state == "canceled":
            self.line_id.write({'decision': 'canceled'})
        elif self.state == "updated":
            self.line_id.write({'decision': 'modified'})

        return True
    
    def get_reason(self):
        canceled_reason = "Motif d\'annulation du pointage"
        updated_reason = "Motif de modification"
        if self.state == 'canceled':
            reason = canceled_reason
        else:
            reason = updated_reason

        view_id = self.env.ref('hr_assignment.view_form_timeclock_updated_reason').id

        return {
            'type': 'ir.actions.act_window',
            'name': reason,
            'res_model': 'hr.assignment.timeclock.line.updated',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_reason': self.reason,
            }
        }
    
    def action_validate(self):
        for record in self:
            record.decision = "validated"
            if record.state == "canceled":
                state = "canceled"
                decision = "canceled"
            else:
                state = "draft"
                decision = "pending"

            if record.line_id:
                record.line_id.write({
                    'hours': record.hours,
                    'state': state,
                    'decision': decision,
                })

    def action_rejecte(self):
        self.decision = "rejected"
        self.line_id.write({'decision': 'pending'})
        

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.depends("assignment_ids", "assignment_ids.state")
    def _compute_is_assigned(self):
        for employee in self:
            is_assigned = employee.assignment_ids.filtered(lambda line: line.state in ["pending", "open", "planned", "canceled"])
            employee.is_assigned = bool(is_assigned)

    is_assigned = fields.Boolean("Est affecté", compute="_compute_is_assigned", store=True)
    assignment_ids = fields.One2many("hr.assignment.line", "employee_id", string="Affectations")
    timeclock_ids = fields.One2many("hr.assignment.timeclock.line", "employee_id", string="Pointages")