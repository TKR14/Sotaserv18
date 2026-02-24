from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ProductBuyer(models.Model):
    _name = "product.buyer"
    
    category_id = fields.Many2one("product.category", string="Catégorie")
    user_id = fields.Many2one("res.users", string="Acheteur", domain=[("employee_id", "!=", False)])
    is_supervisor = fields.Boolean(string="Superviseur", default=False)

    @api.constrains("user_id")
    def _check_duplication(self):
        for record in self:
            count = self.search_count([("category_id", "=", record.category_id.id), ("user_id", "=", record.user_id.id)])
            if count > 1:
                raise ValidationError(f"L'utilisateur {record.user_id.name} est déjà affecté à cette catégorie.")

    @api.onchange("is_supervisor")
    def _onchange_is_supervisor(self):
        default_supervisors = self.env.ref("hr_igaser.product_buyer_default_supervisors_group").users
        if self.user_id in default_supervisors:
            self.is_supervisor = True


class ProductCategory(models.Model):
    _inherit = "product.category"

    @api.depends("buyer_ids", "buyer_ids.is_supervisor")
    def _compute_count(self):
        for record in self:
            record.buyers_count = len(record.buyer_ids.filtered(lambda buyer: not buyer.is_supervisor))
            record.supervisors_count = len(record.buyer_ids.filtered(lambda buyer: buyer.is_supervisor))

    @api.depends("buyer_ids", "buyer_ids.is_supervisor")
    def _compute_secondary_buyer_ids(self):
        all_categories = self.search([])
        for category in all_categories:
            category.secondary_buyer_ids = [(6, 0, [])]
            if category.buyers_count == 0 and category.parent_id:
                parent_category = category.parent_id
                while True:
                    if parent_category.buyers_count > 0:
                        category.secondary_buyer_ids = [(6, 0, parent_category.buyer_ids.filtered(lambda buyer: not buyer.is_supervisor).mapped("user_id").ids)]
                        break
                    elif parent_category.parent_id:
                        parent_category = parent_category.parent_id
                    else:
                        break

    @api.depends("buyer_ids", "buyer_ids.user_id", "buyer_ids.is_supervisor")
    def _compute_supervisor_ids(self):
        default_supervisors = self.env.ref("hr_igaser.product_buyer_default_supervisors_group").users
        categories = self.search([])
        for category in categories:
            if not self._context.get("write_priority"):
                category.buyer_ids = [
                    (0, 0, {"user_id": supervisor.id, "category_id": category.id, "is_supervisor": True})
                    for supervisor in default_supervisors if supervisor not in category.buyer_ids.mapped("user_id")
                ]
            category.supervisor_ids = [(6, 0, category.buyer_ids.filtered(lambda buyer: buyer.is_supervisor).mapped("user_id").ids)]

    buyer_ids = fields.One2many("product.buyer", "category_id", string="Acheteurs")
    supervisor_ids = fields.Many2many("res.users", relation="category_supervisor_rel", column1="category_id", column2="supervisor_id", string="Superviseurs", compute="_compute_supervisor_ids", store=True)
    secondary_buyer_ids = fields.Many2many("res.users", string="Acheteurs secondaires", compute="_compute_secondary_buyer_ids", store=True)

    buyers_count = fields.Integer("Nombre d'acheteurs", compute="_compute_count", store=True)
    supervisors_count = fields.Integer("Nombre de superviseurs", compute="_compute_count", store=True)

    category_type = fields.Selection(
        selection=[
            ('equipment', 'Matériel'),
            ('small_equipment', 'Petit Matériel'),
            ('logistics_consumable', 'Consommable logistique'),
            ('other', 'Autre')
        ],
        string='Type de Catégorie'
    )

    def fix_dev(self):
        for category in self:
            category._compute_supervisor_ids()

    def action_product_buyer(self):
        return {
            "name": "Acheteurs",
            "type": "ir.actions.act_window",
            "res_model": "product.buyer",
            "view_mode": "list",
            "domain": [("category_id", "=", self.id)],
            "context": {
                "default_category_id": self.id,
            },
            "target": "current",
        }

    @api.model
    def create(self, vals):        
        default_supervisors = self.env.ref("hr_igaser.product_buyer_default_supervisors_group").users
        vals["buyer_ids"] = [(0, 0, {"user_id": supervisor.id, "is_supervisor": True}) for supervisor in default_supervisors]
        return super(ProductCategory, self).create(vals)


class ResGroup(models.Model):
    _inherit = "res.groups"

    def write(self, vals):
        for group in self:
            if group == self.env.ref("hr_igaser.product_buyer_default_supervisors_group"):
                if "users" in vals:
                    old_users = group.users.ids
                    new_users = vals["users"][0][2]
                    add_users = [user for user in new_users if user not in old_users]
                    del_users = [user for user in old_users if user not in new_users]
                    to_change = self.env["product.buyer"]
                    to_create = []
                    to_unlink = self.env["product.buyer"]
                    categories = self.env["product.category"].search([])
                    for category in categories:
                        buyers = category.buyer_ids
                        to_change |= buyers.filtered(lambda buyer: buyer.user_id.id in new_users and not buyer.is_supervisor)
                        to_create.extend(
                            {"user_id": user, "category_id": category.id, "is_supervisor": True}
                            for user in add_users if user not in buyers.mapped("user_id").ids
                        )
                        to_unlink |= buyers.filtered(lambda buyer: buyer.user_id.id in del_users)
                    to_change.is_supervisor = True
                    self.env["product.buyer"].with_context(write_priority=True).create(to_create)
                    to_unlink.with_context(write_priority=True).unlink()
        return super(ResGroup, self).write(vals)