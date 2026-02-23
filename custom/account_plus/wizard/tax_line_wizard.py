from odoo import models, fields, api

class TaxLineWizard(models.TransientModel):
    _name = 'tax.line.wizard'
    _description = 'Wizard to Add Line'

    move_id = fields.Many2one('account.move', required=True)
    account_id = fields.Many2one('account.account', string="Compte", required=True, domain="[('code', '=like', '44%')]")
    price_unit = fields.Float(string="Prix", required=True)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self._context.get('active_id'):
            res['move_id'] = self._context.get('active_id')
        return res

    def action_create_line(self):
        self.ensure_one()

        move = self.move_id

        existing_lines_with_tax = move.line_ids.filtered(lambda l: l.tax_ids)
        for line in existing_lines_with_tax:
            line.tax_ids = [(5, 0, 0)]

        existing_tax_line = move.line_ids.filtered("is_tax_line")
        if existing_tax_line:
            existing_tax_line.unlink()

        self.env['account.move.line'].create({
            'move_id': move.id,
            'account_id': self.account_id.id,
            'name': self.account_id.name,
            'debit': self.price_unit if self.price_unit > 0 else 0.0,
            'credit': 0.0,
            'is_tax_line': True,
        })

        move._compute_amount()
        move._recompute_dynamic_lines()

        return {'type': 'ir.actions.act_window_close'}
