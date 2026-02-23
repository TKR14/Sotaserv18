from odoo import models, fields, api, tools


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"


    def clean_purchase_request_line(self):
        pols = self.env["purchase.order.line"].search([("purchase_request_lines", "in", self.ids)])
        pos = pols.mapped("order_id")

        ppc = self.env["purchase.price.comparison"].search([("purchase_order_code", "in", [p.purchase_order_code for p in pos])])
        sps = self.env["stock.picking"].search([("origin_id", "in", pos.ids)])

        if not sps:
            if pos:
                for po in pos:
                    po.button_cancel(reason="Nettoyage des données")
            if ppc:
                for pp in ppc:
                    pp.state = "po_canceled"
                    pp.unlink(reason="Nettoyage des données")

            self.state = "trash"

        pos.mapped("order_line").mapped("purchase_request_lines").update({"state": "trash"})


# class PurchaseOrder(models.Model):
#     _inherit = "purchase.order"

#     def button_cancel(self, reason=None):
#         super(PurchaseOrder, self).button_cancel(reason)
#         # Fuck around here, bitch