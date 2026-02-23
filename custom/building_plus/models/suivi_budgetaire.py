from odoo import models


class SuiviBudgetaire(models.Model):
    _inherit = "suivi.budgetaire"

    def action_get_user_suivi_budgetaire(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id)])
        names = profile_ids.mapped("site_id").mapped("name")

        domain = [("site", "in", names)]

        if group == "SOTASERV_DIRECTRICE_TECHNIQUE" or group == "SOTASERV_AUDITEUR":
            domain = [] 

        return {
            "name": "Suivi budgétaire",
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "suivi.budgetaire",
            "views": [
                (self.env.ref("building_report.view_suivi_budgetaire_tree").id, "tree"),
            ],
            "domain": domain,
        }