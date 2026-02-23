from odoo import models
from odoo.exceptions import UserError

from datetime import datetime


class PurchasePriceComparison(models.Model):
    _inherit = "purchase.price.comparison"

    
    def return_request_purchase_price_comparison(self):
        available_po_records = self.env["purchase.order"].search([("purchase_order_code", "!=", False), ("state", "=", "draft")])
        available_po_records = available_po_records.mapped("purchase_order_code")
        available_po_records = [rec for rec in available_po_records if available_po_records.count(rec) > 1]

        used_po_records = self.env["purchase.price.comparison"].search([("state", "=", "draft")])
        available_po_codes = list(set(available_po_records) - set(used_po_records.mapped("purchase_order_code")))

        if available_po_codes:
            self.env["purchase.request.price.comparison"].initialize()
            
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.request.price.comparison",
                "name": "Comparaison des demandes de prix",
                "view_mode": "form",
                "view_type": "form",
                "views": [[False, "form"]],
                "target": "new",
                "res_id": False,
            }
        else:
            raise UserError("Aucune demande de prix n'a été trouvée.")
        
    def unlink(self, reason=None):
        if self.state == "purchase_validation":
            raise UserError("Il n'est pas possible de supprimer une comparaison liée à un bon de commande.")
        
        for po in self.po_ids:
            po.button_cancel(reason)

        res = super(PurchasePriceComparison, self).unlink()
        return res

    def action_get_price_comparison(self, group):
        profile_ids = self.env["building.profile.assignment"].search([
            ("user_id", "=", self.env.user.id),
            ("group_id.name", "=", group)
        ])
        site_ids = profile_ids.mapped("site_id").ids
        
        domain = [("site_id", "in", site_ids)]
        view_form_id = self.env.ref("purchase_igaser.purchase_price_comparison_form").id
        
        if group == "SOTASERV_DIRECTRICE_TECHNIQUE" or group == "SOTASERV_AUDITEUR":
            domain = []
            view_form_id = self.env.ref("purchase_igaser.purchase_price_comparison_form_readonly").id

        return {
            "name": "Comparaison des Offres",
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "purchase.price.comparison",
            "views": [
                (self.env.ref("purchase_igaser.purchase_price_comparison_tree").id, "tree"),
                (view_form_id, "form"),
            ],
            "domain": domain,
            "context": {
                "create": False,
                "edit": False,
                "delete": False,
            },
        }