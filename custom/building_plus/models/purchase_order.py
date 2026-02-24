from odoo import models, fields, api
from lxml import etree

from collections import Counter


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    reason = fields.Char(string="Motif", tracking=True)

    def open_cancellation_reason_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Assistant d'Annulation",
            "res_model": "cancellation.reason",
            "view_mode": "form",
            "target": "new",
        }

    def action_get_user_purchase_orders(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids
        
        domain = [("site_id", "in", site_ids), ("is_attachment", "=", False), ("state", "in", ["purchase", "done", "full", "partial", "po_canceled"])]
        view_tree_id = self.env.ref("purchase.purchase_order_view_tree").id
        view_form_id = self.env.ref("account_plus.purchase_order_form_readonly").id

        if group in ["SOTASERV_DIRECTRICE_TECHNIQUE", "SOTASERV_AUDITEUR"]:
            domain = [("is_attachment", "=", False), ("state", "in", ["purchase", "done", "full", "partial", "po_canceled"])] 
            view_tree_id = self.env.ref("purchase_igaser.purchase_order_view_tree_readonly").id

        return {
            "name": "Bons de Commande sans Attachement",
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "purchase.order",
            "views": [
                (view_tree_id, "list"),
                (view_form_id, "form"),
            ],
            "search_view_id": (self.env.ref("purchase_plus.purchase_order_view_search").id, "search"),
            "domain": domain,
            "context": {
                "create": False,
                "delete": False,
                "edit": False,
                "hide_actions": True,
                "hide_field": "state_2",
                "search_default_group_by_state": True,
            },
        }
    
    def action_get_user_purchase_orders_service(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids
        
        domain = [("site_id", "in", site_ids), ("is_attachment", "=", False), ("state", "in", ["purchase", "done", "full", "partial",]), ("is_service", "=", True)]
        view_tree_id = self.env.ref("purchase_igaser.purchase_order_view_tree_readonly").id
        view_form_id = self.env.ref("purchase_plus.view_purchase_order_form_inherited_magasinier").id

        return {
            "name": "Bons de Commande",
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "purchase.order",
            "views": [
                (view_tree_id, "list"),
                (view_form_id, "form"),
            ],
            "search_view_id": (self.env.ref("purchase_plus.purchase_order_view_search").id, "search"),
            "domain": domain,
            "context": {
                "create": False,
                "delete": False,
                "edit": True,
                "hide_actions": True,
                "hide_field": "state_2",
                "search_default_group_by_state": True,
            },
        }

    def action_get_user_purchase_orders_attachment(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids
        return {
            "name": "Bons de Commande avec Attachement",
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "purchase.order",
            "views": [
                (self.env.ref("purchase_plus.purchase_order_tree").id, "list"),
                (self.env.ref("purchase_plus.purchase_order_line_attachment_form").id, "form"),
            ],
            "search_view_id": (self.env.ref("purchase_plus.purchase_order_view_search").id, "search"),
            "domain": [("site_id", "in", site_ids), ("is_attachment", "=", True), ("state", "in", ["purchase", "done", "full", "partial", "po_canceled"])],
            "context": {
                "create": False,
                "delete": False,
                "edit": False,
                "hide_actions": True,
                "hide_field": "state",
                "show_search_filter_state_2": True,
                "search_default_group_by_state_2": True,
            },
        }

    def action_get_rfq(self, group):
        profile_ids = self.env["building.profile.assignment"].search([("user_id", "=", self.env.user.id), ("group_id.name", "=", group)])
        site_ids = profile_ids.mapped("site_id").ids

        return {
            "name": "Demandes de Prix",
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "purchase.order",
            "views": [
                (self.env.ref("purchase.purchase_order_tree").id, "list"),
                (self.env.ref("account_plus.purchase_order_form_readonly").id, "form"),
            ],
            "domain": [("state", "in", ["draft", "sent"])], 
            "context": {
                "create": False,
                "edit": False, 
                "delete": False,
            },  
        }

    def button_cancel(self, reason=None):
        request_lines = self.env["purchase.request.line"].search([("purchase_lines", "in", self.order_line.ids)])
        request_lines.state = "approved"
        request_lines.has_pr = False
        request_lines.purchase_order_code = ""
        service_lines = request_lines.filtered(lambda l: l.product_id.type == "service")
        service_lines.mapped("purchase_request_allocation_ids").update({"allocated_product_qty": 0})

        if self.state == "purchase":
            self.env["stock.picking"].search([("purchase_id", "=", self.id)]).action_cancel()

        state = self.state == "purchase" and "po_canceled" or "cancel"
        self.write({"reason": reason, "state": state})

    def button_po_canceled(self, reason):
        self.update({"state": "po_canceled", "reason": reason})
        prl = self.env["purchase.request.line"].search([("purchase_lines", "in", self.order_line.ids)])
        prl.state = "approved"
        prl.purchase_order_code = ""

        ppc = self.env["purchase.price.comparison"].search([("order_id", "=", self.id)], limit=1)
        ppc.po_ids.state = "po_canceled"
        ppc.update({"state": "po_canceled", "reason": reason})