from odoo import models, _, api, fields, exceptions, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_is_zero

from datetime import datetime
from lxml import etree
import json
from itertools import groupby


def generate_code(sequence_number):
    """
    Generates a code with the prefix 'DDP', followed by the current year, month,
    and a sequence number.

    Args:
    sequence_number (int): The current sequence number.

    Returns:
    str: The generated code.
    """
    # Get the current year and month
    now = datetime.now()
    year = now.year
    month = f"{now.month:02d}"  # Format the month as a two-digit number with leading zeros
    
    # Format the sequence number, e.g., as a three-digit number with leading zeros
    sequence_str = f"{sequence_number:04d}"
    
    # Construct the final code
    code = f"DDP/{year}/{month}/{sequence_str}"
    
    return code

def get_next_sequence(env):
    """
    Fetches the next sequence number for a new purchase order based on the latest record.

    Args:
    env: Access to the Odoo environment (database and models).

    Returns:
    int: The next sequence number to be used.
    """
    # Get the current year and month
    now = datetime.now()
    year = now.year
    month = f"{now.month:02d}"  # Format the month as a two-digit number with leading zeros
    
    # Search for the latest purchase order with the pattern 'DDP/YEAR/MONTH/%'
    PurchaseOrder = env['purchase.order']
    pattern = f"DDP/{year}/{month}/%"
    latest_order = PurchaseOrder.search([('purchase_order_code', 'like', pattern)], order='id desc', limit=1)

    if not latest_order:
        # If no order is found, start the sequence at 1
        return 1

    # Extract the sequence number from the latest order purchase_order_code
    last_code = latest_order.purchase_order_code
    # Assuming the sequence is always the last 4 digits after the last '/'
    last_sequence = int(last_code.split('/')[-1])

    # Return the next sequence number
    return last_sequence + 1

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    show_detail_button = fields.Boolean()

    purchase_order_code = fields.Char("Référence Comparaison")
    is_po_multiple = fields.Boolean(default=False)
    button_confirm_visibility = fields.Boolean(compute="_compute_buttons_visibility")
    button_cancel_multi_visibility = fields.Boolean(compute="_compute_buttons_visibility")
    button_cancel_visibility = fields.Boolean(compute="_compute_buttons_visibility")
    button_po_canceled_visibility = fields.Boolean(compute="_compute_buttons_visibility")
    is_ppc_created = fields.Boolean()
    partner_ids = fields.Many2many("res.partner", compute="_compute_partner_ids")
    is_signed = fields.Boolean("Signé", default=False)
    return_to_mg = fields.Boolean(default=False, readonly=True)
    is_attachment = fields.Boolean(string="Attachement", default=False, tracking=True)
    is_done = fields.Boolean(string="Done", default=False)
    state = fields.Selection([
        ("draft", "DP Établie"),
        ("compare_offers", "Compare Offres"),
        ("validated_1", "Validé par Acheteur"),
        ("validation", "Attente Validation DG"),
        ("validated_2", "Validé par DG"),
        ("purchase", "Commande Établie"),
        ("partial", "Partiellement Réceptionnée"),
        ("full", "Totalement Réceptionnée"),
        ("done", "Commande Clôturée"),
        ("cancel", "DP Annulée"),
        ("po_canceled", "Commande Annulée"),

        ("sent", "DP Envoyée"),
        ("to approve", "À approuver"),
        ("validated", "Validée"),
    ], translate=False)

    state_2 = fields.Selection([
        ("draft", "Brouillon"),
        ("validated", "Soumettre à l'approbation"),
        ("approved", "Approuvée"),
    ], string="Pré-statut", default="draft")

    situation = fields.Selection([
        ('rien_a_facturer', 'Rien à facturer'),
        ('attachement_etablie', 'Attachement établie'),
        ('attachement_valide', 'Attachement validé'),
        ('decompte_a_etablir', 'Décompte à établir'),
        ('completement_facture', 'Complètement facturé'),
    ], string='Situation', default='rien_a_facturer')

    establish_by = fields.Many2one('res.users')
    validated_by = fields.Many2one('res.users')
    establish_count_by = fields.Many2one('res.users')
    fully_charged_by = fields.Many2one('res.users')

    reason = fields.Char(string="Motif")

    avance = fields.Float(string="Avance")
    return_of_guarantee = fields.Float(string="Retenue de garantie")

    responsible_for_cancellation = fields.Many2one("res.users", "Responsable de l'annulation")
    pr_ref = fields.Char("Référence DP")

    is_advance_invoice_created = fields.Boolean(compute="_compute_is_advance_invoice_created", default=False)
    is_rg_invoice_created = fields.Boolean(default=False)

    show_create_advance_button = fields.Boolean(
        compute="_compute_show_create_invoice_button"
    )

    is_service = fields.Boolean(compute="_compute_is_service", store=True)
    all_qty_validated = fields.Boolean(compute="_compute_all_qty_validated")
    all_qty_certified = fields.Boolean(compute="_compute_all_qty_certified")
    is_certified = fields.Boolean("Certifié ", default=False, readonly=True)

    remaining_advance = fields.Float(string="Reliquat d'avance", compute="_compute_remaining_advance")
    advance_accumulation = fields.Float(string="Cumul d'avance", compute="_compute_advance_accumulation")
    amount_advance_deduction = fields.Float(string="Déduction d'avance", tracking=True)
    is_cg = fields.Boolean(compute="_compute_is_cg")

    def open_cancellation_reason_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Assistant d'Annulation",
            "res_model": "cancellation.reason",
            "view_mode": "form",
            "target": "new",
        }

    @api.depends("is_cg")
    def _compute_is_cg(self):
        for order in self:
            order.is_cg = False
            if self.env.user.has_group("account_plus.acount_move_group_cg"):
                order.is_cg = True

    def _compute_advance_accumulation(self):
        self.advance_accumulation = sum(self.env["account.move"].search([("invoice_origin", "=", self.name)]).mapped("avance"))

    @api.depends("amount_advance_deduction")
    def _compute_remaining_advance(self):
        for order in self:
            order.remaining_advance = 0
            order_id = self
            if order_id.avance:
                order.remaining_advance = order_id.amount_total * order_id.avance / 100 - (sum(self.env["account.move"].search([("invoice_origin", "=", order_id.name)]).mapped("avance")) + self.amount_advance_deduction)


    @api.depends("is_attachment", "order_line.qty_received")
    def _compute_all_qty_validated(self):
        for purchase in self:
            purchase.all_qty_validated = True
            for line in purchase.order_line:
                if line.qty_received != line.qty_validated or line.qty_validated == 0:
                    purchase.all_qty_validated = False

    @api.depends("is_attachment", "order_line.qty_received")
    def _compute_all_qty_certified(self):
        for purchase in self:
            purchase.all_qty_certified = True
            for line in purchase.order_line:
                if line.qty_received != line.qty_certified or line.qty_certified == 0:
                    purchase.all_qty_certified = False

    @api.depends("is_attachment")
    def _compute_is_service(self):
        for purchase in self:
            purchase.is_service = False
            for line in purchase.order_line:
                if line.product_type == "service":
                    purchase.is_service = True

    @api.depends('user_id')
    def _compute_show_create_invoice_button(self):
        current_user_id = self.env.uid
        for order in self:
            is_different_user = order.user_id.id != current_user_id
            if is_different_user or any(order.picking_ids.filtered(lambda p: p.state == 'done')):
                order.show_create_advance_button = True
            else:
                order.show_create_advance_button = False

    @api.model
    def fields_get(self, fields=None):
        result = super(PurchaseOrder, self).fields_get(fields)

        field = self._context.get('hide_field', False)

        if field and field in result:
            result[field]["searchable"] = False
            result[field]["sortable"] = False
            result[field]["required"] = False

        return result


    # @api.onchange('payment_term_id', 'payment_method_id', 'delivery_method', 
    #               'guaranty_str', 'delivery_time', 'available_str', 
    #               'price_comparison_id', 'fiscal_position_id')
    # def _check_empty_fields(self):
    #     empty_fields = []
    #     fields_to_check = [
    #         ('payment_term_id', "Conditions de paiement"),
    #         ('payment_method_id', "Moyen de paiement"),
    #         ('delivery_method', "Mode de livraison"),
    #         ('guaranty_str', "Garantie"),
    #         ('delivery_time', "Délai de livraison"),
    #         ('available_str', "Disponibilité"),
    #         ('price_comparison_id', "Comparaison"),
    #         ('fiscal_position_id', "Position fiscale")
    #     ]

    #     for field, field_label in fields_to_check:
    #         if not self[field]:
    #             empty_fields.append(field_label)

    #     if empty_fields:
    #         return {
    #             'warning': {
    #                 'title': _("Champs vides"),
    #                 'message': _("Les champs suivants sont laissés vides : %s") % ", ".join(empty_fields),
    #             }
    #         }

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        
        context = self.env.context
        if context.get("method") == "button_po_canceled":
            return res

        self._check_empty_fields()
        return res

    @api.onchange('avance', 'payment_term_id', 'payment_method_id', 'delivery_method', 
                  'guaranty_str', 'delivery_time', 'available_str', 
                  'price_comparison_id', 'fiscal_position_id', 'order_line')
    def _check_empty_fields(self):
        empty_fields = []
        fields_to_check = [
            ('avance', "Avance"),
            ('payment_term_id', "Conditions de paiement"),
            ('payment_method_id', "Moyen de paiement"),
            ('delivery_method', "Mode de livraison"),
            ('guaranty_str', "Garantie"),
            ('delivery_time', "Délai de livraison"),
            ('available_str', "Disponibilité"),
            ('price_comparison_id', "Comparaison"),
            ('fiscal_position_id', "Position fiscale")
        ]

        for field, field_label in fields_to_check:
            if not self[field]:
                empty_fields.append(field_label)

        for line in self.order_line:
            if not line.price_unit:
                empty_fields.append("Prix unitaire")

        if empty_fields:
            return {
                'warning': {
                    'title': _("Champs vides"),
                    'message': _("Les champs suivants sont laissés vides : %s") % ", ".join(empty_fields),
                }
            }

    @api.model
    def default_get(self, fields):
        res = super(PurchaseOrder, self).default_get(fields)
        if self.env.context.get('form_view_initial_mode') == 'edit':
            self._check_empty_fields()
        return res
    
    @api.model
    def action_get_user_purchase_orders_with_attachments(self, group, readonly=False, nocreate=False):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
            # ('group_id.name', '=', group)
        ])
        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'group': group,
            'search_default_group_by_requested_by': 1,
            'edit': False,
            'create': not nocreate,
            'delete': not nocreate,
            'group_by': ['state_2'], 
            'hide_field': 'state'
        }

        if group == "SOTASERV_DIRECTRICE_TECHNIQUE" or group == "SOTASERV_AUDITEUR":
            domain = [('is_attachment', '=', True)]
        else:
            domain = [
                ('is_attachment', '=', True),
                ('site_id', 'in', site_ids)
            ]

        return {
            'name': 'Bons de commande avec attachement',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'views': [
                (self.env.ref('purchase_plus.purchase_order_tree').id, 'tree'),
                (self.env.ref('purchase_plus.purchase_order_line_attachment_form').id, 'form')
            ],
            'domain': domain,
            'context': context,
        }

    @api.model
    def action_get_project_manager_orders(self, group, readonly=False, nocreate=False):
        user_id = self.env.user.id
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', user_id),
            # ('group_id.name', '=', group)
        ])
        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'edit': False,
            'create': not nocreate,
            'delete': not nocreate,
            'group_by': ['state_2'], 
            'hide_field': 'state'
        }

        domain = [
            '&', 
            ('is_attachment', '=', True),
            '|',
            ('create_uid', '=', user_id),
            ('order_line.product_id.categ_id.supervisor_ids', 'in', [user_id])
        ]

        return {
            'name': 'Bons de commande avec attachement',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'views': [
                (self.env.ref('purchase_plus.purchase_order_tree').id, 'tree'),
                (self.env.ref('purchase_plus.purchase_order_line_attachment_form').id, 'form')
            ],
            'domain': domain,
            'context': context,
        }
    
    @api.model
    def action_get_dz_orders(self, group):
        user_id = self.env.user.id
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', user_id),
            # ('group_id.name', '=', group)
        ])
        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'edit': False,
            'create': False,
            'delete': False,
            'group_by': ['state_2'], 
            'hide_field': 'state'
        }

        domain = [
            '&',
            ('is_attachment', '=', True),
            ('site_id', 'in', site_ids),
        ]

        return {
            'name': 'Bons de commande avec attachement',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'views': [
                (self.env.ref('purchase_plus.purchase_order_tree').id, 'tree'),
                (self.env.ref('purchase_plus.purchase_order_line_attachment_form').id, 'form')
            ],
            'domain': domain,
            'context': context,
        }
    
    @api.constrains('avance', 'return_of_guarantee')
    def _check_avance_retenue(self):
        for record in self:
            if record.avance < 0 or record.avance > 100:
                raise ValidationError("La valeur de 'Avance' doit être comprise entre 0 et 100.")
            if record.return_of_guarantee < 0 or record.return_of_guarantee > 100:
                raise ValidationError("La valeur de 'Retenue de garantie' doit être comprise entre 0 et 100.")
    
    def _check_step_2(self, button):
        user = self.env["res.users"].browse(self.write_uid.id)
        approval_chain_line = self.env["approval.chain.line"].search([("step_1", "=", user.id), ("parent_id.model_id", "=", self._name)])
        allowed_uids = approval_chain_line.mapped("step_2")

        if self.env.user not in allowed_uids:
            raise ValidationError(f"Vous n'êtes pas autorisé à {button} cette demande.\n\nAucune chaîne d'approbation ne ressemble à celle-ci:\n{user.name} ─ Vous")

    def action_set_attachement_etablie(self):
        self.write({'situation': 'attachement_etablie', 'establish_by': self.env.user.id})

    def action_set_attachement_valide(self):
        self.write({'situation': 'attachement_valide', 'validated_by': self.env.user.id})

    def action_set_decompte_a_etablir(self):
        self.write({'situation': 'decompte_a_etablir', 'establish_count_by': self.env.user.id})

    def action_set_completement_facture(self):
        self.write({'situation': 'completement_facture', 'fully_charged_by': self.env.user.id})

    def action_validation_quantity(self):
        for line in self.order_line:
            message = f"""
            <strong>La quantité validé a été mise à jour.</strong>
            <ul>
                <li>
                {line.product_id.name}:
                <br />
                Quantité validé: {line.qty_validated} -> {line.qty_received}
                </li>
            </ul>
            """
            line.qty_validated = line.qty_received
            self.message_post(body=message)

    def action_certification_quantity(self):
        for line in self.order_line:
            message = f"""
            <strong>La quantité certifié a été mise à jour.</strong>
            <ul>
                <li>
                {line.product_id.name}:
                <br />
                Quantité certifié: {line.qty_certified} -> {line.qty_validated}
                </li>
            </ul>
            """
            line.qty_certified = line.qty_validated
            self.message_post(body=message)
            self.button_done()

    def action_return_quantity(self):
        for line in self.order_line:
            message = f"""
            <strong>La quantité validé a été remis.</strong>
            <ul>
                <li>
                {line.product_id.name}:
                <br />
                Quantité validé: {line.qty_validated} -> {line.qty_invoiced}
                </li>
            </ul>
            """
            line.qty_validated = line.qty_certified = line.qty_invoiced
            
            self.message_post(body=message)
            # self.is_validated = False
    
    def action_amount_advance_deduction_verification(self):
        if self.avance and self.amount_advance_deduction == 0 and self.remaining_advance != 0:
            return {
                "type": "ir.actions.act_window",
                "name": "Avertissement",
                "res_model": "purchase.order",
                "res_id": self.id,
                "view_mode": "form",
                "view_id": self.env.ref("purchase_plus.purchase_order_modal_view").id,
                "target": "new",
            }
        else:
            self.action_certification_quantity()

    @api.onchange('amount_advance_deduction')
    def _check_amount_advance_deduction(self):
        if self.amount_advance_deduction > (self.remaining_advance + self.amount_advance_deduction):
                raise ValidationError("La déduction d'avance ne peut pas dépasser le reliquat d'avance.")

    @api.constrains('amount_advance_deduction')
    def _check_amount_advance(self):
        for rec in self:
            if rec.is_attachment == False and rec.is_service == True and rec.amount_advance_deduction > (rec.remaining_advance + rec.amount_advance_deduction):
                raise ValidationError("La déduction d'avance ne peut pas dépasser le reliquat d'avance.")

    def update_old_seqs(self):
        records = self.env["purchase.order"].search([("purchase_order_code", "!=", None)], order='create_date asc')
        purchase_order_codes = []

        for r in records:
            if r.purchase_order_code not in purchase_order_codes:
                purchase_order_codes.append(r.purchase_order_code)

        for purchase_order_code in purchase_order_codes:
            sequence_number = get_next_sequence(self.env)
            code = generate_code(sequence_number)
            new_purchase_order_code = code

            pos = self.env["purchase.order"].search([("purchase_order_code", "=", purchase_order_code)])
            for po in pos:
                po.purchase_order_code = new_purchase_order_code

            ppcs = self.env["purchase.price.comparison"].search([("purchase_order_code", "=", purchase_order_code)])
            for ppc in ppcs:
                ppc.purchase_order_code = new_purchase_order_code

            prls = self.env["purchase.request.line"].search([("purchase_order_code", "=", purchase_order_code)])
            for prl in prls:
                prl.purchase_order_code = new_purchase_order_code

    @api.depends("partner_id")
    def _compute_partner_ids(self):
        env = self.env["res.partner"]
        partner_ids = env.search(['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)])
        if self.is_po_multiple:
            used_partners = self.env["purchase.order"].search([("purchase_order_code", "=", self.purchase_order_code)]).mapped("partner_id")
            partner_ids = partner_ids.filtered(lambda partner:partner.id not in used_partners.ids)
        self.partner_ids = partner_ids.ids

    @api.depends("state", "is_po_multiple")
    def _compute_buttons_visibility(self):
        for rec in self:
            rec.button_cancel_visibility = False
            count_stock_pickings = self.env["stock.picking"].search_count([("purchase_id", "=", rec.id), ("state", "=", "done")])
            if (rec.state not in ["compare_offers", "cancel", "po_canceled"]) and not count_stock_pickings:
                rec.button_cancel_visibility = True

            # advance_invoice = self.env['account.move'].search([('site_id', '=', self.site_id.id), ('invoice_origin', '=', self.name), ('state', '!=', 'draft')])
            # if advance_invoice:
            #     rec.button_cancel_visibility = False

            attachements = self.env["purchase.entry"].search_count([("purchase_id", "=", rec.id)])
            if rec.is_attachment and attachements == 0 and rec.state not in ["cancel", "po_canceled"]:
                rec.button_cancel_visibility = True
 
            if (rec.state in ["draft", "validated"] and rec.is_po_multiple == False and (rec.responsible_for_cancellation.id == self.env.user.id or self.env.user.has_group("building_plus.sotaserv_dg"))) or rec.state == "validated" and (rec.responsible_for_cancellation.id == self.env.user.id or self.env.user.has_group("building_plus.sotaserv_dg")):
                rec.button_confirm_visibility = True
            else:
                rec.button_confirm_visibility = False

            if rec.state in ["draft", "validation", "validated"] and rec.is_po_multiple == True and (rec.responsible_for_cancellation.id == self.env.user.id or self.env.user.has_group("building_plus.sotaserv_dg")):
                rec.button_cancel_multi_visibility = True
            else:
                rec.button_cancel_multi_visibility = False

            if rec.state == "purchase" and rec.is_po_multiple == True and (rec.responsible_for_cancellation.id == self.env.user.id or self.env.user.has_group("building_plus.sotaserv_dg")):
                rec.button_po_canceled_visibility = True
            else:
                rec.button_po_canceled_visibility = False

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        result = super(PurchaseOrder, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        
        arch = etree.fromstring(result["arch"])
        arch.set("create", "false")
        arch.set("delete", "false")
        result["arch"] = etree.tostring(arch)
        doc = etree.XML(result['arch'])

        if view_type == 'form':
            
            readonly_fields = ['site_id', 'partner_id', 'purchase_order_code', 'offer_validity_date_planned', 'is_signed', 'offer_validity', 'date_planned', 'mail_reminder_confirmed', 'receipt_reminder_email', 'user_id', 'picking_type_id', 'incoterm_id', 'payment_term_id']

            for node in doc.xpath("//field"):
                domain = [('state', '!=', "draft")]
                attr = json.loads(node.attrib.get('modifiers'))

                if node.attrib.get('name') in readonly_fields:
                    attr['readonly'] = True
                    node.set('modifiers', json.dumps(attr))
                elif node.attrib.get('modifiers') and node.attrib.get('name') not in ['name', 'is_attachment', 'avance', 'return_of_guarantee', 'order_line', 'price_unit', 'amount_advance_deduction']:
                    if attr.get('readonly'):
                        value_readonly = attr.get('readonly')
                        if str(attr.get('readonly')) != "True":
                            value_readonly.insert(0, "|")
                            domain = value_readonly + domain
                    attr['readonly'] = domain
                    node.set('modifiers', json.dumps(attr))
        if toolbar:
            if self._context.get('hide_actions'):
                result['toolbar']['action'] = []
            else:
                pass
        result['arch'] = etree.tostring(doc)

        return result

    def _check_order_line_price_unit(self):
        if 0 in self.order_line.mapped("price_unit"):
            raise UserError("Assurez-vous de saisir les prix unitaires des lignes.")

    def button_validate(self):
        self._check_order_line_price_unit()

        if self.state in ["draft", "compare_offers"]:
            for line in self.order_line:
                need_line = line._get_need_line()
                if (line.price_unit != need_line.price_unit) or (line.price_unit != line.product_id.product_tmpl_id.reference_price):
                    self.state = "validation"
                    return
            self.state = "validated_1"

        if self.state == "validation":
            lines = []
            for line in self.order_line:
                need_line = line._get_need_line()
                if (line.price_unit != need_line.price_unit) or (line.price_unit != line.product_id.product_tmpl_id.reference_price):
                    lines.append([0, 0, {"order_line_id": line.id, "need_price": need_line.price_unit}])

            return {
                "name": "Validation",
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_model": "purchase.order.validation.wizard",
                "target": "new",
                "context": {
                    "default_order_id": self.id,
                    "default_site_id": self.site_id.id,
                    "default_currency_id": self.currency_id.id,
                    "default_line_ids": lines,
                },
            }

    @api.depends('name')
    def _compute_is_advance_invoice_created(self):
        for rec in self:
            invoice = self.env['account.move'].search([('invoice_origin', '=', self.name)])
            rec.is_advance_invoice_created = bool(invoice)
    
    def create_advance_invoice(self):
        if self.avance > 0:
            account = self.env['account.account'].search([('code', '=', '4093000')], limit=1)

            price_unit = (self.amount_untaxed * self.avance) / 100

            move_type = self.env['account.move.type'].search([('name', '=', 'Avance')], limit=1)
            
            invoice_vals = {
                'move_type': 'in_invoice',
                'partner_id': self.partner_id.id,
                'journal_id': 2,
                'site_id': self.site_id.id if self.site_id else False,
                'ref': f"Avance, {self.name}",
                'currency_id': self.currency_id.id,
                'invoice_date': datetime.today(),
                'invoice_origin': self.name,
                'invoice_payment_term_id': self.payment_term_id.id,
                'date': datetime.today(),
                'invoice_type': 'advance',
                'move_type_id': move_type.id if move_type else False,
                'invoice_line_ids': [
                    (0, 0, {
                        'account_id': account.id,
                        'price_unit': price_unit,
                        'quantity': 1,
                        'tax_ids': self.order_line[0].taxes_id,
                        'exclude_from_invoice_tab': False,
                        'credit': 0,
                    }),
                ],
            }
            invoice = self.env['account.move'].create(invoice_vals)
            invoice.recompute_dynamic_lines()

    def button_confirm(self, escape=False):        
        self._purchase_request_line_check()

        for order in self:
            if order.state not in ["validated_1", "validated_2"]:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                name = self.env["ir.sequence"].next_by_code("purchase.order.sequence.order")
                self.write({
                    "name": name,
                    "state": "purchase",
                    "pr_ref": self.name,
                })
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        self._purchase_request_confirm_message()

        for order in self:
            for line in order.order_line:
                for request_line in line.purchase_request_lines:
                    request_line.purchase_order_code = order.purchase_order_code
                    request_line.state = "order_established"
                    request_line.supplier_id = order.partner_id

        return True

    # def _create_picking(self):
    #     StockPicking = self.env['stock.picking']
    #     for order in self.filtered(lambda po: po.state in ('purchase', 'done')):
    #         if any(product.type in ['product', 'consu'] for product in order.order_line.product_id):
    #             order = order.with_company(order.company_id)
    #             pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
    #             if not pickings:
    #                 res = order._prepare_picking()
                    
    #                 picking = StockPicking.with_user(SUPERUSER_ID).create(res)
    #                 raise Exception(picking.read())
    #             else:
    #                 picking = pickings[0]
    #             moves = order.order_line._create_stock_moves(picking)
    #             moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
    #             seq = 0
    #             for move in sorted(moves, key=lambda move: move.date):
    #                 seq += 5
    #                 move.sequence = seq
    #             moves._action_assign()
    #             picking.message_post_with_view('mail.message_origin_link',
    #                 values={'self': picking, 'origin': order},
    #                 subtype_id=self.env.ref('mail.mt_note').id)
    #     raise Exception("##")
        
    #     return True

    def button_done(self):
        if not self.is_service:
            is_partial = any(stock.state == "assigned" for stock in self.picking_ids) and any(line.qty_received != 0 for line in self.order_line)
            if is_partial:
                self.write({"state": "partial", "priority": "0"})
            is_full = all(line.qty_received >= line.product_qty for line in self.order_line) or (all(stock.state != "assigned" for stock in self.picking_ids) and any(line.qty_invoiced < line.qty_received for line in self.order_line))
            if is_full:
                self.write({"state": "full", "priority": "0"})
            is_done = all(line.qty_invoiced == line.qty_received for line in self.order_line) and all(stock.state != "assigned" for stock in self.picking_ids) and any(line.qty_received > 0 for line in self.order_line)
            if is_done:
                request_lines = self.env["purchase.request.line"].search([
                    ("purchase_lines", "in", self.order_line.ids)
                ])
                request_lines.state = "order_done"
                self.write({"state": "done", "priority": "0"})
        else:
            is_partial = any(line.product_qty > line.qty_received for line in self.order_line)
            if is_partial:
                self.write({"state": "partial", "priority": "0"})
            is_full = all(line.product_qty <= line.qty_received for line in self.order_line)
            if is_full:
                self.write({"state": "full", "priority": "0"})
            is_done = all(line.product_qty <= line.qty_received and line.qty_received == line.qty_invoiced for line in self.order_line)
            if is_done:
                request_lines = self.env["purchase.request.line"].search([
                    ("purchase_lines", "in", self.order_line.ids)
                ])
                request_lines.state = "order_done"
                self.write({"state": "done", "priority": "0"})

    def _update_state_from_purchase_entry(self):
        entries = self.env["purchase.entry"].search([("purchase_id", "=", self.id)])
        entries = entries.sorted("create_date", reverse=True)
        latest, *rest = entries
        entry = rest[0] if latest.state_attachemnet == "draft" and rest else latest

        executed = entry.executed
        state_attachemnet = entry.state_attachemnet
        state_decompte = entry.state_decompte
        is_done = entry.is_done
        
        self.write({
            "state": "purchase",
            "is_done": False,
        })
        if state_attachemnet == "internal_validated":
            if executed > 0:
                self.state = "partial"
            if (executed == 100 or is_done):
                if state_decompte != "bill":
                    self.state = "full"
                else:
                    self.write({
                        "state": "done",
                        "is_done": True,
                    })

    def button_print_report(self):
        return self.env.ref("purchase_igaser.purchase_order_report").report_action(self)

    def check_picking_certified(self):
        for order in self:
            done_pickings = order.picking_ids.filtered(lambda p: p.state == 'done')
            all_certified = all(p.certification_state == 'certified' for p in done_pickings)
            
            if all_certified:
                return True 
            else:
                return False
            
    @api.depends('state', 'order_line.qty_to_invoice')
    def _get_invoiced(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for order in self:
            if order.state not in ('purchase', 'done', 'partial', 'full'):
                order.invoice_status = 'no'
                continue

            if any(
                not float_is_zero(line.qty_to_invoice, precision_digits=precision)
                for line in order.order_line.filtered(lambda l: not l.display_type)
            ):
                order.invoice_status = 'to invoice'
            elif (
                all(
                    float_is_zero(line.qty_to_invoice, precision_digits=precision)
                    for line in order.order_line.filtered(lambda l: not l.display_type)
                )
                and order.invoice_ids
            ):
                order.invoice_status = 'invoiced'
            else:
                order.invoice_status = 'no'

    def action_create_invoice(self, picking_ids=False, reception=False, advance=None):
        """Create the invoice associated to the PO.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # 1) Prepare invoice vals and clean-up the section lines
        invoice_vals_list = []
        sequence = 10

        # for order in self:
        #     if not order.check_picking_certified():
        #         raise UserError(_('Cette commande n\'est pas certifiée. Veuillez contacter le "Contrôle de Gestion" pour approbation.'))

        # raise Exception([(line.product_qty, line.qty_invoiced) for line in self.order_line])
        for order in self:
            # raise Exception("#")
            if order.invoice_status != 'to invoice':
                continue
            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order._prepare_invoice()
            # Invoice line values (keep only necessary sections).
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    if pending_section:
                        line_vals = pending_section._prepare_account_move_line(picking_ids=picking_ids, move=self.env['account.move']._origin)
                        line_vals.update({'sequence': sequence})
                        invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                        sequence += 1
                        pending_section = None
                    line_vals = line._prepare_account_move_line(picking_ids=picking_ids, move=self.env['account.move']._origin)
                    line_vals.update({'sequence': sequence})
                    if line_vals.get('quantity', 0) > 0 and line_vals.get('price_unit', 0) > 0:
                        invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                        sequence += 1
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise UserError(_('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

        # 2) group by (company_id, partner_id, currency_id) for batch creation
        new_invoice_vals_list = []
        for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
            origins = set()
            payment_refs = set()
            refs = set()
            ref_invoice_vals = None
            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                origins.add(invoice_vals['invoice_origin'])
                payment_refs.add(invoice_vals['payment_reference'])
                refs.add(invoice_vals['ref'])
            move_type_reception = self.env['account.move.type'].search([('name', '=', 'Fourniture_Réception')], limit=1)
            move_type_without_attachment = self.env['account.move.type'].search([('name', '=', 'Service sans attachement')], limit=1)
            ref_invoice_vals.update({
                'ref': ', '.join(refs)[:2000],
                'move_type_id': move_type_reception.id if reception else move_type_without_attachment.id,
                'avance': advance if advance else self.amount_advance_deduction,
                'return_of_guarantee': (self.amount_untaxed * self.return_of_guarantee) / 100,
                "invoice_payment_term_id": self.payment_term_id.id,
                'invoice_origin': ', '.join(origins),
                'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
            })
            new_invoice_vals_list.append(ref_invoice_vals)
        invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()

        moves.recompute_dynamic_lines()

        self.write({"amount_advance_deduction": 0})
        
        for order in self:
            order.button_done()
        return moves

        # return self.action_view_invoice(moves)

    def button_sign(self):
        if self.state in ["purchase", "done", "full"]:
            self.is_signed = True

    def button_certif(self):
        self.is_certified = True

    def update_ventilate(self):
        for po in self.env["purchase.order"].search([("is_attachment", "=", True)]):
            for line in po.order_line:
                line._compute_ventilate()

    def button_return_to_mg(self):
        self.sudo().write({"return_to_mg": True})

        if self.picking_ids:
            self.picking_ids.sudo().write({"return_to_mg": True})
    
    def action_validated(self):
        problematic_lines = [
            line for line in self.order_line if line.ventilate > 0
        ]

        if problematic_lines:
            line_info = "\n".join(
                [line.product_id.display_name for line in problematic_lines]
            )
            raise ValidationError(
                "La transition vers l'état 'validé' est interdite lorsque des lignes de commande ont un champ 'ventilate' supérieur à 0. "
                "Veuillez vérifier les articles suivants : {}".format(line_info)
            )

        self.write({'state_2': 'validated'})

    def open_back_to_draft_reason_wizard(self):
        return {
            "name": "Assistant de retour",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cancellation.reason',
            'target': 'new',
        }

    def action_back_to_draft(self, reason=None):
        self._check_step_2(button='Remettre')
        self.write({'state_2': 'draft'})
        body = f"""
        <ul>
          <li>Motif de retour: {reason}</li>
        <ul/>
        """
        self.message_post(body=body)

    @api.onchange('is_attachment')
    def onchange_is_done(self):
        for record in self:
            if record.is_attachment:
                return {
                    'warning': {
                        'title': 'Confirmation',
                        'message': 'Êtes-vous sûr de vouloir marquer ce bon de commande avec un attachement comme terminé?',
                    }
                }
            else:
                return {
                    'warning': {
                        'title': 'Confirmation',
                        'message': 'Êtes-vous sûr de vouloir réinitialiser l\'état de ce bon de commande sans attachement?',
                    }
                }

    def toggle_is_attachment(self):
        for record in self:
            record.is_attachment = not record.is_attachment

    def action_approved(self):
        if not self.avance:
            return {
                'name': 'Confirmation Requise',
                'type': 'ir.actions.act_window',
                'res_model': 'alert.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': self.env.context,
            }
        
        if not self.return_of_guarantee:
            return {
                'name': 'Confirmation Requise',
                'type': 'ir.actions.act_window',
                'res_model': 'alert.return.guarantee.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': self.env.context,
            }
        
        if self.avance and self.return_of_guarantee:
            self.write({'state_2': 'approved'})

    # def create_rg_invoice(self):
    #     if self.return_of_guarantee > 0:
    #         self.is_rg_invoice_created = True
    #         self.write({'state_2': 'approved'})

    #         move_type = self.env['account.move.type'].search([('name', '=', 'Libération RG')], limit=1)

    #         invoice_vals = {
    #             'move_type': 'in_invoice',
    #             'partner_id': self.partner_id.id,
    #             'journal_id': 2,
    #             'site_id': self.site_id.id if self.site_id else False,
    #             'ref': f"RG, {self.name}",
    #             'invoice_date': datetime.today(),
    #             'invoice_origin': self.name,
    #             'date': datetime.today(),
    #             'move_type_id': move_type.id if move_type else False,
    #             'invoice_line_ids': [
    #                 (0, 0, {
    #                     'account_id': self.env['account.account'].search([('code', '=', '4817000')], limit=1).id,
    #                     'price_unit': (self.amount_untaxed * self.return_of_guarantee) / 100,
    #                     'quantity': 1,
    #                     'tax_ids': self.order_line[0].taxes_id,
    #                     'exclude_from_invoice_tab': False,
    #                     'credit': 0,
    #                 }),
    #                 (0, 0, {
    #                     'account_id': self.env['account.account'].search([('code', '=', '4013000')], limit=1).id,
    #                     'exclude_from_invoice_tab': True,
    #                 }),
    #             ], 
    #         }
        
    #         invoice = self.env['account.move'].create(invoice_vals)
    #         invoice._recompute_dynamic_lines()

class AlerReturnWizard(models.TransientModel):
    _name = 'alert.return.guarantee.wizard'

    def action_confirm(self):
        active_id = self._context.get('active_id')
        record = self.env['purchase.order'].browse(active_id)
        if not record.return_of_guarantee:
            record.write({'state_2': 'approved'})

class AlertWizard(models.TransientModel):
    _name = 'alert.wizard'

    def action_confirm(self):
        active_id = self._context.get('active_id')
        record = self.env['purchase.order'].browse(active_id)
        if not record.return_of_guarantee:
            return {
                'name': 'Confirmation Requise',
                'type': 'ir.actions.act_window',
                'res_model': 'alert.return.guarantee.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': self.env.context,
            }
        else:
            record.write({'state_2': 'approved'})


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    detail_ids = fields.One2many("purchase.order.line.detail", "purchase_order_line_id", "Line Details")
    amount_total = fields.Float(string='Total', compute='_compute_amount_total', store=True)
    ventilate = fields.Monetary(string='À ventiler', compute='_compute_ventilate', store=True)
    is_attachment = fields.Boolean(related='order_id.is_attachment', store=True)
    is_certified = fields.Boolean(related='order_id.is_certified')
    product_type = fields.Selection(related='product_id.type')
    can_edit_received_qty = fields.Boolean(compute="_compute_can_edit_received_qty", default=False)
    qty_validated = fields.Float("Qté Validé")
    qty_certified = fields.Float("Qté Certifié")
    

    @api.depends("product_qty", "qty_received", "qty_invoiced")
    def _compute_can_edit_received_qty(self):
        for line in self:
            line.can_edit_received_qty = False
            if self.env.user.has_group("building_plus.sotaserv_magasinier") or self.env.user.has_group("building_plus.sotaserv_magasinier_chantier"):
                tolerance = line.product_qty * line.company_id.purchase_tolerance / 100
                if line.qty_validated <= line.qty_invoiced:
                    line.can_edit_received_qty = True
                if line.qty_invoiced == line.product_qty or line.qty_invoiced == line.product_qty + tolerance:
                    line.can_edit_received_qty = False

    # entry_line_ids = fields.One2many('purchase.entry.line', 'order_line_id', string='Entry Lines')

    @api.onchange("qty_received")
    def _onchange_qty_received(self):
        tolerance = self.product_qty * self.company_id.purchase_tolerance / 100
        if self.qty_received > (self.product_qty + tolerance):
            mssg = "La quantité reçue ne peut pas dépasser celle demandée."
            if self.company_id.purchase_tolerance:
                mssg = f"La quantité reçue ne peut dépasser celle demandée que par {self.company_id.purchase_tolerance}%"
            raise UserError(mssg)
        if self.qty_received < self.qty_invoiced:
            raise UserError("Assurer que la quantité reçue est supérieure à celle facturée.")

    @api.depends('detail_ids.subtotal')
    def _compute_amount_total(self):
        for line in self:
            line.amount_total = sum(detail.subtotal for detail in line.detail_ids)

    @api.depends('amount_total', 'price_subtotal')
    def _compute_ventilate(self):
        for line in self:
            ventilate_value = line.price_subtotal - line.amount_total
            if ventilate_value < 0:
                excess_amount = line.amount_total - line.price_subtotal
                if line.is_attachment:
                    raise ValidationError(
                        "Vous avez dépassé le montant de la facture de {:.2f} CFA. "
                        "La pièce jointe ne peut pas dépasser le montant de la facture.".format(excess_amount)
                    )
            line.ventilate = ventilate_value

    @api.constrains('ventilate')
    def _check_ventilate(self):
        for line in self:
            if line.ventilate < 0:
                excess_amount = line.amount_total - line.price_subtotal
                if line.is_attachment:
                    raise ValidationError(
                        "Vous avez dépassé le montant de la facture de {:.2f} CFA. "
                        "La pièce jointe ne peut pas dépasser le montant de la facture.".format(excess_amount)
                    )

    def _get_need_line(self):
        filter = lambda line: line.product_id == self.product_id

        need = self.env["building.purchase.need"].search([("site_id", "=", self.order_id.site_id.id)])
        need_line = need.line_ids.filtered(filter)
        if not need_line:
            need_line = need.service_provision_ids.filtered(filter)
        if not need_line:
            need_line = need.mini_equipment_ids.filtered(filter)
        if not need_line:
            need_line = need.fuel_ids.filtered(filter)

        return need_line
    
    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity', 'qty_received', 'product_uom_qty', 'order_id.state')
    def _compute_qty_invoiced(self):
        for line in self:
            # compute qty_invoiced
            qty = 0.0
            for inv_line in line.invoice_lines:
                if inv_line.move_id.state not in ['cancel']:
                    if inv_line.move_id.move_type == 'in_invoice':
                        qty += inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
                    elif inv_line.move_id.move_type == 'in_refund':
                        qty -= inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
            line.qty_invoiced = qty

            # compute qty_to_invoice
            if line.order_id.state in ['purchase', 'done', 'partial', 'full']:
                if line.product_id.purchase_method == 'purchase':
                    line.qty_to_invoice = line.product_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_received - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    def _prepare_account_move_line(self, move=False, picking_ids=False):
        self.ensure_one()
        aml_currency = move and move.currency_id or self.currency_id
        date = move and move.date or fields.Date.today()
        quantity = self.qty_to_invoice
        if picking_ids:
            quantity = sum(picking_ids.move_ids_without_package.filtered(lambda l:l.product_id.id == self.product_id.id).mapped("quantity_done"))

        res = {
            'display_type': self.display_type,
            'sequence': self.sequence,
            'name': '%s: %s' % (self.order_id.name, self.name),
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': quantity,
            'price_unit': self.currency_id._convert(self.price_unit, aml_currency, self.company_id, date, round=False),
            'tax_ids': [(6, 0, self.taxes_id.ids)],
            'analytic_account_id': self.account_analytic_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'purchase_line_id': self.id,
        }
        if not move:
            return res

        if self.currency_id == move.company_id.currency_id:
            currency = False
        else:
            currency = move.currency_id

        res.update({
            'move_id': move.id,
            'currency_id': currency and currency.id or False,
            'date_maturity': move.invoice_date_due,
            'partner_id': move.partner_id.id,
        })
        return res

    # @api.constrains('price_unit')
    # def _check_price_unit(self):
    #     for line in self:
    #         if line.price_unit <= 0:
    #             raise ValidationError("Le prix unitaire ne peut pas être zéro.")