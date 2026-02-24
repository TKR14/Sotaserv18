from odoo import models, fields, api
from odoo.exceptions import UserError


class IncidentMateriel(models.Model):
    _name = "incident.materiel"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Déclaration d'incidents matériels"
    _order = "date desc"

    site_id = fields.Many2one("building.site", string="Affaire", domain=lambda self: self._site_id_domain(), required=True, tracking=True)
    fleet_id = fields.Many2one("fleet.vehicle", string="Matériel", required=True, tracking=True)
    date = fields.Datetime(string="Date", required=True, default=fields.Datetime.now)
    type = fields.Selection([
        ('blocking', 'Bloquant'),
        ('non_blocking', 'Non Bloquant'),
    ], string="Type", required=True, tracking=True)
    description = fields.Text(string="Description")
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumis'),
        ('approved', 'Validée'),
        ('resolved', 'Traitée'),
        ('rejected', 'Rejetée'),
    ], string="Statut", default='draft', tracking=True)
    set_type = fields.Boolean(compute="_compute_set_type")

    def action_open_user_incident_materiel(self, group):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
            ("group_id.name", "=", group),
            ("active", "=", True)
        ])
        site_ids = profile_ids.mapped('site_id').ids

        domain = [
            ('site_id', 'in', site_ids)
        ]

        return {
            'name': 'Pointages',
            'type': 'ir.actions.act_window',
            'res_model': 'incident.materiel',
            'view_mode': 'lis,form',
            'views': [
                (self.env.ref('logistics.view_incident_materiel_tree').id, 'list'),
                (self.env.ref('logistics.view_incident_materiel_form').id, 'form'),
            ],
            'domain': domain,
        }

    def _site_id_domain(self):
        domain = []

        profile_assignments = self.env["building.profile.assignment"].search([
            ("user_id", "=", self.env.user.id),
            ("group_id.name", "=", "SOTASERV_CHEF_PROJET"),
        ])

        site_ids = profile_assignments.mapped("site_id").ids

        domain = [("id", "in", site_ids)]

        return domain
    
    @api.onchange('site_id')
    def _onchange_site_id(self):
        if not self.site_id:
            return {'domain': {'fleet_id': []}}

        assignment_lines = self.env['building.assignment.line'].search([
            ('site_id', '=', self.site_id.id),
        ])

        return {
            'domain': {
                'fleet_id': [('id', 'in', assignment_lines.mapped('vehicle_id').ids)]
            }
        }

    @api.depends('state')
    def _compute_set_type(self):
        for record in self:
            if record.state == 'draft':
                record.set_type = True
            elif record.state == 'submitted' and self.env.user.has_group('logistics.logistics_group'):
                record.set_type = True
            else:
                record.set_type = False

    def open_return_to_wizard(self):
        return {
            "name": "Assistant de retour",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cancellation.reason',
            'target': 'new',
        }

    def open_rejection_wizard(self):
        return {
            "name": "Assistant de rejet",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cancellation.reason',
            'target': 'new',
        }

    def submit_incident(self):
        for record in self:
            record.state = 'submitted'

    def draft_incident(self, reason=None):
        for record in self:
            record.state = 'draft'
            body = f"""
                <ul>
                    <li>Motif de Retour: {reason}</li>
                </ul>
                """
            self.message_post(body=body)
    
    def approve_incident(self):
        for record in self:
            record.state = 'approved'

    def return_to_submitted(self, reason=None):
        for record in self:
            record.state = 'submitted'
            body = f"""
                <ul>
                    <li>Motif de Retour: {reason}</li>
                </ul>
                """
            self.message_post(body=body)

    def resolve_incident(self):
        for record in self:
            record.state = 'resolved'

    def reject_incident(self, reason=None):
        for record in self:
            record.state = 'rejected'
            body = f"""
                <ul>
                    <li>Motif de Rejet: {reason}</li>
                </ul>
                """
            self.message_post(body=body)

    def unlink(self):
        not_draft = self.filtered(lambda r: r.state != 'draft')
        if not_draft:
            raise UserError(
                "Suppression interdite : seuls les incidents brouillon sont supprimables."
            )
        return super().unlink()

