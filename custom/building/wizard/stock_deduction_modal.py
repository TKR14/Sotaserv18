from odoo import fields, models, api
from odoo.exceptions import ValidationError

class StockDeductionModalWizard(models.TransientModel):
    _name = "stock.deduction.modal.wizard"
    _description = "Wizard de déduction d'avance sur réception"

    stock_ids = fields.Many2many("stock.picking", string="Réceptions")
    is_last = fields.Boolean(string="Dernier reliquat")
    amount_total = fields.Float(string="Montant total")
    remaining_advance = fields.Float(string="Reliquat d'avance")
    amount_advance_deduction = fields.Float(string="Déduction d'avance")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        active_ids = context.get('active_ids', [])
        
        if active_ids:
            stock_records = self.env['stock.picking'].browse(active_ids)
            last_stocks = stock_records.filtered(lambda s: s.is_last)

            total = 0.0
            for picking in stock_records:
                order_lines = picking.purchase_id.order_line.filtered(
                    lambda line: line.product_id in picking.move_ids_without_package.mapped("product_id")
                )
                for order_line in order_lines:
                    qty = sum(picking.move_ids_without_package.filtered(
                        lambda m: m.product_id == order_line.product_id
                    ).mapped("product_uom_qty"))
                    line_total = order_line.price_unit * qty
                    if order_line.taxes_id:
                        taxes = order_line.taxes_id.compute_all(
                            order_line.price_unit, order_line.currency_id, qty, order_line.product_id, order_line.order_id.partner_id
                        )
                        line_total = taxes["total_included"]
                    total += line_total
            
            res['amount_total'] = total
            res['stock_ids'] = [(6, 0, active_ids)]

            remaining_advance = 0.0
            if stock_records:
                order = stock_records[0].purchase_id
                advance_move = self.env['account.move'].search([
                    ('invoice_origin', '=', order.name),
                    ('site_id', '=', order.site_id.id),
                    ('move_type', '=', 'in_invoice'),
                    ('move_type_code', '=', 'inv_advance'),
                    ('state', '!=', 'cancel')
                ], limit=1)
                if advance_move:
                    already_deducted = sum(self.env["stock.picking"].search([
                        ("purchase_id", "=", order.id),
                        ('certification_state', '=', 'invoiced')
                    ]).mapped("amount_advance_deduction"))
                    remaining_advance = advance_move.amount_total - already_deducted
            
            res['remaining_advance'] = remaining_advance

            if last_stocks:
                res['is_last'] = True
                res['amount_advance_deduction'] = remaining_advance
        return res

    def action_amount_advance_deduction_verification(self):
        self.ensure_one()

        amount_total = self.amount_total
        remaining_advance = self.remaining_advance

        if self.amount_advance_deduction > amount_total:
            raise ValidationError("La déduction d'avance ne peut pas dépasser le montant total.")
        if self.amount_advance_deduction < 0:
            raise ValidationError("La déduction d'avance ne peut pas être négative.")
        if self.amount_advance_deduction > remaining_advance:
            raise ValidationError("La déduction d'avance ne peut pas dépasser le reliquat d'avance.")

        for picking in self.stock_ids:
            vals = {
                "remaining_advance": remaining_advance,
                "amount_advance_deduction": self.amount_advance_deduction / len(self.stock_ids),
            }
            picking.write(vals)

        if self.amount_advance_deduction == 0 and remaining_advance != 0:
            return {
                "name": "Avertissement",
                "type": "ir.actions.act_window",
                "res_model": "advance.deduction.warning.wizard",
                "view_mode": "form",
                "target": "new",
                "context": {
                    "default_message": "Le champ déduction d'avance est égal à 0. Voulez-vous continuer ?",
                    "default_stock_ids": self.stock_ids.ids,
                },
            }

        return self.stock_ids.action_generate_invoice()
    

class AdvanceDeductionWarningWizard(models.TransientModel):
    _name = "advance.deduction.warning.wizard"
    _description = "Avertissement Déduction d'Avance"

    message = fields.Text(string="Message", readonly=True)
    stock_ids = fields.Many2many("stock.picking", string="Réceptions")

    def action_confirm(self):
        return self.stock_ids.action_generate_invoice()
