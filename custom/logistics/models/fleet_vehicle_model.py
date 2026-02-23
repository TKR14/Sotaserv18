from odoo import models, fields


class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    vehicle_type = fields.Selection(string="Type de véhicule", required=True, selection=
        [
            ("car", "Voiture"),
            ("bike", "vélo"),
            ("machine", "Engin"),
        ]
    )
