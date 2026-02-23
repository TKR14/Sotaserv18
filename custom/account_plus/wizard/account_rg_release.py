from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class AccountRgRelease(models.TransientModel):
    _name = "account.rg.release"

    date = fields.Date(string="Date", default=fields.Date.context_today)

    def create_rg_release_invoice(self):
        journal = self.env["account.journal"].search([("code", "=", "ACH")], limit=1)
        move_type = self.env["account.move.type"].search([("code", "=", "inv_rg")], limit=1)
        if not journal or not move_type: raise ValueError("Journal ou type de facture introuvable.")

        lines = self._context.get("line_ids", [])
        lines = self.env["account.move.line"].browse(lines)
        sum_lines = sum(line.credit for line in lines)
        partner = lines.mapped("partner_id")
        site = lines.mapped("site_id")
        d_account = self.env["account.account"].search([("code", "=", "4817000")], limit=1)
        c_account = self.env["account.account"].search([("code", "=", "4013000")], limit=1)
        no_tax = self.env["account.tax"].search([("amount", "=", 0.0)], limit=1)
        move = self.env["account.move"].create({
            "move_type": "in_invoice",
            "journal_id": journal.id,
            "partner_id": partner.id,
            "move_type_id": move_type.id,
            "date": self.date,
            "invoice_date": self.date,
            "site_id": site.id,
            "ref": str(int(fields.Datetime.now().timestamp())),
            "is_rg_release": True,
            "invoice_line_ids": [(0, 0, {
                "account_id": d_account.id,
                "exclude_from_invoice_tab": False,
                "quantity": 1,
                "price_unit": sum_lines,
                "journal_id": journal.id,
                "partner_id": partner.id,
                "tax_ids": no_tax.ids,
            })]
        })
        lines.write({"pending_reconcile_move_id": move.id})