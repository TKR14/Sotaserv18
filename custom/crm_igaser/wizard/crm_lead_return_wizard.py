from odoo import api, fields, models, _, tools


class CrmLeadReturnWizard(models.TransientModel):
    _name = 'crm.lead.return.wizard'
    _description = 'Return Lead'

    reason = fields.Text('Motif', required=True)

    def return_lead(self):
        active_id = self.env.context.get('active_id')
        lead = self.env['crm.lead'].browse(active_id)
        lead.write({'reason': self.reason})
        lead.action_return()
