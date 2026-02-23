from odoo import models, api
from lxml import etree


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def action_get_user_purchase_requests(self, group, readonly=False, nocreate=False):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids
        not_supervisor = group != "SOTASERV_SUPERVISEUR_SITE"
        context = {
                "group": group,
                "search_default_group_by_requested_by": 1,
        }

        if readonly:
            context["edit"] = not readonly

        if nocreate:
            context["create"] = not nocreate
            context["delete"] = not nocreate

        if not not_supervisor:
            context["is_supervisor"] = True

        if group == "SOTASERV_DIRECTRICE_TECHNIQUE" or group == "SOTASERV_AUDITEUR":
            domain = []
        else:
            domain = [("site_id", "in", site_ids)] if not_supervisor else []

        return {
            "name": "Demandes d'achat",
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "purchase.request",
            "views": [
                (self.env.ref("purchase_igaser.purchase_request_view_tree").id, "tree"),
                (self.env.ref("purchase_igaser.purchase_request_view_form").id, "form")
            ],
            "domain": domain,
            "context": context,
        }
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        result = super(PurchaseRequest, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self.env.context.get("is_supervisor") == True:
            if view_type == "form":
                doc = etree.XML(result["arch"])
                for button in doc.xpath("//header/button"):
                    button.getparent().remove(button)
                result["arch"] = etree.tostring(doc)

        return result
        