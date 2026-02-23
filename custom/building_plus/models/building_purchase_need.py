from odoo import models, api
from lxml import etree


class BuildingPurchaseNeed(models.Model):
    _inherit = "building.purchase.need"

    def action_get_user_needs(self, group, readonly=False):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids
        not_supervisor = group != "SOTASERV_SUPERVISEUR_SITE"
        context = {
            "create": True,
            "edit" : True,
            "delete": True
        }

        domain = [("site_id", "in", site_ids)] if not_supervisor else []

        if readonly:
            context["edit"] = not readonly
            context["create"] = not readonly
            context["delete"] = not readonly
            
        if not not_supervisor:
            context["is_supervisor"] = True
        
        if group == "SOTASERV_DIRECTRICE_TECHNIQUE" or group == "SOTASERV_AUDITEUR":
            domain = [] 

        return {
            "name": "Liste des besoins",
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "building.purchase.need",
            "views": [
                (self.env.ref("building.building_purchase_need_tree").id, "tree"),
                (self.env.ref("building_plus.building_purchase_need_form_inherit_building").id, "form")
            ],
            "domain": domain,
            "context": context,
        }
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        result = super(BuildingPurchaseNeed, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self.env.context.get("is_supervisor") == True:
            if view_type == "form":
                doc = etree.XML(result["arch"])
                for button in doc.xpath("//header/button"):
                    button.getparent().remove(button)
                result["arch"] = etree.tostring(doc)

        arch = etree.fromstring(result["arch"])
        arch.set("delete", "false")
        result["arch"] = etree.tostring(arch)

        return result