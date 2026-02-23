from odoo import models, api

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    
    def button_print(self):
        self.ensure_one()
        if self.is_attachment:  
            return self.env.ref('purchase_plus.detail_action').report_action(self)
        else:
            return self.env.ref("purchase_igaser.purchase_order_report").report_action(self)
 
    # def button_print(self):
    #     return self.env.ref('purchase_plus.detail_action').report_action(self)
