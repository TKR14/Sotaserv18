from odoo import models, fields, api

class Dashboard(models.Model):
    _name = "dashboard"
    _description = "dashboard"
    
    site_id = fields.Many2one('building.site', string="Affaire")
    tab = fields.Selection([
        ('tab1', 'Ressource humain'),
        ('tab2', 'Fournitures'),
        ('tab3', 'Prestation de service'),
        ('tab4', 'Outilages'),
        ('tab5', 'Matériels'),
        ('tab6', 'Petite matériels'),
        ('tab7', 'Gasoil')
    ], string='Onglet')
    product_id = fields.Reference(selection=[
        ('hr.job', 'Poste'), 
        ('product.product', 'Article'), 
        ('product.product', 'Outilages'), 
        ('maintenance.vehicle.category', 'Matériels'),
        ('fleet.vehicle', 'Petite matériel'),
    ], string='Article')
    initial_quantity = fields.Float(string="Qté Initial")
    initial_price_unit = fields.Float(string="PU Initial")
    initial_budget = fields.Float(string="Budget Initial")
    consumed_quantity = fields.Float(string="Qté Consommée")
    consumed_amount = fields.Float(string="Montant Consommé")
    remaining_quantity = fields.Float(string="Qté Reliquat")
    remaining_price = fields.Float(string="PU Reliquat")
    remaining_amoun = fields.Float(string="Montant Reliquat")
    difference = fields.Float(string="Écart")