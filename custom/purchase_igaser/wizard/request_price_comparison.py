from odoo import models, _
from datetime import datetime


class purchase_request_price_comparison(models.TransientModel):
    _name = 'purchase.request.price.comparison'

    def create_request_price_comparison(self):
        po_ids = self.env["purchase.order"].search([("purchase_order_code", "=", self.purchase_order_codes.name)]).ids
        purchase_price_comparison_obj = self.env["purchase.price.comparison"]
        year = datetime.today().year
        comparisons_current_year = purchase_price_comparison_obj.search([("year", "=", str(year))])
        record_comparison = {

            "name": str(len(comparisons_current_year)+1) + "/"+ str(year),
            "date_comparison": datetime.today(),
            "purchase_order_code": self.purchase_order_codes.name,
            "year": str(year)
        }
        new_comparison = purchase_price_comparison_obj.create(record_comparison)
        if po_ids:
            for po_id in po_ids:
                po = self.env["purchase.order"].browse(po_id)
                po.price_comparison_id = new_comparison.id
                po.state = "compare_offers"
                for line in po.order_line:
                    line.price_comparison_id = new_comparison.id

        res_id = new_comparison.id
            
        return {
            "type": "ir.actions.act_window",
            "name": "Comparaison des demandes de prix",
            "res_model": "purchase.price.comparison",
            "view_mode": "form",
            "target": "current",
            "res_id": res_id,
        }