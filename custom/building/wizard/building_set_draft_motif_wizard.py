from odoo import models, fields

class SetDraftMotifWizard(models.TransientModel):
    _name = 'set.draft.motif.wizard'
    _description = 'Wizard pour définir le motif lors du passage à l\'état Brouillon'

    motif = fields.Char(string="Motif", required=True)

    def action_set_draft(self):
        active_id = self.env.context.get('active_id')
        record = self.env['maintenance.request.resource.material'].browse(active_id)

        record.state = 'draft'

        record.motif = self.motif

        record.message_post(
            body=f"Changement d'état en Brouillon. Motif : {self.motif}",
            message_type='comment',
            # subtype_xmlid='mail.mt_comment'
        )

        return {'type': 'ir.actions.act_window_close'}
    
    