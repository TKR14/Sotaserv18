from odoo import models, fields, api
from lxml import etree


class BuildingSite(models.Model):
    _inherit = "building.site"

    def action_get_user_sites(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        ids = profile_ids.mapped("site_id").ids
        not_supervisor = group != "SOTASERV_SUPERVISEUR_SITE"
        context = {
            "disable_toggle": True,
            "create": False,
            "delete": True,
            "edit": True,
        }

        domain = [("id", "in", ids)] if not_supervisor else []

        if group == "SOTASERV_DIRECTRICE_TECHNIQUE" or group == "SOTASERV_AUDITEUR":
            domain = [] 

        if not not_supervisor:
            context["is_supervisor"] = True

        return {
            "name": "Affaires",
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "building.site",
            "views": [
                (self.env.ref("building.building_site_tree_view").id, "list"),
                (self.env.ref("building_plus.building_site_form_view_inherit_building").id, "form"),
            ],
            "domain": domain,
            "context": context,
        }

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        result = super(BuildingSite, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
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