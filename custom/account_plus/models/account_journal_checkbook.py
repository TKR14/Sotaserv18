from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError


class AccountJournalCheckbook(models.Model):
    _name = "account.journal.checkbook"
    _rec_name = "number"

    journal_id = fields.Many2one("account.journal", string="Journal bancaire", ondelete="cascade")
    number = fields.Char("Numéro", required=True)
    start = fields.Integer("Début", required=True)
    size = fields.Integer("Taille", required=True)
    type = fields.Selection(string="Type", required=True, selection=
        [
            ("check", "Chèque"),
            ("effect", "Effet"),
        ]
    )
    check_ids = fields.One2many("account.journal.check", "checkbook_id", string="Chèques")
    is_locked = fields.Boolean("Verrouillé", default=False)

    @api.constrains("start", "size")
    def _cheque_order(self):
        for record in self:
            if record.start < 0:
                raise UserError("Assurez-vous que le Début est positive.")
            if record.size < 0:
                raise UserError("Assurez-vous que la Taille est positive.")

    def get_checks(self):
        if not self.is_locked:
            self.create_checks()
        return {
            "name": "Chèques",
            "type": "ir.actions.act_window",
            "res_model": "account.journal.checkbook",
            "view_mode": "form",
            "views": [
                (self.env.ref("account_plus.account_journal_checkbook_view_form").id, "form")
            ],
            "res_id": self.id,
            "context": {
                "create": False,
                "delete": False,
                "edit": False,
            },
            "target": "new",
        }

    def create_checks(self):
        new_checks = []
        for n in range(self.start, self.start + self.size):
            new_checks.append(
                {
                    "checkbook_id": self.id,
                    "serial_number": f"{self.number}{n:04}",
                }
            )
        self.env["account.journal.check"].create(new_checks)
        self.is_locked = True

    def unlink(self):
        for record in self:
            if bool(record.check_ids.mapped("payment_id")):
                raise UserError(_("Impossible de supprimer un chéquier utilisé."))
        return super(AccountJournalCheckbook, self).unlink()


class AccountJournalCheck(models.Model):
    _name = "account.journal.check"
    _rec_name = "serial_number"

    checkbook_id = fields.Many2one("account.journal.checkbook", string="Chéquier", ondelete="cascade")
    journal_id = fields.Many2one("account.journal", string="Journal bancaire", related="checkbook_id.journal_id")
    serial_number = fields.Char("Numéro de série")
    state = fields.Selection(string="Status", default="valid", selection=
        [
            ("valid", "Valide"),
            ("used", "Utilisé"),
            ("canceled", "Annulé"),
        ]
    )
    payment_id = fields.Many2one("account.payment", string="Paiement")

    def use(self, payment_id):
        self.payment_id = payment_id
        self.state = "used"
    
    def cancel(self):
        self.state = "canceled"
        return self.checkbook_id.get_checks()


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    journal_type = fields.Selection("Type du journal", related="journal_id.type")
    check_id = fields.Many2one("account.journal.check", string="Chèque", domain="[('journal_id', '=', journal_id), ('checkbook_id.type', '=', payment_method_code), ('state', '=', 'valid')]")

    def action_create_payments(self):
        result = super(AccountPaymentRegister, self).action_create_payments()
        if self.check_id:
            payment_id = result["res_id"]
            self.check_id.use(payment_id)
            self.env["account.payment"].browse(payment_id).check_id = self.check_id.id
        return result

    @api.onchange("check_id", "journal_type", "payment_method_code")
    def _onchange_check_id(self):
        if self.journal_type == "bank" and self.payment_method_code in ["check", "effect"]:
            self.communication = ""
            if self.check_id:
                self.communication = self.check_id.serial_number
        else:
            self.check_id = None
            self._compute_communication()

    def _post_payments(self, to_process, edit_mode=False):
        if self.env.context.get("keep_payments_draft", False):
            return
        return super(AccountPaymentRegister, self)._post_payments(to_process, edit_mode)

    def _reconcile_payments(self, to_process, edit_mode=False):
        if self.env.context.get("keep_payments_draft", False):
            return
        return super(AccountPaymentRegister, self)._reconcile_payments(to_process, edit_mode)

    def action_create_payments_parent(self):
        if self.check_id and self.check_id.state == "used":
            raise ValidationError("Ce chèque est déjà utilisé, veuillez en choisir un autre.")
            
        payment_amounts = {
            line.move_id.id: line.amount for line in self.apr_line_ids
        }
        return self.with_context({"payment_amounts": payment_amounts}).action_create_payments()


class AccountPayment(models.Model):
    _inherit = "account.payment"

    journal_type = fields.Selection("Type du journal", related="journal_id.type")
    check_id = fields.Many2one("account.journal.check", string="Chèque", domain="[('journal_id', '=', journal_id), ('checkbook_id.type', '=', payment_method_code), ('state', '=', 'valid')]")
    # state = fields.Selection(string="Statut", default="draft", selection=
    #     [
    #         ("draft", "Brouillon"),
    #         ("validated", "Validé"),
    #         ("approved", "Approuvé"),
    #         ("submitted_bo", "Remis au BO"),
    #         ("submitted", "Remis"),
    #         ("posted", "Comptabilisé"),
    #         ("cancel", "Annulé"),
    #     ]
    # )
    approval_state = fields.Selection(string="Statut d'approbation", default="submit", selection=
        [
            ("submit", "Soumettre"),
            ("validation", "Attente Validation DG"),
            ("validated", "Validé DG"),
            ("submitted", "Remis"),
            ("close", "Rapproché"),
        ],
        tracking=True
    )
    state_1 = fields.Selection(string="Statut", related="approval_state", tracking=False)
    state_2 = fields.Selection(string="Statut", related="approval_state", tracking=False)

    @api.model
    def _get_method_codes_using_bank_account(self):
        return ['transfer']

    @api.onchange("journal_type", "payment_method_code")
    def _onchange_journal_type_payment_method_code(self):
        if self.journal_type != "bank" or self.payment_method_code not in ["check", "effect"]:
    
            self.check_id = False

    def action_submit(self):
        self.approval_state = "validation"

    def action_validate(self):
        for rec in self:
            if rec.approval_state != "validation":
                raise UserError(_("Vous ne pouvez pas valider un paiement qui n'est pas en attente de validation."))
            rec.approval_state = "validated"

    def action_submit_bo(self):
        self.approval_state = "submitted"

    def action_return_payment(self, state, reason):
        self.write({'approval_state': state})
        body = f"""
        <ul>
          <li>Motif de remise: {reason}</li>
        <ul/>
        """
        self.message_post(body=body)

    def open_cancellation_reason_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Assistant d'Annulation",
            "res_model": "cancellation.reason",
            "view_mode": "form",
            "target": "new",
        }

    def action_post(self):
        result = super(AccountPayment, self).action_post()
        self.state = "posted"
        return result

    def action_draft(self):
        result = super(AccountPayment, self).action_draft()
        self.state = "draft"
        return result

    @api.model
    def create(self, values):
        payments = super(AccountPayment, self).create(values)
        for payment in payments:
            if payment.check_id:
                payment.check_id.use(payment.id)
        return payments

    def write(self, values):
        new_check_id = values.get("check_id")
        if new_check_id:
            self.check_id.state = "valid"
            self.check_id.payment_id = None
            self.env["account.journal.check"].browse(new_check_id).use(self.id)
        return super(AccountPayment, self).write(values)

    def unlink(self):
        for payment in self:
            if payment.check_id:
                payment.check_id.state = "canceled"
        return super(AccountPayment, self).unlink()