from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    apr_line_ids = fields.One2many(
        "account.payment.register.line",
        "payment_register_id",
        string="Lignes de paiement",
    )

    def default_get(self, fields):
        res = super().default_get(fields)
        if self._context.get("active_model") == "account.move":
            active_ids = self._context.get("active_ids", [])
            if active_ids:
                move_lines = self.env["account.move"].browse(active_ids).filtered(
                    lambda m: m.state == "posted" and m.amount_residual > 0
                )
                res["apr_line_ids"] = [
                    (0, 0, {
                        "move_id": move.id,
                        "amount": move.amount_residual,
                        "paid": move.amount_total - move.amount_residual,
                    }) for move in move_lines
                ]
            res["group_payment"] = True
        return res

    @api.onchange("apr_line_ids")
    def _onchange_apr_line_ids(self):
        if self.apr_line_ids:
            self.amount = sum(line.amount for line in self.apr_line_ids)

    @api.constrains("apr_line_ids")
    def _check_apr_line_ids(self):
        for line in self.apr_line_ids:
            if line.amount > line.residual:
                raise ValidationError("Le montant à payer ne peut pas dépasser le montant dû.")


class AccountPaymentRegisterLine(models.TransientModel):
    _name = "account.payment.register.line"


    payment_register_id = fields.Many2one(
        "account.payment.register",
        string="Parent",
    )
    move_id = fields.Many2one(
        "account.move",
        string="Facture",
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Devise",
        related="move_id.currency_id",
    )
    amount = fields.Monetary(
        string="À payer",
        currency_field="currency_id",
    )
    paid = fields.Monetary(
        string="Payé",
        currency_field="currency_id",
        readonly=True,
    )
    residual = fields.Monetary(
        string="Dû",
        currency_field="currency_id",
        related="move_id.amount_residual",
        readonly=True,
    )

    @api.onchange("amount")
    def _onchange_amount(self):
        self.payment_register_id.amount = sum(
            line.amount for line in self.payment_register_id.apr_line_ids
        )