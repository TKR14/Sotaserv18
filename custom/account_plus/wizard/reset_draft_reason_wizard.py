from odoo import models, fields

class ResetToDraftReasonWizard(models.TransientModel):
    _name = 'reset.draft.reason.wizard'
    _description = 'Motif de Remise en Brouillon'

    reason = fields.Char(string="Motif", required=True)

    def action_confirm_reset(self):
        active_id = self.env.context.get('active_id')
        record = self.env['account.move'].browse(active_id)
        record.button_draft(reason=self.reason)
        return {'type': 'ir.actions.act_window_close'}
