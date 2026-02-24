from odoo import fields, models, api
from odoo.exceptions import ValidationError


class BuildingProfileAssignment(models.Model):
    _name = "building.profile.assignment"
    
    site_id = fields.Many2one("building.site", string="Affaire")
    user_id = fields.Many2one("res.users", string="Utilisateur")
    group_id = fields.Many2one("res.groups", string="Profil", domain=[("type", "=", "profile")])
    active = fields.Boolean(string="Active", default=True)

    @api.constrains("user_id", "group_id")
    def _check_duplication(self):
        count = self.search_count([("site_id", "=", self.site_id.id), ("user_id", "=", self.user_id.id), ("group_id", "=", self.group_id.id)])
        if count > 1:
            raise ValidationError("Ce profil existe déjà.")
        
    def _onsave(self, values):
        group = self.env["res.groups"].browse(values.get("group_id", False) or self.group_id.id)
        user = self.env["res.users"].browse(values.get("user_id", False) or self.user_id.id)
        if user.id not in group.users.ids:
            group.users += user

    @api.model
    def create(self, values):
        self._onsave(values)
        return super(BuildingProfileAssignment, self).create(values)

    def write(self, values):
        self._onsave(values)
        return super(BuildingProfileAssignment, self).write(values)


class ResGroups(models.Model):
    _inherit = "res.groups"

    type = fields.Selection([("profile", "Profil"), ("button", "Bouton")], string="Type")
    model_id = fields.Many2one("ir.model", string="Modèle")

    def write(self, values):
        if self.name != "SOTASERV_SUPERVISEUR_SITE":
            if self._context.get("disable_toggle") == True:
                values = {}
            elif self.type == "profile" and values.get("users") and self._context.get("bypass_check") == None:
                old_users = self.users.ids
                new_users = values["users"][0][2]
                users = [id for id in new_users if id in old_users]
                deleted_users = [id for id in old_users if id not in users]
                for user in deleted_users:
                    active = self.env["building.profile.assignment"].search_count([("group_id.name", "=", self.name), ("user_id", "=", user)])
                    if active:
                        users.append(user)
                values["users"] = [[6, False, users]]
        return super(ResGroups, self).write(values)


class BuildingSite(models.Model):
    _inherit = "building.site"

    @api.depends("profile_ids")
    def _compute_profiles_count(self):
        for record in self:
            record.profiles_count = len(record.profile_ids)
    
    profile_ids = fields.One2many("building.profile.assignment", "site_id", string="Profils")
    profiles_count = fields.Integer("Nombre de profils", compute="_compute_profiles_count", store=True)

    def action_get_profiles(self):
        context = {
            "default_site_id": self.id,
            "bypass_check": True,
            "active_test": False,
            "delete": False,
            "create": False,
            "edit": False,
        }
        
        if not self._context.get("disable_toggle"):
            context.update({
                "create": True,
                "edit": True,
            })

        return {
            "name": "Profils",
            "type": "ir.actions.act_window",
            "res_model": "building.profile.assignment",
            "view_mode": "list,search",
            "target": "current",
            "context": context,
            "domain": [
                ("site_id", "=", self.id),
            ],
        }