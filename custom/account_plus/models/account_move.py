from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError, UserError
import xml.etree.ElementTree as ET
from lxml import etree
import json
from num2words import num2words
from datetime import timedelta
from odoo.tools.misc import format_date
import math
import logging


_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    is_payrun_entry = fields.Boolean(string="Pièce Lot Paie", compute="_compute_is_payrun_entry", store=True)
    is_payrun_paid = fields.Boolean(string="Pièce Lot Payée")
    has_tax_line = fields.Boolean(string="Has Tax Line", compute="_compute_has_tax_line")

    @api.depends("line_ids.is_tax_line")
    def _compute_has_tax_line(self):
        for move in self:
            move.has_tax_line = any(line.is_tax_line for line in move.line_ids)

    @api.depends("journal_id.code")
    def _compute_is_payrun_entry(self):
        for record in self:
            record.is_payrun_entry = record.journal_id.code == "Paie"

    def action_register_payments_payrun(self):
        target_groups = [
            [[("4220000", "Salaire Net")]],
            [
                [("4472000", "Total Retenue Fiscale Salariale"), ("4472000", "ITS Patronale")],
                [("4478020", "FDFP (FPC)")],
                [("4478010", "Taxe d'Apprent")]
            ],
            [[("4313000", "CNPS (C R)"), ("4313000", "Caisse de Retraite")]],
            [
                [("4311000", "Prestation Familiale")],
                [("4312000", "Assurance Maternité"), ("4312000", "Accident de Travail")],
                [("4318000", "CMU Patronale")]
            ],
        ]

        payments = []
        for i, group in enumerate(target_groups, start=1):
            add_dot = len(group) > 1
            for j, target in enumerate(group, start=1):
                lines = self.line_ids.filtered(lambda line: (line.account_id.code, line.name) in target)
                amount = sum(lines.mapped("amount_currency"))
                account = lines and lines[0].account_id
                partner = lines and lines[0].partner_id
                date = self.env["hr.payslip.run"].sudo().search([("move_id", "=", self.id)], limit=1).date_end
                payments.append({
                    "ref": add_dot and f"Paiement {i}.{j}" or f"Paiement {i}",
                    "date": date,
                    "amount": abs(amount),
                    "account_id": account.id,
                    "partner_id": partner.id,
                    "payment_type": amount > 0 and "inbound" or "outbound",
                })

        wizard = self.env["hr.payslip.run.payment"].sudo().create({"move_id": self.id, "line_ids": [(0, 0, payment) for payment in payments]})
        return {
            "type": "ir.actions.act_window",
            "name": "Création Paiements",
            "res_model": "hr.payslip.run.payment",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }

    regime_imposition = fields.Selection(
        related='partner_id.regime_imposition',
    )
    is_cancel_visible = fields.Boolean(compute="_compute_is_cancel_visible")
    is_tax_ids_readonly = fields.Boolean(compute="_compute_is_tax_ids_readonly")

    def print_invoice_decompte_report(self):
        data = self.get_invoice_data()
        return self.env.ref('account_plus.invoice_decompte_client_report_action').report_action(self, data={'data': data})

    def amount_remaining_in_word(self, amount):
        currency = self.env['res.company'].search([], limit=1).currency_id

        amount_main = int(amount)
        amount_cents = int(round((amount - amount_main) * 100))

        amount_main_word = currency.amount_to_text(amount_main)

        if amount_cents > 0:
            cents_word = currency.amount_to_text(amount_cents)
            return f"{amount_main_word} et {cents_word} Centimes CFA"
        else:
            return f"{amount_main_word} et Zéro Centimes CFA"
    
    def get_invoice_data(self):
        data = []
        for rec in self:
            amount_advance_untaxed = rec.prc_advance_deduction * (1 + (rec.amount_tax / 100)) if rec.amount_tax else rec.prc_advance_deduction * (18 / 100)
            amount_gr_untaxed = rec.prc_gr * (1 + (rec.amount_tax / 100)) if rec.amount_tax else rec.prc_gr * (18 / 100)
            amount_prc_ten_year_untaxed = rec.prc_ten_year * (1 + (rec.amount_tax / 100)) if rec.amount_tax else rec.prc_ten_year * (18 / 100)
            for line in rec.invoice_line_ids:
                data.append({
                    'ref': rec.ref,
                    'invoice_date': rec.invoice_date.strftime('%d/%m/%Y'),
                    'partner': rec.partner_id.name if rec.partner_id else '',
                    'site': rec.site_id.name if rec.site_id else '',
                    'name': line.name,
                    'amount_untaxed': rec.amount_untaxed,
                    'amount_tax': rec.amount_tax,
                    'tax_amount': rec.amount_tax if rec.amount_tax else rec.amount_untaxed * (18 / 100),
                    'amount_total_before_deduction': rec.amount_total_before_deduction,
                    'amount_advance_untaxed': amount_advance_untaxed if rec.amount_tax else rec.prc_advance_deduction,
                    'amount_advance_tax': rec.prc_advance_deduction - amount_advance_untaxed if rec.amount_tax else rec.prc_advance_deduction * (18 / 100),
                    'prc_advance_deduction': rec.prc_advance_deduction,
                    'amount_gr_untaxed': amount_gr_untaxed if rec.amount_tax else rec.prc_gr,
                    'amount_gr_tax': rec.prc_gr - amount_gr_untaxed if rec.amount_tax else rec.prc_gr * (18 / 100),
                    'prc_gr': rec.prc_gr,
                    'amount_prc_ten_year_untaxed': amount_prc_ten_year_untaxed if rec.amount_tax else rec.prc_ten_year,
                    'amount_prc_ten_year_tax': rec.prc_ten_year - amount_prc_ten_year_untaxed if rec.amount_tax else rec.prc_ten_year * (18 / 100),
                    'prc_ten_year': rec.prc_ten_year,
                    'amount_total': rec.amount_total,
                    'amount_total_in_words': self.amount_remaining_in_word(rec.amount_total),
                    'vat_exempt': rec.site_id.vat_exempt if rec.site_id else '',
                    'company_id': {
                        'capital': rec.company_id.capital or 0,
                        'rccm': rec.company_id.rccm or '',
                        'niu_nemuro': rec.company_id.niu_nemuro or '',
                        'cnps': rec.company_id.cnps or '',
                        'street': rec.company_id.street or '',
                        'street2': rec.company_id.street2 or '',
                        'city': rec.company_id.city or '',
                        'country': rec.company_id.country_id.display_name if rec.company_id.country_id else '',
                        'phone': rec.company_id.phone or '',
                        'mobile': rec.company_id.mobile or '',
                        'email': rec.company_id.email or '',
                        'website': rec.company_id.website or '',
                        'bank_account': rec.company_id.bank_account or '',
                    }
                })
        return data

    @api.constrains('ref', 'move_type', 'partner_id', 'journal_id', 'invoice_date', 'state')
    def _check_duplicate_supplier_reference(self):
        moves = self.filtered(lambda move: move.state == 'posted' and move.is_purchase_document() and move.ref)
        if not moves:
            return

        self.env["account.move"].flush([
            "ref", "move_type", "invoice_date", "journal_id",
            "company_id", "partner_id", "commercial_partner_id",
        ])
        self.env["account.journal"].flush(["company_id"])
        self.env["res.partner"].flush(["commercial_partner_id"])

        # Updated SQL to exclude canceled moves
        self._cr.execute('''
            SELECT move2.id
            FROM account_move move
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN res_partner partner ON partner.id = move.partner_id
            INNER JOIN account_move move2 ON
                move2.ref = move.ref
                AND move2.company_id = journal.company_id
                AND move2.commercial_partner_id = partner.commercial_partner_id
                AND move2.move_type = move.move_type
                AND (move.invoice_date IS NULL OR move2.invoice_date = move.invoice_date)
                AND move2.id != move.id
                AND move2.state != 'cancel'
            WHERE move.id IN %s
        ''', [tuple(moves.ids)])

        duplicated_moves = self.browse([r[0] for r in self._cr.fetchall()])
        if duplicated_moves:
            raise ValidationError(_('Duplicated vendor reference detected. You probably encoded twice the same vendor bill/credit note:\n%s') % "\n".join(
                duplicated_moves.mapped(lambda m: "%(partner)s - %(ref)s - %(date)s" % {
                    'ref': m.ref,
                    'partner': m.partner_id.display_name,
                    'date': format_date(self.env, m.invoice_date),
                })
            ))

    @api.depends('regime_imposition')
    def _compute_is_tax_ids_readonly(self):
        for record in self:
            record.is_tax_ids_readonly = record.regime_imposition in ['normal', 'simplifie'] and record.move_type == "in_invoice"

    # @api.onchange('invoice_line_ids')
    # def _onchange_invoice_line_ids(self):
    #     if self.move_type == 'out_invoice':
    #         return {
    #             'domain': {
    #                 'invoice_line_ids.tax_ids': [
    #                     ('type_tax_use', '=', 'sale'),
    #                     ('tax_group_id.name', '!=', 'Retenue'),
    #                     ('company_id', '=', self.company_id.id)
    #                 ]
    #             }
    #         }
    #     else:
    #         return {
    #             'domain': {
    #                 'invoice_line_ids.tax_ids': [
    #                     ('type_tax_use', '=', 'purchase'),
    #                     ('tax_group_id.name', '!=', 'Retenue'),
    #                     ('company_id', '=', self.company_id.id)
    #                 ]
    #             }
    #         }

    def open_reset_draft_reason_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Motif de remise en brouillon",
            "res_model": "reset.draft.reason.wizard",
            "view_mode": "form",
            "target": "new",
        }

    def action_view_stock_picking(self):
        stock_pickings = self.env['stock.picking'].search([('invoice_id', '=', self.id)])
        tree_view = self.env.ref('account_plus.stock_picking_readonly_tree_view')
        return {
            'name': _('Réceptions associées'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree',
            'views': [(tree_view.id, 'tree')],
            'domain': [('id', 'in', stock_pickings.ids)],
            'target': 'current',
            'context': {
                'delete': False,
                'create': False,
                'edit': False,
                'hide_actions': True,
            },
        }

    @api.depends('invoice_origin')
    def _compute_is_cancel_visible(self):
        for record in self:
            last_decompte = self.env['purchase.entry'].search([('purchase_id.name', '=', record.invoice_origin)], order='create_date desc', limit=1)
            if last_decompte.account_move_id.id == record.id:
                record.is_cancel_visible = True
            else:
                record.is_cancel_visible = False
    
    def action_cancel_decompte_invoice(self, reason=None):
        for record in self:
            purchase = self.env['purchase.entry'].search([('account_move_id', '=', record.id)])
            record.write({
                'state': 'cancel',
                'decompte': False,
                'invoice_origin': False,
                'reason': reason,
            })
            purchase.write({'account_move_id': False, 'state_decompte': 'done', 'state_decompte_not_done': 'done'})

            message = "Facture annulée : cette facture n'est plus associée à aucun décompte."
            if purchase:
                message += "<br/>Décompte concernées :<ul>"
                for rec in purchase:
                    message += f"<li>{rec.number}</li>"
                message += "</ul>"

            record.message_post(
                body=message,
                subtype_xmlid='mail.mt_note'
            )

            for rec in purchase:
                rec.message_post(
                    body=f"La facture associée {record.name} a été annulée. Cette Décompte n'est plus liée à une facture.",
                    subtype_xmlid='mail.mt_note'
                )
    
    def action_cancel_reason(self):
        return {
            "name": "Annuler",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "cancellation.reason",
            "target": "new",
        }

    def action_cancel(self, reason=None):
        for record in self:
            if record.state == "received" and record.move_type_code == "inv_other":
                record.write({
                    "state": "cancel",
                    "reason": reason,
                })
            else:
                stock_pickings = self.env['stock.picking'].search([('invoice_id', '=', record.id)])
                record.write({'state': 'cancel'})
                stock_pickings.write({'is_invoiced': False, 'invoice_id': False, 'certification_state': 'certified', 'amount_advance_deduction': 0})

                message = "Facture annulée. Cette facture n'est plus associée à aucune réception."
                if stock_pickings:
                    message += "<br/>Réceptions concernées :<ul>"
                    for picking in stock_pickings:
                        message += f"<li>{picking.name}</li>"
                    message += "</ul>"

                record.message_post(
                    body=message,
                    subtype_xmlid='mail.mt_note'
                )

                for picking in stock_pickings:
                    picking.message_post(
                        body=f"La facture associée {record.name} a été annulée. Cette réception n'est plus liée à une facture.",
                        subtype_xmlid='mail.mt_note'
                    )

    def button_draft(self, reason=None):
        res = super(AccountMove, self).button_draft()
        if reason:
            message = f"Facture remise en brouillon. Motif : {reason}"
            self.message_post(body=message)
        if self.move_type_type != "manual":
            self.state = "pre_validated"
        # return res

    def recompute_dynamic_lines(self):
        self.with_context(force_delete=True)._onchange_invoice_line_ids()
        self.line_ids.filtered(lambda l: l.account_id.code == '61261300').with_context(force_delete=True).unlink()

    def _check_balanced(self):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        moves = self.filtered(lambda move: move.line_ids)
        if not moves:
            return

        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend of computed stored fields (e.g. balance).
        # It happens as the ORM makes the create with the 'no_recompute' statement.
        self.env['account.move.line'].flush(self.env['account.move.line']._fields)
        self.env['account.move'].flush(['journal_id'])
        self._cr.execute('''
            SELECT line.move_id, ROUND(SUM(line.debit - line.credit), currency.decimal_places)
            FROM account_move_line line
            JOIN account_move move ON move.id = line.move_id
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN res_company company ON company.id = journal.company_id
            JOIN res_currency currency ON currency.id = company.currency_id
            WHERE line.move_id IN %s
            GROUP BY line.move_id, currency.decimal_places
            HAVING ROUND(SUM(line.debit - line.credit), currency.decimal_places) != 0.0;
        ''', [tuple(self.ids)])

        query_res = self._cr.fetchall()
        if query_res:
            ids = [res[0] for res in query_res]
            sums = [res[1] for res in query_res]
            list_lines = []
            list_moves = []
            account_adjustment = self.env['account.account'].search([('code', '=', '61261300')])
            record_line = {
                'account_id': account_adjustment.id,
                'name':account_adjustment.name,
                'quantity':1,
                'exclude_from_invoice_tab':True,
                'is_building_specific': True,
            }
            record_lines = {}
            #########################Aziz: Ajout une ligne Ecart au cas ou desequilibre ne depasse passe 1 DHs#######
            for mv_id, mnt_ajust in zip(ids, sums):
                if mv_id not in list_moves:
                    acc_move = self.env['account.move'].browse(mv_id)
                    record_line['move_id'] = mv_id
                    record_line['currency_id'] = acc_move.currency_id.id
                    list_moves.append(mv_id)

                    if mnt_ajust < 0:
                        record_line['price_unit'] = abs(mnt_ajust)
                        # record_line['debit_after_deduction'] = abs(mnt_ajust)
                        # record_line['credit_after_deduction'] = 0
                        record_line['debit'] = abs(mnt_ajust)
                        record_line['credit'] = 0
                    if mnt_ajust > 0:
                        record_line['price_unit'] = abs(mnt_ajust)
                        # record_line['debit_after_deduction'] = 0
                        # record_line['credit_after_deduction'] = abs(mnt_ajust)
                        record_line['debit'] = 0
                        record_line['credit'] = abs(mnt_ajust)
                    record_lines[mv_id] = record_line
                else:
                    if mnt_ajust < 0:
                        record_line['price_unit'] += abs(mnt_ajust)
                        # record_line['debit_after_deduction'] += abs(mnt_ajust)
                        # record_line['credit_after_deduction'] = 0
                        record_line['debit'] += abs(mnt_ajust)
                        record_line['credit'] = 0
                    if mnt_ajust > 0:
                        record_line['price_unit'] += abs(mnt_ajust)
                        # record_line['debit_after_deduction'] = 0 
                        # record_line['credit_after_deduction'] += abs(mnt_ajust)
                        record_line['debit'] = 0
                        record_line['credit'] += abs(mnt_ajust)
                    record_lines[mv_id] = record_line
            for _, rcd_line in record_lines.items():
                list_lines.append(rcd_line)
            if isinstance(acc_move.id, models.NewId):
                self.env['account.move.line'].new(list_lines)
            else:
                self.env['account.move.line'].create(list_lines)

    @api.model
    def _get_invoice_in_payment_state(self):
        # OVERRIDE to enable the 'in_payment' state on invoices.
        return 'in_payment'

    # def _get_default_invoice_payment_term_id(self):
    #     if self.partner_id:
    #         return self.partner_id.property_supplier_payment_term_id.id
    #     else:
    #         return self.env["account.payment.term"].search([("name", "=", "60 jours")], limit=1).id
        
    # def _get_default_invoice_date_due(self):
    #     return fields.Date.today() + timedelta(days=60)
    
    invoice_line_ids_readability = fields.Boolean(compute="_compute_invoice_line_ids_readability")
    reason = fields.Char(string="Motif")
    return_of_guarantee = fields.Float(string="RG")
    penalty = fields.Float(string="Pénalité")
    avance = fields.Float(string="Avance")

    is_advance_invoice = fields.Boolean(default=True, compute="_compute_is_advance_invoice")
    is_decompte = fields.Boolean(default=False, compute="_compute_is_advance_invoice")
    is_invisible_penalty = fields.Boolean(default=False, compute="_compute_is_advance_invoice")
    is_invisible_rg = fields.Boolean(default=False, compute="_compute_is_advance_invoice")
    is_readonly_advance = fields.Boolean(default=False, compute="_compute_is_readonly_advance_rg")
    move_type_id = fields.Many2one(
        "account.move.type", 
        string="Type de Facture", 
        domain=[("is_active", "=", True), ("type", "=", "manual")], 
        default=lambda self: self.env["account.move.type"].search([("name", "=", "Autre")], limit=1).id, 
        required=True
    )
    move_type_code = fields.Char(related="move_type_id.code")
    move_type_type = fields.Selection(related="move_type_id.type", string="Type Type Facture", store=True)
    is_automatic_move_type = fields.Boolean(compute="_compute_is_automatic_move_type")

    state = fields.Selection([
        ("draft", "Brouillon"),
        ("submitted", "Soumise"),
        ("pre_validated", "Validée"),
        ("received", "Récéptionnée"),
        ("validated", "Validée CG"),
        ("posted", "Comptabilisé"),
        ("blocked", "Bloquée"),
        ("cancel", "Annulé"),
    ], default="draft")

    def open_create_line_taxe_wizard(self):
        self.ensure_one()
        return {
            "name": "Ajouter une ligne de taxe",
            "type": "ir.actions.act_window",
            "res_model": "tax.line.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_id": self.id,
            }
        }        

    def open_back_to_draft_reason_wizard(self):
        return {
            "name": "Assistant de retour",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cancellation.reason',
            'target': 'new',
        }

    def action_return_validated(self, reason=None):
        if self.state == "posted":
            self.state = "validated"
        self.message_post(body=f"""
            <ul>
                <li>Retour à l'état <strong>{dict(self._fields['state'].selection).get(self.state, self.state)}</strong></li>
                <li>Motif : {reason}</li>
            </ul>
        """)

    def action_return_received(self, reason=None):
        if self.state == "validated":
            self.state = "received"
        self.message_post(body=f"""
            <ul>
                <li>Retour à l'état <strong>{dict(self._fields['state'].selection).get(self.state, self.state)}</strong></li>
                <li>Motif : {reason}</li>
            </ul>
        """)
        
    def action_return_pre_validated(self, reason=None):
        if self.state == "received":
            self.state = "pre_validated"
        self.message_post(body=f"""
            <ul>
                <li>Retour à l'état <strong>{dict(self._fields['state'].selection).get(self.state, self.state)}</strong></li>
                <li>Motif : {reason}</li>
            </ul>
        """)
    
    def action_return_submitted(self, reason=None):
        if self.state == "pre_validated":
            self.state = "submitted"
        self.message_post(body=f"""
            <ul>
                <li>Retour à l'état <strong>{dict(self._fields['state'].selection).get(self.state, self.state)}</strong></li>
                <li>Motif : {reason}</li>
            </ul>
        """)
        
    def action_return_draft(self, reason=None):
        if self.state == "submitted":
            self.state = "draft"
        self.message_post(body=f"""
            <ul>
                <li>Retour à l'état <strong>{dict(self._fields['state'].selection).get(self.state, self.state)}</strong></li>
                <li>Motif : {reason}</li>
            </ul>
        """)

    def button_submit(self):
        if self.state == "draft": self.state = "submitted"

    def button_pre_validate(self):
        if self.state == "submitted": self.state = "pre_validated"

    entry_state = fields.Selection("Statut", related="state")

    is_attachment = fields.Boolean(string="Attachement", default=False)
    based_on = fields.Selection([("based_on_purchase_order", "Basé sur bon de commande"), ("based_on_attachment", "Basé sur attachement"), ("other", "Autre")], compute="_compute_based_on", default="other", string="Basé sur", store=True)
    invoice_type = fields.Selection([("standard", "Standard"), ("specific", "Specific"), ("advance", "Avance")], store=True)
    set_invoice_type = fields.Selection([
        ("advance", "Avance"), 
        ("supply_receipt", "Fourniture_Réception"), 
        ("service_without_attachment", "Service sans attachement"), 
        ("decompte", "Décompte"), 
        ("rg", "Libération RG"), 
        ("other", "Autre")], store=True, string="Type de Facture", default="other")
    
    deposit_date = fields.Date(string="Date Dépôt", default=fields.Date.context_today)

    # invoice_date_due = fields.Date(string='Due Date', compute='_compute_invoice_date_due', store=True)
    # invoice_date_due = fields.Date(string='Due Date', store=True, default=_get_default_invoice_date_due)
    # invoice_payment_term_id = fields.Many2one('account.payment.term', default=_get_default_invoice_payment_term_id)

    decompte = fields.Char(string="Numéro Décompte", readonly=True)

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        ondelete='restrict'
    )
    journal_type = fields.Selection(
        related='journal_id.type',
        string="Journal Type",
        store=True,
        readonly=True,
    )
    is_general_paie_entry = fields.Boolean(
        compute="_compute_is_general_paie_entry",
        string="Readonly Entry Fields",
    )

    out_state = fields.Selection(
        selection=[
            ('draft', 'Brouillon'),
            ('submitted', 'Soumis'),
            ('finance_validated', 'Validé Finance'),
            ('posted', 'Comptabilisé'),
        ],
        default='draft',
        string='Statut',
        tracking=True,
    )

    def action_submit(self):
        self.out_state = 'submitted'

    def action_validate_finance(self):
        self.out_state = 'finance_validated'

    def action_out_post(self):
        self.out_state = "posted"
        self.action_post()

    def action_out_invoice_back(self):
        return {
            "name": "Remettre",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "res_model": self._name,
            "res_id": self.id,
            "target": "new",
            "views": [(self.env.ref("account_plus.account_move_form_out_invoice_back").id, "form")],
        }

    def button_out_invoice_back(self):
        out_state_flow = {
            "posted": "finance_validated",
            "finance_validated": "submitted",
            "submitted": "draft",
        }
        current_out_state = self.out_state
        new_out_state = out_state_flow.get(current_out_state)
        reason = self.reason

        if current_out_state == "posted":
            self.button_draft()

        self.write({"out_state": new_out_state, "reason": ""})
        self.env.cr.commit()
        last_message = self.message_ids.sorted("id")[-1]
        self.env["mail.tracking.value"].create({
            "mail_message_id": last_message.id,
            "field": self.env["ir.model.fields"].search([("model", "=", self._name), ("name", "=", "out_state")], limit=1).id,
            "field_desc": "Motif",
            "new_value_char": reason,
        })

    @api.onchange('move_type')
    def _onchange_move_type(self):
        if self.move_type == 'out_invoice':
            domain = [('is_active', '=', True), ('type', '=', 'manual'), ('client_supplier', 'in', ['client', 'both'])]
        elif self.move_type == 'in_invoice': 
            domain = [('is_active', '=', True), ('type', '=', 'manual'), ('client_supplier', 'in', ['supplier', 'both'])]
        else:
            domain = [('is_active', '=', True), ('type', '=', 'manual')]

        return {'domain': {'move_type_id': domain}}

    @api.depends('journal_type', 'journal_id')
    def _compute_is_general_paie_entry(self):
        for rec in self:
            rec.is_general_paie_entry = rec.journal_type == 'general' and rec.journal_id.name == 'Paie'

    # @api.onchange('invoice_date_due')
    # def _onchange_invoice_date_due(self):
    #     if self.invoice_date_due:
    #         self.date = False

    def _compute_name(self):
        no_name = self.filtered(lambda move: move.state != "posted" and not move.posted_before)
        for move in no_name:
            move.name = "/"

        self = self.filtered(lambda move: move.state == "posted")
        super()._compute_name()

    is_controle_gestion_user = fields.Boolean(compute="_compute_is_controle_gestion_user")
    is_rg_release = fields.Boolean(string="Libération RG", store=True)

    def _compute_invoice_line_ids_readability(self):
        for move in self:
            if move.state != "draft":
                move.invoice_line_ids_readability = True
                if self.env.user.has_group("account_plus.acount_move_group_invoice") and move.state == "validated":
                    move.invoice_line_ids_readability = False
                if self.env.user.has_group("account_plus.acount_move_group_Aud") and move.state == "blocked":
                    move.invoice_line_ids_readability = False
            else:
                move.invoice_line_ids_readability = False
        
    @api.onchange('invoice_date')
    def onchange_invoice_date(self):
        lines_to_keep = self.invoice_line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)
        self.invoice_line_ids = [(6, 0, lines_to_keep.ids)]

    @api.depends('move_type_id')
    def _compute_is_automatic_move_type(self):
        for rec in self:
            rec.is_automatic_move_type = rec.move_type_id and rec.move_type_id.type == "automatic"

    @api.depends()
    def _compute_is_controle_gestion_user(self):
        controle_gestion_group = self.env.ref("account_plus.acount_move_group_cg")
        for rec in self:
            rec.is_controle_gestion_user = self.env.user in controle_gestion_group.users

    @api.constrains('avance')
    def _check_avance_and_guarantee(self):
        for invoice in self:
            order = self.env['purchase.order'].search([('name', '=', invoice.invoice_origin)], limit=1)
            if order:
                invoices = self.env['account.move'].search([('invoice_origin', '=', order.name), ('move_type', '=', 'in_invoice'), ("state", "!=", "cancel")])

                advance_total = sum(invoices.mapped('avance'))
                order_advance = self.env['account.move'].search([('invoice_origin', '=', order.name), ('move_type_code', '=', 'inv_advance'), ("state", "!=", "cancel")]).amount_total

                def format_number(number):
                    return f"{number:,.2f}".replace(",", " ").replace(".", ",")

                formatted_total = format_number(advance_total)
                formatted_max = format_number(order_advance)

                if advance_total > order_advance:
                    raise ValidationError(
                        f"Le total des avances ({formatted_total}) dépasse l'avance maximale autorisée ({formatted_max})."
                    )

    @api.depends('invoice_origin')
    def _compute_is_readonly_advance_rg(self):
        for rec in self:
            order = self.env['purchase.order'].search([('name', '=', rec.invoice_origin)], limit=1)
            rec.is_readonly_advance = order.avance if order else False

    @api.depends('move_type_id')
    def _compute_is_advance_invoice(self):
        for rec in self:
            move_type_name = rec.move_type_id.name if rec.move_type_id else ""
            # raise Exception(move_type_name)
            rec.is_advance_invoice = move_type_name not in ["Service sans attachement", "Fourniture_Réception", "Décompte"]
            rec.is_decompte = move_type_name == "Décompte"
            rec.is_invisible_penalty = rec.is_invisible_rg = move_type_name in ["Service sans attachement", "Fourniture_Réception",]

    @api.depends("is_attachment", "invoice_origin")
    def _compute_based_on(self):
        for move in self:
            if move.is_attachment:
                move.based_on = "based_on_attachment"
            elif move.invoice_origin:
                move.based_on = "based_on_purchase_order"
            else:
                move.based_on = "other"

    # @api.depends('invoice_line_ids.purchase_line_id.order_id.effective_date')
    # def _compute_invoice_date_due(self):
    #     for move in self:
    #         purchase_orders = move.invoice_line_ids.mapped('purchase_line_id.order_id')
    #         if purchase_orders:
    #             move.invoice_date_due = purchase_orders[0].effective_date

    # amount_total_before_deduction = fields.Float(string="Total Travaux TTC", compute="_compute_amount_total_before_deduction")

    # def _compute_amount_total_before_deduction(self):
    #     for move in self:
    #         amount_untaxed_before_deduction = sum(line.price_subtotal for line in move.invoice_line_ids)
    #         move.amount_total_before_deduction = amount_untaxed_before_deduction

    # @api.onchange('deposit_date', 'invoice_payment_term_id', 'invoice_date', 'highest_name', 'company_id')
    # def _onchange_invoice_date(self):
    #     if self.deposit_date:
    #         if not self.invoice_payment_term_id and self.deposit_date:
    #             self.invoice_date_due = self.deposit_date

    #         has_tax = bool(self.line_ids.tax_ids or self.line_ids.tax_tag_ids)
    #         accounting_date = self._get_accounting_date(self.deposit_date, has_tax) or False
    #         if accounting_date and accounting_date != self.date:
    #             # self.date = accounting_date
    #             self._onchange_currency()
    #         else:
    #             self._onchange_recompute_dynamic_lines()

    # def _recompute_payment_terms_lines(self, return_date=False):
    #     ''' Compute the dynamic payment term lines of the journal entry.'''
    #     self.ensure_one()
    #     # if self.invoice_payment_term_id and self.invoice_payment_term_id.name.strip().lower() == 'comptant':
    #     #     return
    #     self = self.with_company(self.company_id)
    #     in_draft_mode = self != self._origin
    #     today = fields.Date.context_today(self)
    #     self = self.with_company(self.journal_id.company_id)

    #     def _get_payment_terms_computation_date(self):
    #         ''' Get the date from invoice that will be used to compute the payment terms.
    #         :param self:    The current account.move record.
    #         :return:        A datetime.date object.
    #         '''
    #         if self.invoice_payment_term_id:
    #             return self.deposit_date or self.invoice_date
    #         else:
    #             return self.invoice_date_due or self.deposit_date or self.invoice_date

    #     def _get_payment_terms_account(self, payment_terms_lines):
    #         ''' Get the account from invoice that will be set as receivable / payable account.
    #         :param self:                    The current account.move record.
    #         :param payment_terms_lines:     The current payment terms lines.
    #         :return:                        An account.account record.
    #         '''
    #         if payment_terms_lines:
    #             # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
    #             return payment_terms_lines[0].account_id
    #         elif self.partner_id:
    #             # Retrieve account from partner.
    #             if self.is_sale_document(include_receipts=True):
    #                 return self.partner_id.property_account_receivable_id
    #             else:
    #                 return self.partner_id.property_account_payable_id
    #         else:
    #             # Search new account.
    #             domain = [
    #                 ('company_id', '=', self.company_id.id),
    #                 ('internal_type', '=', 'receivable' if self.move_type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'),
    #             ]
    #             return self.env['account.account'].search(domain, limit=1)

    #     def _compute_payment_terms(self, date, total_balance, total_amount_currency):
    #         ''' Compute the payment terms.
    #         :param self:                    The current account.move record.
    #         :param date:                    The date computed by '_get_payment_terms_computation_date'.
    #         :param total_balance:           The invoice's total in company's currency.
    #         :param total_amount_currency:   The invoice's total in invoice's currency.
    #         :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
    #         '''
    #         if self.invoice_payment_term_id:
    #             to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date, currency=self.company_id.currency_id)
    #             if self.currency_id == self.company_id.currency_id:
    #                 # Single-currency.
    #                 return [(b[0], b[1], b[1]) for b in to_compute]
    #             else:
    #                 # Multi-currencies.
    #                 to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency, date_ref=date, currency=self.currency_id)
    #                 return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
    #         else:
    #             return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

    #     def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
    #         ''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
    #         :param self:                    The current account.move record.
    #         :param existing_terms_lines:    The current payment terms lines.
    #         :param account:                 The account.account record returned by '_get_payment_terms_account'.
    #         :param to_compute:              The list returned by '_compute_payment_terms'.
    #         '''
    #         # As we try to update existing lines, sort them by due date.
    #         existing_terms_lines = existing_terms_lines.sorted(lambda line: line.date_maturity or today)
    #         existing_terms_lines_index = 0

    #         # Recompute amls: update existing line or create new one for each payment term.
    #         new_terms_lines = self.env['account.move.line']
    #         for date_maturity, balance, amount_currency in to_compute:
    #             currency = self.journal_id.company_id.currency_id
    #             if currency and currency.is_zero(balance) and len(to_compute) > 1:
    #                 continue

    #             if existing_terms_lines_index < len(existing_terms_lines):
    #                 # Update existing line.
    #                 candidate = existing_terms_lines[existing_terms_lines_index]
    #                 existing_terms_lines_index += 1
    #                 candidate.update({
    #                     'date_maturity': date_maturity,
    #                     'amount_currency': -amount_currency,
    #                     'debit': balance < 0.0 and -balance or 0.0,
    #                     'credit': balance > 0.0 and balance or 0.0,
    #                 })
    #             else:
    #                 # Create new line.
    #                 create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
    #                 candidate = create_method({
    #                     'name': self.payment_reference or '',
    #                     'debit': balance < 0.0 and -balance or 0.0,
    #                     'credit': balance > 0.0 and balance or 0.0,
    #                     'quantity': 1.0,
    #                     'amount_currency': -amount_currency,
    #                     'date_maturity': date_maturity,
    #                     'move_id': self.id,
    #                     'currency_id': self.currency_id.id,
    #                     'account_id': account.id,
    #                     'partner_id': self.commercial_partner_id.id,
    #                     'exclude_from_invoice_tab': True,
    #                 })
    #             new_terms_lines += candidate
    #             if in_draft_mode:
    #                 candidate.update(candidate._get_fields_onchange_balance(force_computation=True))
    #         return new_terms_lines

    #     existing_terms_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
    #     others_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
    #     company_currency_id = (self.company_id or self.env.company).currency_id
    #     total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
    #     total_amount_currency = sum(others_lines.mapped('amount_currency'))

    #     if not others_lines:
    #         self.line_ids -= existing_terms_lines
    #         return

    #     computation_date = _get_payment_terms_computation_date(self)
    #     account = _get_payment_terms_account(self, existing_terms_lines)
    #     to_compute = _compute_payment_terms(self, computation_date, total_balance, total_amount_currency)
    #     new_terms_lines = _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute)

    #     # Remove old terms lines that are no longer needed.
    #     self.line_ids -= existing_terms_lines - new_terms_lines
    #     if return_date:
    #         return new_terms_lines[-1].date_maturity
        
    #     if new_terms_lines:
    #         self.payment_reference = new_terms_lines[-1].name or ''
    #         self.invoice_date_due = new_terms_lines[-1].date_maturity

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_ids.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_ids.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'avance',
        'return_of_guarantee',
        "prc_gr",
        "prc_advance_deduction",
        "prc_ten_year",
    )
    def _compute_amount(self):
        res = super(AccountMove, self)._compute_amount()
        for move in self:

            currencies = move._get_lines_onchange_currency().currency_id
            amount_untaxed_before_deduction = sum(line.price_subtotal for line in move.invoice_line_ids)
            amount_tax_before_deduction = 0
            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total = 0.0
            total_currency = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0

            for line in move.line_ids:
                if move.is_invoice(include_receipts=True):
                    if not line.exclude_from_invoice_tab and not line.is_tax_line:
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency

                    elif line.account_id.user_type_id.type in ('receivable', 'payable'):
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency

            if move.move_type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1

            for line in move.invoice_line_ids:
                if line.tax_ids:
                    if line.tax_ids[0].amount >= 0:
                        amount_tax_before_deduction += line.tax_ids[0].amount * line.price_subtotal / 100

                if line.is_tax_line:
                    amount_tax_before_deduction += line.price_unit

            # if round(move.avance) > move.amount_total:
            #     raise UserError("La déduction d'avance ne peut pas dépasser le montant total de la facture.")
            
            # amount_advance_deduction = move.currency_id._convert(move.avance, move.company_id.currency_id, move.company_id, move.date or fields.Date.context_today(move))
            # amount_advance_ht = amount_advance_deduction / (1 + move.invoice_line_ids.tax_ids.amount / 100)
            # amount_advance_tax = amount_advance_deduction - amount_advance_ht

            # Update Untaxed amount EXCLUDING lines is_tax_line = True
            move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            move.amount_tax = amount_tax_before_deduction
            
            move.amount_untaxed_before_deduction = amount_untaxed_before_deduction
            move.amount_tax_before_deduction = amount_tax_before_deduction
            move.amount_total_before_deduction = move.amount_untaxed + move.amount_tax
            # move.amount_tax = amount_tax_before_deduction - amount_advance_tax
            move.amount_total = move.amount_total \
                - (round(move.avance or 0.0) + round(move.return_of_guarantee or 0.0)) \
                - (round(move.prc_advance_deduction or 0.0) + round(move.prc_gr or 0.0) + round(move.prc_ten_year or 0.0))
            move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
            move.amount_residual_signed = total_residual

        return res
    
    # def test(self):
    #     for move in self.env["account.move"].search([]):
    #         move._compute_amount()

        # currencies = self._get_lines_onchange_currency().currency_id
        # amount_untaxed_before_deduction = sum(line.price_subtotal for line in self.invoice_line_ids)
        # amount_tax_before_deduction = 0
        # total_residual = 0.0
        # total_residual_currency = 0.0

        # for line in self.line_ids:
        #     if self.is_invoice(include_receipts=True):
        #         if line.account_id.user_type_id.type in ('receivable', 'payable'):
        #             total_residual += line.amount_residual
        #             total_residual_currency += line.amount_residual_currency

        # if self.move_type == 'entry' or self.is_outbound():
        #         sign = 1
        # else:
        #     sign = -1

        # amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
        # amount_residual_signed = total_residual

        # raise Exception(amount_residual, amount_residual_signed)

    def action_post(self):
        result = super(AccountMove, self).action_post()
        for move in self:
            if move.is_rg_release:
                pending_reconcile_lines = self.env["account.move.line"].search([("pending_reconcile_move_id", "=", move.id)])
                account = pending_reconcile_lines.mapped("account_id")
                move_lines = move.line_ids.filtered(lambda l: l.account_id == account)
                (pending_reconcile_lines + move_lines).reconcile()
                pending_reconcile_lines.write({"pending_reconcile_move_id": False})
        return result

    def entry_action_post(self):
        return self.action_post()
    
    def action_received(self): 
        for rec in self:
            # if not rec.partner_id:
            #     raise ValidationError("Le Fournisseur est obligatoire.")
            # elif not rec.invoice_date:
            #     raise ValidationError("La Date de facturation est obligatoire.")
            # elif not rec.ref:
            #     raise ValidationError("La Référence de la facture est obligatoire.")
            # elif not rec.invoice_line_ids:
            #     raise ValidationError("Ligne de la facture est obligatoire.")
            # else:
            rec.state = "received"
    
    def action_validated(self):
        for rec in self:
            rec.state = "validated"

    def open_bolque_reason_wizard(self):
        return {
            "name": "Assistant de blocage",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cancellation.reason',
            'target': 'new',
        }
    
    def action_block(self, reason=None):
        self.update({"reason": reason, "state" : "blocked"})

    def action_cancel_block(self):
        for rec in self:
            rec.state = "received"
    
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AccountMove, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if toolbar:
            print_actions_to_remove = [
                self.env.ref('account.account_invoices_without_payment').id,
                self.env.ref('accounting.action_report_facture_client').id,
                self.env.ref('accounting_pdf_reports.action_report_journal_entries').id,
            ]
            res['toolbar']['print'] = [
                action for action in res['toolbar'].get('print', [])
                if action['id'] not in print_actions_to_remove
            ]
        if toolbar:
            if self._context.get('hide_actions'):
                res['toolbar']['action'] = []
                res['toolbar']['print'] = []
            else:
                pass

        if view_type == 'form' and self.env.context.get('active_id'):
            doc = etree.XML(res['arch'])
            readonly_fields = ['ref', 'invoice_date', 'payment_reference', 'partner_bank_id', 'invoice_payment_term_id', 'invoice_line_ids', 'line_ids', 'currency_id', 'narration', 'deposit_date']
            for field in readonly_fields:
                for node in doc.xpath("//field[@name='%s']" % field):
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    modifiers['no_open'] = True
                    node.set("modifiers", json.dumps(modifiers))

            res['arch'] = etree.tostring(doc, encoding='unicode')

        user_groups = self.env.user.groups_id
        bo_group = self.env.ref('account_plus.acount_move_group_bo')
        
        if view_type == 'form' and bo_group in user_groups:
            doc = etree.XML(res['arch'])
            readonly_fields = [
                'partner_id', 'site_id',
                'deposit_date', 'invoice_payment_term_id', 'invoice_date_due',
                'currency_id', 'invoice_vendor_bill_id',
            ]
            for field in readonly_fields:
                for node in doc.xpath("//field[@name='%s']" % field):
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    modifiers['no_open'] = True
                    node.set("modifiers", json.dumps(modifiers))

            res['arch'] = etree.tostring(doc, encoding='unicode')
        
        if view_type == 'tree':
            root = etree.fromstring(res['arch'])
            if (self.env.user.has_group('account_plus.acount_move_group_creer') or self.env.user.has_group('account_plus.acount_move_group_invoice')):
                root.set("create", "true")
            elif view_type == 'tree':
                root.set("create", "false")
            res['arch'] = etree.tostring(root)

        return res

    # @api.constrains('invoice_date', 'partner_id', 'ref', 'invoice_line_ids')
    # def _check_required_fields(self):
    #     for record in self:
    #         if record.move_type in ['out_invoice', 'in_invoice']:
    #             if not record.partner_id:
    #                 raise exceptions.ValidationError("Le 'Fournisseur' est obligatoire.")
    #             if not record.invoice_date:
    #                 raise exceptions.ValidationError("La 'Date de facturation' est est obligatoire.")
    #             if not record.ref:
    #                 raise exceptions.ValidationError("La 'Référence de la facture' est est obligatoire.")
    #             if not record.invoice_line_ids:
    #                 raise exceptions.ValidationError("Ligne de la facture est obligatoire.")
        
    # @api.model
    # def create(self, vals_list):
    #     moves = super(AccountMove, self).create(vals_list)
    #     for move in moves:
    #         if move.reversed_entry_id:
    #             continue
    #         purchase = move.line_ids.mapped('purchase_line_id.order_id')
    #         if not purchase:
    #             continue
    #         refs = [name_get[1] for name_get in purchase.name_get()]
    #         message = _("This vendor bill has been created from: %s") % ','.join(refs)
    #         move.message_post(body=message)
    #     return moves

    @api.model
    def create(self, values):
        move_type = values.get("move_type")
        move_type_type = values.get("move_type_type")
        if move_type == "in_invoice" and move_type_type != "manual":
            values["state"] = "pre_validated"
        return super().create(values)

    def action_view_purchase_order(self):
        self.ensure_one()
        purchase_orders = self.invoice_line_ids.mapped('purchase_line_id.order_id')
        if purchase_orders:
            action = self.env.ref('purchase.purchase_rfq').read()[0]
            if len(purchase_orders) > 1:
                action['domain'] = [('id', 'in', purchase_orders.ids)]
            else:
                if self.move_type_id.code == "inv_entry":
                    view_id = 'purchase_plus.purchase_order_line_attachment_form' if self.env.user.has_group("account_plus.acount_move_group_achat") else 'account_plus.purchase_order_attachment_form_readonly'
                else:
                    view_id = 'purchase.purchase_order_form' if self.env.user.has_group("account_plus.acount_move_group_achat") else 'account_plus.purchase_order_form_readonly'
                action['views'] = [(self.env.ref(view_id).id, 'form')]
                action['res_id'] = purchase_orders.id

            return action
        
        elif self.invoice_origin:
            action = self.env.ref('purchase.purchase_rfq').read()[0]
            if self.move_type_id.code == "inv_entry":
                view_id = 'purchase_plus.purchase_order_line_attachment_form' if self.env.user.has_group("account_plus.acount_move_group_achat") else 'account_plus.purchase_order_attachment_form_readonly'
            else:
                view_id = 'purchase.purchase_order_form' if self.env.user.has_group("account_plus.acount_move_group_achat") else 'account_plus.purchase_order_form_readonly'
            action['views'] = [(self.env.ref(view_id).id, 'form')]
            action['res_id'] = self.env["purchase.order"].search([("name", "=", self.invoice_origin)], limit=1).id

            return action
        else:
            raise ValidationError("Aucun bon de commande n'est lié à cette facture.")
    
    def action_view_purchase_entry_decompte(self):
        self.ensure_one()

        if not self.invoice_origin:
            raise ValidationError("Aucun Décompte n'est lié à cette facture.")

        purchase_entry = self.env["purchase.entry"].search([("account_move_id", "=", self.id)], limit=1)

        if not purchase_entry:
            purchase_entry = self.env["purchase.entry"].search([("number", "=", self.decompte)], limit=1)

        if not purchase_entry:
            raise ValidationError("Aucun Décompte n'est lié à cette facture.")

        return {
            'name': 'Purchase Entry',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.entry',
            'res_id': purchase_entry.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'views': [(self.env.ref('purchase_plus.purchase_entry_decompt_readonly_form').id, 'form')],
        }

    def action_view_purchase_entry_decompte_client(self):
        self.ensure_one()

        building_attachment = self.env["building.attachment"].search([("account_move_id", "=", self.id)], limit=1)

        if not building_attachment:
            building_attachment = self.env["building.attachment"].search([("number", "=", self.decompte)], limit=1)

        if not building_attachment:
            raise ValidationError("Aucun Décompte n'est lié à cette facture.")

        return {
            'name': 'Décompte Client',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'building.attachment',
            'res_id': building_attachment.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'views': [(self.env.ref('building.building_attachment_inv_situation_form').id, 'form')],
        }
    
    def action_view_bp_client(self):
        self.ensure_one()
        building_order = self.env['building.order'].search([('site_id', '=', self.site_id.id)], limit=1)

        action = self.env.ref('building.building_order_readonly_action').read()[0]
        action['res_id'] = building_order.id
        return action
        
    def action_return_to_cg(self):
        for rec in self:
            rec.state = "received"

    def action_return_to_bo(self):
        self.state = "draft" if self.move_type_type == "manual" else "pre_validated"

    def update_purchase_entry_reference(self):
        move_records = self.search([("based_on", "=", "based_on_attachment")])
        for rec in move_records:
            purchase_entry = rec.env["purchase.entry"].search([("number", "=", rec.ref)], limit=1)
            rec.decompte = purchase_entry.number

    is_avance = fields.Boolean(default=False, compute="_compute_is_avance")

    @api.depends("invoice_origin")
    def _compute_is_avance(self):
        for record in self:
            purchase_order = self.env["purchase.order"].search([("name", "=", self.invoice_origin)], limit=1)
            record.is_avance = purchase_order.avance > 0 if purchase_order else False

    is_invoicing_groupe = fields.Boolean(default=False, compute="_compute_is_invoicing_groupe")

    @api.depends('is_avance')
    def _compute_is_invoicing_groupe(self):
        for record in self:
            record.is_invoicing_groupe = not self.env.user.has_group('account_plus.acount_move_group_invoice')

    def _adjust_line_ids(self):
        self.line_ids.filtered(lambda l:l.is_building_specific).with_context(check_move_validity=False).unlink()

        # taxe_id = self.invoice_line_ids.tax_ids.tax_group_id in ["TVA 18%", "TVA 9%"] if self.invoice_line_ids.tax_ids else False
        taxe_id = self.invoice_line_ids.tax_ids.filtered(lambda t:t.tax_group_id.name in ["TVA 18%", "TVA 9%"]) if self.invoice_line_ids.tax_ids else False
        taxe_amount = taxe_id.amount if taxe_id else 0
        account_tax_id = None
        if taxe_id:
            account_tax_id = self.env["account.tax.repartition.line"].search([("invoice_tax_id", "=", taxe_id.id or taxe_id._origin.id), ("account_id", "!=", False)], limit=1).account_id

        account_advance = self.env["account.account"].search([("code", "=", "4093000")], limit=1)
        amount_advance_deduction = self.currency_id._convert(self.avance, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        amount_advance_ht = amount_advance_deduction / (1 + taxe_amount / 100)
        amount_advance_tax = amount_advance_deduction - amount_advance_ht

        if amount_advance_ht != 0:
            record_line = {
                'account_id': account_advance.id,
                'name': account_advance.name,
                'price_unit': round(abs(amount_advance_ht)),
                'debit': 0,
                'credit': amount_advance_ht,
                'move_id': self.id,
                'exclude_from_invoice_tab': True,
                'currency_id': self.currency_id.id,
                'is_building_specific': True,
            }
            if isinstance(self.id, models.NewId):
                line = self.env['account.move.line'].new(record_line)
                self.invoice_line_ids -= line
            else:
                self.env['account.move.line'].create(record_line)

        if amount_advance_tax > 0 and account_tax_id:
            record_line = {
                'account_id': account_tax_id.id,
                'name': account_tax_id.name,
                'price_unit': round(abs(amount_advance_tax)),
                'debit': 0,
                'credit': amount_advance_tax,
                'move_id': self.id,
                'exclude_from_invoice_tab': True,
                'currency_id': self.currency_id.id,
                'is_building_specific': True,
            }
            if isinstance(self.id, models.NewId):
                line = self.env['account.move.line'].new(record_line)
                self.invoice_line_ids -= line
            else:
                self.env['account.move.line'].create(record_line)
        
        account_return_of_guarantee = self.env["account.account"].search([("code", "=", "4817000")], limit=1)
        amount_return_of_guarantee = self.currency_id._convert(self.return_of_guarantee, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if amount_return_of_guarantee != 0:
            record_line = {
                'account_id': account_return_of_guarantee.id,
                'name': account_return_of_guarantee.name,
                'price_unit': abs(self.return_of_guarantee),
                'debit': 0,
                'credit': amount_return_of_guarantee,
                'move_id': self.id,
                'exclude_from_invoice_tab': True,
                'currency_id': self.currency_id.id,
                'is_building_specific': True,
            }
            
            if isinstance(self.id, models.NewId):
                self.env['account.move.line'].new(record_line)
            else:
                self.env['account.move.line'].create(record_line)
        
        account_rg = self.env["account.account"].search([("code", "=", "4117000")], limit=1)
        amount_rg = self.currency_id._convert(self.prc_gr, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if amount_rg != 0:
            record_line = {
                'account_id': account_rg.id,
                'name': account_rg.name,
                'price_unit': abs(self.prc_gr),
                'debit': amount_rg,
                'credit': 0,
                'move_id': self.id,
                'exclude_from_invoice_tab': True,
                'currency_id': self.currency_id.id,
                'is_building_specific': True,
            }
            
            if isinstance(self.id, models.NewId):
                self.env['account.move.line'].new(record_line)
            else:
                self.env['account.move.line'].create(record_line)
        
        account_prc_ten_year = self.env["account.account"].search([("code", "=", "4117100")], limit=1)
        amount_prc_ten_year = self.currency_id._convert(self.prc_ten_year, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if amount_prc_ten_year != 0:
            record_line = {
                'account_id': account_prc_ten_year.id,
                'name': account_prc_ten_year.name,
                'price_unit': abs(self.prc_ten_year),
                'debit': amount_prc_ten_year,
                'credit': 0,
                'move_id': self.id,
                'exclude_from_invoice_tab': True,
                'currency_id': self.currency_id.id,
                'is_building_specific': True,
            }
            
            if isinstance(self.id, models.NewId):
                self.env['account.move.line'].new(record_line)
            else:
                self.env['account.move.line'].create(record_line)

        account_supp_advance = self.env["account.account"].search([("code", "=", "4191000")], limit=1)
        amount_supp_advance = self.currency_id._convert(self.prc_advance_deduction, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if amount_supp_advance != 0:
            record_line = {
                'account_id': account_supp_advance.id,
                'name': account_supp_advance.name,
                'price_unit': abs(self.prc_advance_deduction),
                'debit': amount_supp_advance,
                'credit': 0,
                'move_id': self.id,
                'exclude_from_invoice_tab': True,
                'currency_id': self.currency_id.id,
                'is_building_specific': True,
            }
            
            if isinstance(self.id, models.NewId):
                self.env['account.move.line'].new(record_line)
            else:
                self.env['account.move.line'].create(record_line)

    @api.onchange("prc_advance_deduction", "prc_gr", "prc_ten_year")
    def _onchange_prc_recompute_dynamic_lines(self):
        self._recompute_dynamic_lines()

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        if self.move_type in ["in_invoice", "out_invoice", "in_refund", "out_refund"]:
            self.line_ids = self.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)
            res = super(AccountMove, self)._recompute_dynamic_lines(recompute_all_taxes, recompute_tax_base_amount)

            account_supplier = self.partner_id.property_account_payable_id
            line_supplier = self.line_ids.filtered(lambda x: x.account_id.code in [account_supplier.code, self.move_type_id.account_id.code])
            line_supplier.name = account_supplier.name

            account_customer = self.partner_id.property_account_receivable_id
            line_customer = self.line_ids.filtered(lambda x: x.account_id.code in [account_customer.code])

            # raise Exception(line_supplier.mapped("debit"), line_supplier.mapped("credit"))

            if self.partner_id.regime_imposition in ["tee", "rme"]:
                for line in self.invoice_line_ids:
                    retenue_taxes = line.tax_ids.filtered(lambda t: t.tax_group_id.name == 'Retenue')
                    if not retenue_taxes:
                        new_taxes = line.tax_ids | self.partner_id.taux_imposition
                    else:
                        non_retenue_taxes = line.tax_ids - retenue_taxes
                        new_taxes = non_retenue_taxes | self.partner_id.taux_imposition
                    line.tax_ids = [(6, 0, new_taxes.ids)]
                
                self._recompute_tax_lines()
                self._recompute_payment_terms_lines()
                self._compute_amount()

            if self.move_type_id.code in ["inv_entry", "inv_reception_supply", "inv_service_no_attachment", "inv_other"]:
                if self.move_type in ['out_invoice', 'out_refund']:
                    amount_total_residual = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))

                    if self.invoice_payment_term_id.id == 20 and len(line_customer) == 2:
                        line_customer[0].debit = amount_total_residual * 0.3
                        line_customer[1].debit = amount_total_residual * 0.7
                    else:
                        line_customer.debit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))

                    line_customer.credit = 0
                      
                else:
                    amount_total_residual = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
                    
                    if self.invoice_payment_term_id.id == 20 and len(line_supplier) == 2:
                        line_supplier[0].credit = amount_total_residual * 0.3
                        line_supplier[1].credit = amount_total_residual * 0.7
                    else:
                        line_supplier.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
                        
                    line_supplier.debit = 0

                if self.move_type_id.account_id and account_supplier.id != self.move_type_id.account_id.id:
                    line_supplier.account_id = self.move_type_id.account_id.id
                    line_supplier.name = self.move_type_id.account_id.name

                self._adjust_line_ids()

            if self.move_type_id.code == "inv_advance":
                order = self.env['purchase.order'].search([('name', '=', self.invoice_origin)], limit=1)
                if order.is_attachment:
                    type_id = self.env['account.move.type'].search([('code', '=', 'inv_entry')], limit=1)
                    line_supplier.account_id = type_id.account_id.id
                    line_supplier.name = type_id.account_id.name
                    line_supplier.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
                    line_supplier.debit = 0
                else:
                    if order.is_service:
                        type_id = self.env['account.move.type'].search([('code', '=', 'inv_service_no_attachment')], limit=1)
                        line_supplier.account_id = type_id.account_id.id
                        line_supplier.name = type_id.account_id.name
                        line_supplier.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
                        line_supplier.debit = 0
                    else:
                        type_id = self.env['account.move.type'].search([('code', '=', 'inv_reception_supply')], limit=1)
                        line_supplier.account_id = type_id.account_id.id
                        line_supplier.name = type_id.account_id.name
                        line_supplier.credit = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date or fields.Date.context_today(self))
                        line_supplier.debit = 0

            if self.move_type_id.code == "inv_rg":
                line_supplier.account_id = self.env["account.account"].search([("code", "=", "4013000")], limit=1).id

            if self.move_type == "out_invoice":                
                def _debit_line(account_code, amount):
                    account = self.env["account.account"].search([("code", "=", account_code)])
                    line = self.line_ids.filtered(lambda l: l.account_id == account)
                    if amount > 0:
                        debit = amount
                        credit = 0
                        if line:
                            line.debit = debit
                            line.credit = credit
                        else:
                            line_values = {
                                "account_id": account.id,
                                "name": account.name,
                                "quantity": 1,
                                "price_unit": amount,
                                "debit": debit,
                                "credit": credit,
                                "move_id": self.id,
                                "exclude_from_invoice_tab": True,
                                "is_building_specific": True,
                                "currency_id": self.currency_id.id
                            }
                            if isinstance(self.id, models.NewId):
                                self.env["account.move.line"].new(line_values)
                            else:
                                self.env["account.move.line"].create(line_values)

                _debit_line("4191000", self.prc_advance_deduction)
                _debit_line("4117000", self.prc_gr)
                _debit_line("4117100", self.prc_ten_year)

            self.line_ids._update_amount_currency()

            return res
        
    @api.onchange("avance")
    def _execute_onchange_invoice_line_ids(self):
        self._onchange_invoice_line_ids()
        
    def _set_invoice_line_vals(self):
        for rec in self:
            line_vals = []
            
            purchase = self.env["purchase.entry"].search([('number', '=', rec.decompte)], limit=1)
            order = self.env["purchase.order"].search([('name', '=', rec.invoice_origin)], limit=1)

            account_4093 = self.env['account.account'].search([('code', '=', '4093000')], limit=1)
            account_6058 = self.env['account.account'].search([('code', '=', '6058000')], limit=1)
            
            if rec.move_type_id.name == "Avance":
                price_unit = (order.amount_untaxed * order.avance) / 100   
                if account_4093:
                    line_vals.append((0, 0, {
                        'account_id': account_4093.id,
                        'price_unit': price_unit,
                        'quantity': 1,
                        'tax_ids': order.order_line[0].taxes_id,
                        'exclude_from_invoice_tab': False,
                        'credit': 0,
                    }))

            elif rec.move_type_id.name == "Décompte":
                # rec.avance = purchase.is_done_avance if purchase.is_done else purchase.avance
                for line in purchase.line_ids:
                    if line.amount_ht_invoiced != 0:
                        percentage = (line.amount_ht_invoiced / purchase.amount_invoiced)
                        if account_6058:
                            line_vals.append((0, 0, {
                                'product_id': line.product_id.id,
                                'quantity': 1,
                                'price_unit': line.amount_ht_invoiced - (purchase.penalty * percentage),
                                'tax_ids': line.tax_ids,
                                'exclude_from_invoice_tab': False,
                                'credit': 0,
                            }))
                            
            if line_vals:
                rec.invoice_line_ids = line_vals

    def set_invoice_line_ids(self):
        for rec in self:
            old_state = rec.state
            old_payment_state = rec.payment_state

            old_payments = rec.line_ids.mapped('matched_debit_ids.debit_move_id.payment_id') | rec.line_ids.mapped('matched_credit_ids.credit_move_id.payment_id')

            if rec.state == "posted":
                rec.button_draft()

            rec.line_ids.unlink()
            rec._set_invoice_line_vals()

            if old_state == "posted":
                rec.action_post()

                if old_payments:
                    rec._reconcile_payments(old_payments)

                rec.payment_state = old_payment_state

            rec._compute_amount()

    def _reconcile_payments(self, old_payments):
        """ Reapply payments after reposting the invoice. """
        for payment in old_payments:
            payment_lines = payment.move_id.line_ids.filtered(lambda l: l.account_id.reconcile and l.account_id.code == '4013000')
            invoice_lines = self.line_ids.filtered(lambda l: l.account_id.reconcile and l.account_id.code == '4013000')
            (invoice_lines + payment_lines).reconcile()

    def action_register_payment(self):
        res = super(AccountMove, self).action_register_payment()
        partners = self.mapped("partner_id")
        if len(partners) > 1:
            raise ValidationError("Assurez-vous que les factures sélectionnées partagent le même fournisseur.")
        return res

    def write(self, vals):
        for move in self:
            other_vals_than_state = any(key not in ["state", "reason", "posted_before", "sequence_prefix", "sequence_number"] for key in vals)
            if move.is_rg_release and other_vals_than_state:
                raise ValidationError("Vous ne pouvez pas modifier cette facture.")
        return super(AccountMove, self).write(vals)

    def _cron_fix_invoice_vat(self):
        SQL_QUERY = """
                SELECT DISTINCT am.id FROM account_move_line aml 
                JOIN account_move am ON aml.move_id = am.id
                JOIN account_move_line_account_tax_rel amlatr ON amlatr.account_move_line_id = aml.id
                JOIN account_tax at ON at.id = amlatr.account_tax_id
                WHERE am.amount_tax = 0 
                    AND am.move_type = 'in_invoice' 
                    AND at.amount <> 0 
                    AND am.state != 'posted'
                    AND am.payment_state = 'not_paid';
            """
        self.env.cr.execute(SQL_QUERY)
        move_ids = [row[0] for row in self.env.cr.fetchall()]
        moves = self.env['account.move'].browse(move_ids)
        for move in moves:
            try:
                move.recompute_dynamic_lines()
            except Exception as e:
                _logger.error(f"Failed to recompute dynamic lines for move ID {move.id}: {e}")

class account_move_line(models.Model):
    _inherit = 'account.move.line'

    is_tax_line = fields.Boolean()
    is_building_specific = fields.Boolean()
    invoice_origin = fields.Char(string="Origine", related="move_id.invoice_origin", store=True)
    pending_reconcile_move_id = fields.Many2one(
        "account.move",
        string="Écriture en attente de lettrage",
        help="Facture brouillon qui rapproche cette écriture comptable une fois comptabilisée.",
    )

    def fields_view_get(self, view_id=None, view_type="tree", toolbar=False, submenu=False):
        res = super(account_move_line, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if toolbar:
            if self._context.get("hide_actions"):
                res["toolbar"]["action"] = []
        return res

    @api.model
    def _get_fields_onchange_subtotal_model(self, price_subtotal, move_type, currency, company, date):
        if move_type in self.move_id.get_outbound_types():
            sign = 1
        elif move_type in self.move_id.get_inbound_types():
            sign = -1
        else:
            sign = 1

        amount_currency = price_subtotal * sign
        balance = currency._convert(amount_currency, company.currency_id, company, date or fields.Date.context_today(self))
        return {
            'amount_currency': amount_currency,
            'currency_id': currency.id,
            'debit': balance > 0.0 and balance or 0.0,
            'credit': balance < 0.0 and -balance or 0.0,
        }
    
    def _update_amount_currency(self):
        for line in self:
            if line.move_id.is_invoice():
                local_currency = self.env.company.currency_id
                tx = line.currency_id._get_conversion_rate(local_currency, line.currency_id, line.move_id.company_id, line.move_id.date)
                line.amount_currency = line.balance*tx


    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')

        vals = [{k:val[k] for k in list(ACCOUNTING_FIELDS)+list(BUSINESS_FIELDS)+['account_id'] if k in val} for val in vals_list]
        lines = super(account_move_line, self).create(vals_list)
        for val in vals:
            if any(val.get(field) for field in ACCOUNTING_FIELDS):
                continue
            elif any(val.get(field) for field in BUSINESS_FIELDS):
                debit = val.get('debit', 0.0)
                credit = val.get('credit', 0.0)
                amount_currency = val.get('amount_currency', 0.0)
                account_id = val.get('account_id', False)
                line = lines.filtered(lambda line: line.account_id.id == account_id)
                if line and debit == 0 and credit == 0 and amount_currency == 0:
                    line.debit = 0
                    line.credit = 0
                    line.amount_currency = 0
                    line.price_subtotal = 0
                    line.price_total = 0
        return lines

    def _prepare_reconciliation_partials(self):        
        ''' Prepare the partials on the current journal items to perform the reconciliation.
        /!\ The order of records in self is important because the journal items will be reconciled using this order.

        :return: A recordset of account.partial.reconcile.
        '''
        def fix_remaining_cent(currency, abs_residual, partial_amount):
            if abs_residual - currency.rounding <= partial_amount <= abs_residual + currency.rounding:
                return abs_residual
            else:
                return partial_amount

        debit_lines = iter(self.filtered(lambda line: line.balance > 0.0 or line.amount_currency > 0.0 and not line.reconciled))
        credit_lines = iter(self.filtered(lambda line: line.balance < 0.0 or line.amount_currency < 0.0 and not line.reconciled))
        void_lines = iter(self.filtered(lambda line: not line.balance and not line.amount_currency and not line.reconciled))
        debit_line = None
        credit_line = None

        debit_amount_residual = 0.0
        debit_amount_residual_currency = 0.0
        credit_amount_residual = 0.0
        credit_amount_residual_currency = 0.0
        debit_line_currency = None
        credit_line_currency = None

        payment_amounts = self._context.get("payment_amounts", {})

        partials_vals_list = []

        while True:

            # Move to the next available debit line.
            if not debit_line:
                debit_line = next(debit_lines, None) or next(void_lines, None)
                
                if not debit_line:
                    break
                to_pay_amount = payment_amounts.get(debit_line.move_id.id)
                is_customer_invoice = debit_line.move_id.move_type == "out_invoice"

                debit_amount_residual = (
                    to_pay_amount and (to_pay_amount if is_customer_invoice else -to_pay_amount)
                ) or debit_line.amount_residual

                if debit_line.currency_id:
                    debit_amount_residual_currency = (
                        to_pay_amount and (to_pay_amount if is_customer_invoice else -to_pay_amount)
                    ) or debit_line.amount_residual_currency
                    debit_line_currency = debit_line.currency_id
                else:
                    debit_amount_residual_currency = debit_amount_residual
                    debit_line_currency = debit_line.company_currency_id

            # Move to the next available credit line.
            if not credit_line:
                credit_line = next(void_lines, None) or next(credit_lines, None)

                if not credit_line:
                    break
                to_pay_amount = payment_amounts.get(credit_line.move_id.id)
                is_customer_invoice = credit_line.move_id.move_type == "out_invoice"

                credit_amount_residual = (
                    to_pay_amount and (to_pay_amount if is_customer_invoice else -to_pay_amount)
                ) or credit_line.amount_residual

                if credit_line.currency_id:
                    credit_amount_residual_currency = (
                        to_pay_amount and (to_pay_amount if is_customer_invoice else -to_pay_amount)
                    ) or credit_line.amount_residual_currency
                    credit_line_currency = credit_line.currency_id
                else:
                    credit_amount_residual_currency = credit_amount_residual
                    credit_line_currency = credit_line.company_currency_id

            min_amount_residual = min(debit_amount_residual, -credit_amount_residual)

            if debit_line_currency == credit_line_currency:
                # Reconcile on the same currency.

                min_amount_residual_currency = min(debit_amount_residual_currency, -credit_amount_residual_currency)
                min_debit_amount_residual_currency = min_amount_residual_currency
                min_credit_amount_residual_currency = min_amount_residual_currency

            else:
                # Reconcile on the company's currency.

                min_debit_amount_residual_currency = credit_line.company_currency_id._convert(
                    min_amount_residual,
                    debit_line.currency_id,
                    credit_line.company_id,
                    credit_line.date,
                )
                min_debit_amount_residual_currency = fix_remaining_cent(
                    debit_line.currency_id,
                    debit_amount_residual_currency,
                    min_debit_amount_residual_currency,
                )
                min_credit_amount_residual_currency = debit_line.company_currency_id._convert(
                    min_amount_residual,
                    credit_line.currency_id,
                    debit_line.company_id,
                    debit_line.date,
                )
                min_credit_amount_residual_currency = fix_remaining_cent(
                    credit_line.currency_id,
                    -credit_amount_residual_currency,
                    min_credit_amount_residual_currency,
                )

            debit_amount_residual -= min_amount_residual
            debit_amount_residual_currency -= min_debit_amount_residual_currency
            credit_amount_residual += min_amount_residual
            credit_amount_residual_currency += min_credit_amount_residual_currency

            partials_vals_list.append({
                'amount': min_amount_residual,
                'debit_amount_currency': min_debit_amount_residual_currency,
                'credit_amount_currency': min_credit_amount_residual_currency,
                'debit_move_id': debit_line.id,
                'credit_move_id': credit_line.id,
            })

            has_debit_residual_left = not debit_line.company_currency_id.is_zero(debit_amount_residual) and debit_amount_residual > 0.0
            has_credit_residual_left = not credit_line.company_currency_id.is_zero(credit_amount_residual) and credit_amount_residual < 0.0
            has_debit_residual_curr_left = not debit_line_currency.is_zero(debit_amount_residual_currency) and debit_amount_residual_currency > 0.0
            has_credit_residual_curr_left = not credit_line_currency.is_zero(credit_amount_residual_currency) and credit_amount_residual_currency < 0.0

            if debit_line_currency == credit_line_currency:
                # The debit line is now fully reconciled because:
                # - either amount_residual & amount_residual_currency are at 0.
                # - either the credit_line is not an exchange difference one.
                if not has_debit_residual_curr_left and (has_credit_residual_curr_left or not has_debit_residual_left):
                    debit_line = None

                # The credit line is now fully reconciled because:
                # - either amount_residual & amount_residual_currency are at 0.
                # - either the debit is not an exchange difference one.
                if not has_credit_residual_curr_left and (has_debit_residual_curr_left or not has_credit_residual_left):
                    credit_line = None

            else:
                # The debit line is now fully reconciled since amount_residual is 0.
                if not has_debit_residual_left:
                    debit_line = None

                # The credit line is now fully reconciled since amount_residual is 0.
                if not has_credit_residual_left:
                    credit_line = None

        return partials_vals_list

    def action_rg(self):
        tree_view_id = self.env.ref("account_plus.account_move_line_view_tree_inherit_rg").id

        domain = [
            ("reconciled", "=", False),
            ("full_reconcile_id", "=", False),
            ("balance", "!=", 0),
            ("move_id.state", "=", "posted"),
            ("journal_id.code", "=", "ACH"),
            ("journal_id.type", "=", "purchase"),
            ("account_id.code", "=", "4817000"),
            ("pending_reconcile_move_id", "=", False),
        ]

        return {
            "name": "Libération RG",
            "type": "ir.actions.act_window",
            "res_model": "account.move.line",
            "view_mode": "tree",
            "views": [(tree_view_id, "tree")],
            "domain": domain,
            "context": {
                "search_default_group_by_site_id": True,
                "search_default_group_by_partner": True,
                "search_default_group_by_invoice_origin": True,
                "create": False,
                "delete": False,
                "edit": False,
                "hide_actions": True,
            },
            "target": "main",
        }

    def create_rg_release_invoice(self):
        all_sites = self.mapped("site_id")
        all_partners = self.mapped("partner_id")
        field = "la même affaire" if len(all_sites) != 1 else "le même fournisseur" if len(all_partners) != 1 else ""
        if field:
            raise UserError(f"Merci de sélectionner des lignes qui partagent {field}.")
        if any(bool(line.pending_reconcile_move_id) for line in self):
            raise UserError("Certaines lignes sont déjà réservées pour la réconciliation.")

        wizard = self.env["account.rg.release"].create({})
        return {
            "name": "Saisir la date comptable",
            "type": "ir.actions.act_window",
            "res_model": "account.rg.release",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
            "context": {"line_ids": self.ids},
        }


class account_payment(models.Model):
    _inherit = 'account.payment'
    
    # amount = fields.Float(string="Montant")
    amount_in_words = fields.Char(string="Montant en lettres", compute='_compute_amount_in_words')
    
    @api.depends('amount')
    def _compute_amount_in_words(self):
        for record in self:
            if record.amount:
                record.amount_in_words = num2words(record.amount, lang='fr').capitalize()
            else:
                record.amount_in_words = ""

                
    def print_virement(self):
        return self.env.ref('account_plus.virement_action').report_action(self)
    

    @api.depends('move_id.line_ids.amount_residual', 'move_id.line_ids.amount_residual_currency', 'move_id.line_ids.account_id')
    def _compute_reconciliation_status(self):
        ''' Compute the field indicating if the payments are already reconciled with something.
        This field is used for display purpose (e.g. display the 'reconcile' button redirecting to the reconciliation
        widget).
        '''
        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            if not pay.currency_id or not pay.id:
                pay.is_reconciled = False
                pay.is_matched = False
            elif pay.currency_id.is_zero(pay.amount):
                pay.is_reconciled = True
                pay.is_matched = True
            else:
                residual_field = 'amount_residual' if pay.currency_id == pay.company_id.currency_id else 'amount_residual_currency'
                if pay.journal_id.default_account_id and pay.journal_id.default_account_id in liquidity_lines.account_id:
                    # Allow user managing payments without any statement lines by using the bank account directly.
                    # In that case, the user manages transactions only using the register payment wizard.
                    pay.is_matched = True
                else:
                    pay.is_matched = pay.currency_id.is_zero(sum(liquidity_lines.mapped(residual_field)))

                reconcile_lines = (counterpart_lines + writeoff_lines).filtered(lambda line: line.account_id.reconcile)
                pay.is_reconciled = pay.currency_id.is_zero(sum(reconcile_lines.mapped(residual_field)))
                
            if pay.approval_state != "submit":
                if pay.is_matched:
                    pay.approval_state = "close"
                else:
                    if pay.payment_method_code in ['check', 'effect']:
                        pay.approval_state = "submitted"
                    else:
                        pay.approval_state = "validated"

    class account_move_type(models.Model):
        _name = "account.move.type"
        _description = "Types de Factures"

        code = fields.Char(string="Code")
        account_id = fields.Many2one("account.account", string="Compte Comptable", domain="[('code', '=like', '4%')]")
        move_ids = fields.One2many("account.move", "move_type_id", string="Factures Associées")
        name = fields.Char(string="Nom", required=True)
        type = fields.Selection(string="Type", required=True, default="manual", selection=
                                [
                                    ("manual", "Manuelle"),
                                    ("automatic", "Automatique"),
                                ])
        is_active = fields.Boolean(string="Active", default=True)
        client_supplier = fields.Selection(
            string="Client/Fournisseur",
            selection=[
                ("client", "Client"),
                ("supplier", "Fournisseur"),
                ("both", "Client / Fournisseur"),
            ],
            required=True,
        )

        def unlink(self):
            for record in self:
                if record.type == 'automatic':
                    raise ValidationError("La suppression des types de facture 'Automatique' est interdite.")
                
                if record.move_ids:
                    raise ValidationError(
                        "Impossible de supprimer ce type de facture car il est lié à une ou plusieurs factures."
                    )
            return super().unlink()

        @api.constrains("name")
        def _check_unique_code_name(self):
            for record in self:
                existing_name = self.search([("name", "=", record.name), ("id", "!=", record.id)])
                existing_code = self.search([("code", "=", record.code), ("id", "!=", record.id)])
                if existing_name:
                    raise ValidationError("Le nom du type de facture doit être unique !")
                if record.code and existing_code:
                    raise ValidationError("Le code du type de facture doit être unique !")


class MailTrackingValue(models.Model):
    _inherit = "mail.tracking.value"

    def create(self, vals_list):
        records = super(MailTrackingValue, self).create(vals_list)        
        exclude_fields = ["state", "entry_state"]
        field_ids = self.env["ir.model.fields"].search([("model", "=", "account.move"), ("name", "in", exclude_fields)]).ids
        for record in records:
            model = record.mail_message_id.model
            if model == "account.move" and record.field.id in field_ids:
                res_id = record.mail_message_id.res_id
                move = self.env["account.move"].browse(res_id)
                if move.move_type == "out_invoice":
                    record.unlink()
        return records