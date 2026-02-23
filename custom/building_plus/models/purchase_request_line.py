from odoo import fields, models, api
from odoo.exceptions import UserError


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    def action_get_user_purchase_request_lines(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids
        not_supervisor = group not in ["SOTASERV_SUPERVISEUR_SITE", "SOTASERV_MAGASINIER"]

        domain = []
        if not_supervisor:
            domain = [("site_id", "in", site_ids)]        
        if group == "SOTASERV_MAGASINIER":
            domain.append(("state", "=", "transfer_validated"))
        if group == "SOTASERV_DIRECTRICE_TECHNIQUE" or group == "SOTASERV_AUDITEUR":
            domain = []

        return {
            "name": "Lignes de demande d'achat",
            "type": "ir.actions.act_window",
            "view_mode": "tree",
            "res_model": "purchase.request.line",
            "search_view_id": (self.env.ref("purchase_igaser.purchase_request_line_view_search").id, "search"),
            "views": [
                (self.env.ref("purchase_igaser.purchase_request_line_view_tree").id, "tree"),
            ],
            "domain": domain,
            "context": {
                "create": False,
                "delete": False,
                "edit": False,
                "search_default_group_state_id": 1,
            },
        }
    
    def dev(self):
        pass

    def action_get_purchase_request_lines_readonly(self):
        return {
            "name": "Lignes de demande d'achat (Principal & Logistique)",
            "type": "ir.actions.act_window",
            "view_mode": "tree",
            "res_model": "purchase.request.line",
            "views": [
                (self.env.ref("purchase_plus.purchase_request_line_view_tree_readonly").id, "tree"),
            ],
            "domain": [("site_id.number", "in", ["000", "002"])],
            "context": {
                "create": False,
                "delete": False,
                "edit": False,
                "hide_create_rfq_action": True,
                "search_default_site_id": True,
            },
        }

    def button_reset_to_approved(self):
        for line in self:
            if line.state != 'transfer_validated':
                raise UserError("Vous devez sélectionner uniquement les lignes ayant un statut 'Transfert Validé'.")
            line.state = 'approved'

