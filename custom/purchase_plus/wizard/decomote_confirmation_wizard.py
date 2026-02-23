from odoo import models, fields, api

class DecompteConfirmationWizard(models.TransientModel):
    _name = 'decompte.confirmation.wizard'
    _description = "Confirmation du changement d'état du décompte"

    message = fields.Text(string="Message", readonly=True)

    def action_confirm(self):
        context = self.env.context
        record = self.env[context.get("active_model")].browse(context.get("active_id"))

        method = context.get("method")
        if method == "validated_dz_action":
            record.validated_dz_action()
        elif method == "provider_validation_action":
            record.provider_validation_action()
        elif method == "action_done":
            record.action_done()
        else:
            record.action_create_decompte_bill()

        record._update_purchase_order_state()