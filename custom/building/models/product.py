from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_component = fields.Boolean('Produit Composant')
    is_finished = fields.Boolean('Produit fini')
    is_timesheet = fields.Boolean('Produit Temps de présence')
    is_material = fields.Boolean('Matériau')
    is_conso = fields.Boolean('Consommable')
    is_fuel = fields.Boolean("Carburant", related="categ_id.is_fuel")
    fuel_type = fields.Selection(string="Type de carburant", default=False, selection=[
        ("diesel", "Gasoil"),
        ("super", "Super"),
    ])
    reference_price = fields.Float("Prix référence")

    @api.constrains('name')
    def check_name(self):
        for product_template in self:
            product_template_id = self.env['product.template'].search([('name', '=', product_template.name),
                                                                       ('id', '!=', product_template.id)])
            if product_template_id:
                raise ValidationError(_('Il existe deja un produit avec le même nom %s!', product_template.name))


class ProductCategory(models.Model):
    _inherit = "product.category"

    is_coffrage = fields.Boolean('Coffrage/EChaffaudage?')
    is_diesel = fields.Boolean('Gasoil?')
    is_fuel = fields.Boolean("Carburant")