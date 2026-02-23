from odoo import models, fields
from odoo.exceptions import UserError

class CancellationReason(models.TransientModel):
    _name = "cancellation.reason"
    _description = "Assistant d'Annulation avec Motif"

    reason = fields.Char(string="Motif", required=True)

    def confirm_cancellation(self):
        context = self.env.context

        if context.get("method") == "button_canceled":
            # self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).button_cancel(self.reason)
            purchase_order = self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1)
            if purchase_order:
                avance_invoices = self.env['account.move'].search([
                    ("invoice_origin", "=", purchase_order.name),
                    ('move_type', '=', 'in_invoice'),
                    ('state', '!=', 'cancel')
                ])
                if avance_invoices:
                    raise UserError(
                        "Vous ne pouvez pas annuler un bon de commande qui a une facture d'avance."
                    )
            purchase_order.button_cancel(self.reason)

        elif context.get("method") == "button_po_canceled":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).button_po_canceled(self.reason)
        elif context.get("method") == "action_block":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_block(self.reason)
        elif context.get("method") == "cancel_prl_line":
            self.env[context.get("active_model")].search([("id", "in", context.get("active_ids"))]).cancel_prl_line(self.reason)
        elif context.get("method") == "action_back_to_draft":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_back_to_draft(self.reason)
        elif context.get("index") == "return_payment":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_return_payment(context.get("state"), self.reason)
        elif context.get("method") == "button_back_certification":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_return_certification(self.reason)
        elif context.get("method") == "button_back_cg":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_return_cg(self.reason)

        # [ DECOMPTES
        elif context.get("method") == "back_to_draft":
            return self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).back_to_draft(self.reason)
        elif context.get("method") == "remettre_to_draft_decompt":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).remettre_to_draft_decompt(self.reason)
        elif context.get("method") == "remettre_to_validated_dz_done":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).remettre_to_validated_dz_done(self.reason)
        elif context.get("method") == "remettre_to_validated_dz_not_done":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).remettre_to_validated_dz_not_done(self.reason)
        elif context.get("method") == "remettre_to_provider_validated":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).remettre_to_provider_validated(self.reason)
        elif context.get("method") == "remettre_to_dt":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).remettre_to_dt(self.reason)
        # DECOMPTES ]

        elif context.get("method") == "action_draft_attachment":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_draft_attachment(self.reason)
        elif context.get("method") == "action_back_to_attachment_draft":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_back_to_attachment_draft(self.reason)
            return self.env.ref('building.building_attachment_inv_act').read()[0]
        elif context.get("method") == "back_to_draft_decompte":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).back_to_draft_decompte(self.reason)
        elif context.get("method") == "back_to_dz_validated":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).back_to_dz_validated(self.reason)
        elif context.get("method") == "back_to_customer_validated_decompte":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).back_to_customer_validated_decompte(self.reason)
        elif context.get("method") == "action_draft":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_draft(self.reason)
        elif context.get("method") == "opning_action_back_cp_ct":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).opning_action_back_cp_ct(self.reason)
        elif context.get("method") == "action_cancel_reason":
            self.env[context.get("active_model")].browse(context.get("active_id")).action_cancel(self.reason)
        elif context.get("method") == "action_cancel_decompte_invoice":
            self.env[context.get("active_model")].browse(context.get("active_id")).action_cancel_decompte_invoice(self.reason)

        elif context.get("method") == "action_return_validated":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_return_validated(self.reason)
        elif context.get("method") == "action_return_received":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_return_received(self.reason)
        elif context.get("method") == "action_return_pre_validated":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_return_pre_validated(self.reason)
        elif context.get("method") == "action_return_submitted":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_return_submitted(self.reason)
        elif context.get("method") == "action_return_draft":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_return_draft(self.reason)

        # [ REBUT
        elif context.get("method") == "button_draft_scrap":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).button_draft_scrap(self.reason)
        elif context.get("method") == "button_resubmit_scrap":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).button_resubmit_scrap(self.reason)
        # REBUT]

        # [ RETOUR
        elif context.get("method") == "button_draft_return":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).button_draft_return(self.reason)
        # RETOUR]

        # [ TRANSFERT_INTERNE
        elif context.get("method") == "button_draft_internal_transfer":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).button_draft_internal_transfer(self.reason)
        elif context.get("method") == "button_resubmitted_internal_transfer":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).button_resubmitted_internal_transfer(self.reason)
        # TRANSFERT_INTERNE]

        # [ LIGNES DE DEMANDES D'AFFECTATION RH
        elif context.get("method") == "action_back_to_validated":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_back_to_validated(self.reason)
        # LIGNES DE DEMANDES D'AFFECTATION RH ]

        # [ Fornisseurs
        elif context.get("method") == "action_set_to_draft":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).action_set_to_draft(self.reason)
        # Fornisseurs ]

        # [ Incident Materiel
        elif context.get("method") == "draft_incident":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).draft_incident(self.reason)
        elif context.get("method") == "return_to_submitted":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).return_to_submitted(self.reason)
        elif context.get("method") == "reject_incident":
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).reject_incident(self.reason)
        # Incident Materiel ]
        else:
            self.env[context.get("active_model")].search([("id", "=", context.get("active_id"))], limit=1).unlink(self.reason)
            action = self.env.ref('purchase_igaser.purchase_price_comparison_action')
            action["target"] = "main"
            return action.read()[0]
