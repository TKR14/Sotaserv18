from odoo import api, fields, models, _
from lxml import etree
import json
from odoo.exceptions import ValidationError, UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ice = fields.Char("ICE", size=15)
    taxpayer_account = fields.Char("Compte contribuable", size=15)
    regime_imposition = fields.Selection([
        ('normal', 'Réel Normal'),
        ('simplifie', 'Réel Simplifié'),
        ('tee', 'Impôt Synthétique – TEE'),
        ('rme', 'Impôt Synthétique – RME'),
    ], string="Régime d’Imposition", default='normal', required=True)

    taux_imposition = fields.Many2one("account.tax", string="Taux d'Imposition", domain="[('tax_group_id.name', '=', 'Retenue')]")
    completed_by_finance = fields.Boolean('Complété par la Finance', default= False)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('approved', 'Validé DAF'),
    ], default='draft', tracking=True)

    def open_set_to_draft_wizard(self):
        return {
            "name": "Assistant de retour",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cancellation.reason',
            'target': 'new',
        }

    def action_set_to_draft(self, reason=None):
        for record in self:
            record.state = 'draft'
            body = f"""
                <ul>
                    <li>Motif de Retour: {reason}</li>
                </ul>
                """
            self.message_post(body=body)

    def action_validate(self):
        for record in self:
            record.state = 'approved'

    ALWAYS_READONLY_FIELDS = ['on_time_rate', 'total_invoiced']

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ResPartner, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if toolbar and self._context.get('hide_actions'):
            if 'toolbar' in res and 'action' in res['toolbar']:
                res['toolbar']['action'] = []

        if view_type == 'form':
            doc = etree.XML(res['arch'])

            for node in doc.xpath("//field"):
                field_name = node.get('name')
                modifiers = json.loads(node.get("modifiers", "{}"))

                if field_name in self.ALWAYS_READONLY_FIELDS:
                    # ✅ Always readonly
                    modifiers['readonly'] = True
                else:
                    # ✅ readonly if state = approved
                    modifiers['readonly'] = [["state", "=", "approved"]]

                modifiers['no_open'] = True
                node.set("modifiers", json.dumps(modifiers))

            res['arch'] = etree.tostring(doc, encoding='unicode')

        return res

    def action_validate_finance(self):
        for record in self:
            record.completed_by_finance = True

    @api.onchange('regime_imposition')
    def _onchange_regime_imposition(self):
        if self.regime_imposition not in ['normal', 'simplifie']:
            purchase_lines = self.env["purchase.order.line"].search([('id', 'in', self.purchase_line_ids.ids)])
            for line in purchase_lines:
                line.taxes_id = [(6, 0, [])]

    @api.depends('regime_imposition')
    def _compute_taux_visibility(self):
        for record in self:
            record.taux_visible = record.regime_imposition in ['tee', 'rme']

    taux_visible = fields.Boolean(compute="_compute_taux_visibility")

    @api.constrains('name')
    def check_name(self):
        for partner in self:
            partner_id = self.env['res.partner'].search([('name', '=', partner.name),
            ('id', '!=', partner.id),
            ('customer_rank', '=', partner.customer_rank),
            ('supplier_rank', '=', partner.supplier_rank)])
            if partner_id:
                raise ValidationError(_('Il existe deja un partenaire avec le même nom %s!', partner.name))

    def action_get_suppliers(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids

        domain = [("supplier_rank", ">", 0)]

        return {
            "name": "Fournisseurs",
            "type": "ir.actions.act_window",
            "view_mode": "kanban,form,tree",
            "res_model": "res.partner",
            "views": [
                (self.env.ref("base.res_partner_kanban_view").id, "kanban"),
                (self.env.ref("base.view_partner_form").id, "form"),
                (self.env.ref("base.view_partner_tree").id, "list"),
                
            ],
            "domain": domain,
            "context": {
                "create": False,
                "edit": False,
                "delete": False,
            },
        }

    def action_get_clients(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids

        return {
            "name": "Clients",
            "type": "ir.actions.act_window",
            "view_mode": "kanban,form,tree",
            "res_model": "res.partner",
            "views": [
                (self.env.ref("base.res_partner_kanban_view").id, "kanban"),
                (self.env.ref("base.view_partner_form").id, "form"),
                (self.env.ref("base.view_partner_tree").id, "list"),
                
            ],
            "context": {
                "create": False,
                "edit": False,
                "delete": False,
            },
        }
    
    def write(self, values):
        tracked_fields = self.fields_get()
        messages = {}

        for record in self:
            changes = []

            for field, new_value in values.items():
                field_description = tracked_fields[field]['string']
                old_value = record[field] or ''

                if old_value != new_value:
                    field_type = record._fields[field].type

                    if field_type == 'many2one':
                        old_value = old_value.display_name if old_value else ''
                        new_value = self.env[record._fields[field].comodel_name].browse(new_value).display_name if new_value else ''
                        changes.append(f"<li>{field_description}: {old_value} ➡ {new_value}</li>")

                    elif field_type == 'one2many':
                        new_records = [op[2] for op in new_value if op[0] == 0] if new_value else []
                        if new_records:
                            new_value = ', '.join([rec.get('display_name', '') for rec in new_records if rec.get('display_name')]) 
                            changes.append(f"<li>{field_description} créé: {new_value}</li>")

                    elif field_type == 'selection':
                        selection_field = record._fields[field].selection
                        if callable(selection_field):
                            selection_values = dict(selection_field(record))
                        else:
                            selection_values = dict(selection_field)
                        old_value = selection_values.get(old_value, old_value)
                        new_value = selection_values.get(new_value, new_value)
                        changes.append(f"<li>{field_description}: {old_value} ➡ {new_value}</li>")

                    else:
                        changes.append(f"<li>{field_description}: {old_value} ➡ {new_value}</li>")

            if changes:
                messages[record] = f"<ul class='o_Message_trackingValues'>{''.join(changes)}</ul>"

        for record, message in messages.items():
            record.message_post(body=message, subtype_xmlid="mail.mt_note")

        return super(ResPartner, self).write(values)


class ResCompany(models.Model):
    _inherit = 'res.company'

    ice = fields.Char("ICE", size=15)
    taxpayer_account = fields.Char("Compte contribuable", size=15)
    mobile = fields.Char(string="Mobile")
    rccm = fields.Char(string="RCCM")
    niu_nemuro = fields.Char(string="NIU")
    cnps = fields.Char(string="CNPS")
    bank_account = fields.Char(string="Compte bancaire")
    capital = fields.Float(string="Capital")
    purchase_tolerance = fields.Float(string="Tolérance Achat")

    @api.onchange("purchase_tolerance")
    def _onchange_purchase_tolerance(self):
        if self.purchase_tolerance:
            if self.purchase_tolerance < 0 or self.purchase_tolerance > 100:
                raise UserError("La tolérance d'achat doit être comprise entre 0 et 100.")
