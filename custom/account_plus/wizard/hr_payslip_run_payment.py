from odoo import models, fields, api
from odoo.exceptions import UserError


class HrPayslipRunPayment(models.TransientModel):
    _name = "hr.payslip.run.payment"

    move_id = fields.Many2one("account.move", string="Pièce Comptable")
    line_ids = fields.One2many("hr.payslip.run.payment.line", "parent_id", string="Paiements")
    show_check_id_column = fields.Boolean(string="Afficher Champ Chèque", compute="_compute_show_check_id_column")

    @api.depends("line_ids.journal_id")
    def _compute_show_check_id_column(self):
        for record in self:
            record.show_check_id_column = any(line.payment_method_id.code in ["check", "effect"] for line in record.line_ids)

    def button_register_payments(self):
        if any(not line.journal_id or not line.payment_method_id for line in self.line_ids):
            raise UserError("Veuillez sélectionner le journal et le moyen de paiement pour chaque paiement.")
        if any(line.payment_method_code in ["check", "effect"] and not line.check_id for line in self.line_ids):
            raise UserError("Veuillez sélectionner le chèque pour les paiements utilisant le moyen de paiement Chèque/Effet.")
        has_check_id = len(self.line_ids.filtered(lambda line: line.check_id))
        checks = len(self.line_ids.mapped("check_id"))
        if has_check_id != checks:
            raise UserError("Chaque paiement doit avoir un chèque unique.")

        payments = []
        for line in self.line_ids:
            payments.append({
                "ref": line.ref,
                "date": line.date,
                "amount": line.amount,
                "partner_id": line.partner_id.id,
                "journal_id": line.journal_id.id,
                "payment_method_id": line.payment_method_id.id,
                "check_id": line.check_id.id,
                "payment_type": line.amount > 0 and "outbound" or "inbound",
                "partner_type": "supplier",
                "invoice_origin": self.move_id.id,
            })

        payments = self.env["account.payment"].create(payments)
        payments.action_post()

        to_reconcile = []
        for payment in payments:
            for payment_line in payment.line_ids.filtered(lambda l: l.account_id.user_type_id.type in ["payable", "receivable"]):
                move_lines = self.move_id.line_ids.filtered(lambda l: l.account_id == payment_line.account_id and l.partner_id == payment_line.partner_id)
                to_reconcile.append(move_lines + payment_line)
        for group in to_reconcile:
            group.reconcile()
        self.move_id.write({"is_payrun_paid": True})


class HrPayslipRunPaymentLine(models.TransientModel):
    _name = "hr.payslip.run.payment.line"

    parent_id = fields.Many2one("hr.payslip.run.payment", string="Parent")

    ref = fields.Char(string="Référence")
    date = fields.Date(string="Date")
    amount = fields.Float(string="Montant")
    account_id = fields.Many2one("account.account", string="Compte")
    partner_id = fields.Many2one("res.partner", string="Fournisseur")
    payment_type = fields.Char("Type de Paiement")

    journal_id = fields.Many2one("account.journal", string="Journal", domain=[("type", "in", ["bank", "cash"])])
    available_payment_methods_ids = fields.Many2many("account.payment.method", string="Moyens de paiement disponibles", compute="_compute_available_payment_methods_ids")
    payment_method_id = fields.Many2one("account.payment.method", string="Moyen de paiement", domain="[('id', 'in', available_payment_methods_ids)]")
    payment_method_code = fields.Char(related="payment_method_id.code", string="Code Moyen de Paiement")
    check_id = fields.Many2one("account.journal.check", string="Chèque", domain="[('journal_id', '=', journal_id), ('checkbook_id.type', '=', payment_method_code), ('state', '=', 'valid')]")

    @api.onchange("payment_method_id")
    def onchange_payment_method_id(self):
        self.check_id = False

    @api.onchange("journal_id")
    def onchange_journal_id(self):
        self.payment_method_id = False

    @api.depends("journal_id")
    def _compute_available_payment_methods_ids(self):
        for record in self:
            record.available_payment_methods_ids = []
            if record.journal_id:
                record.available_payment_methods_ids = record.payment_type == "inbound" and record.journal_id.inbound_payment_method_ids or record.journal_id.outbound_payment_method_ids