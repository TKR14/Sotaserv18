from odoo import _, api, fields, models


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"
    
    def create_returns(self):
        self.picking_id.is_returned = True
        return super(StockReturnPicking, self).create_returns()