from odoo import models, _, api, fields
from odoo.exceptions import UserError
from lxml import etree

from collections import Counter

PURCHASE_REQUEST_LINE_STATE_MAPPING = { 
	"draft": "Brouillon",
	"validated": "Validée",
	"approved": "Approuvée",
	"purchase_validated": "Achat Validé",
	"price_request_established": "Demande de Prix Établie",
	"order_established": "Commande Établie",
	"receiving": "Réception en Cours",
	"received": "Réception Faite",
	"no_reception": "Pas de Réception",
	"transfer_validated": "Transfert Validé",
	"transfer_established": "Transfert Établi",
	"transfer_done": "Transfert Clôturé",
	"invoiced": "Facture Établie",
	"invoice_paid": "Facture Payée",
	"closed": "Clôturée",
	"rejected": "Rejetée"
}

class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    reason = fields.Char(string="Motif", tracking=True)
    purchase_order_code = fields.Char("Demande de prix")
    chargeby_id = fields.Many2one("res.users", string="En charge par")
    state_id = fields.Many2one('purchase.request.line.state', string='Statut', compute="_compute_state_id", store=True)
    state_name = fields.Char(related="state_id.name", store=True)
    rejected_by_buyer = fields.Boolean(default=False)

    def button_reset_to_approved(self):
        for line in self:
            if line.state != 'transfer_validated':
                raise UserError("Vous devez sélectionner uniquement les lignes ayant un statut 'Transfert Validé'.")
            line.state = 'approved'

    def _action_note(self, state):
        return {
            "name": "Motif du refus",
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "view_mode": "form",
            "res_id": self.id,
            "views": [(self.env.ref("purchase_igaser.purchase_request_view_form_note").id, "form")],
            "target": "new",
            "context": {f"{state}": True},
        }
    
    def button_reject(self):
        return self._action_note("rejected")
    
    def button_note(self):
        return self._action_note("draft")

    def open_cancel_reason_wizard(self):
        if any(state != "approved" for state in self.mapped("state")):
            raise UserError("Seules les lignes Approuvées peuvent être annulées.")
        return {
            "name": "Assistant d'annulation",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cancellation.reason',
            'target': 'new',
        }

    def cancel_prl_line(self, reason=None):
        self.update({"state": "rejected", "rejected_by_buyer": True, "reason": reason})
        for line in self:
            quantity = f"{line.product_qty:,.2f}".replace(',', ' ').replace('.', ',')
            body = f"""
                <ul>
                    <li>Ligne annulée: {line.product_id.name} {quantity} {line.product_uom_id.name}</li>
                    <li>Motif d'annulation: {reason}</li>
                <ul/>
            """
            line.request_id._check_cancel()
            line.request_id.message_post(body=body)

    def show_reason(self):
        # raise UserError(f"Motif: {self.reason}")

        return {
            "name": "Motif de rejet",
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            "view_id": self.env.ref('purchase_plus.reason_form_view').id,
            'res_model': 'purchase.request.line',
            'target': 'new',
        }
    
    def requester_cancel(self):
        self.update({"state": "canceled"})

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
      res = super(PurchaseRequestLine, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
      if toolbar:
        actions_in_toolbar = res['toolbar'].get('action')
        if actions_in_toolbar:
          if (not self.env.user.has_group('purchase_request.group_purchase_request_manager') and not self.env.user.has_group('purchase_request.group_purchase_request_user')) or self.env.context.get("hide_create_rfq_action"):
            res['toolbar']['action'] = []

      arch = etree.fromstring(res["arch"])
      arch.set("delete", "false")
      res["arch"] = etree.tostring(arch)

      return res

    def button_transfer_wizard(self):
        states = list(set(self.mapped("state")))
        if len(states) != 1 or states[0] != "transfer_validated":
            raise UserError('Vous pouvez transférer uniquement les lignes en "Transfert Validé".')

        source_id = self.env["stock.location"].search([("barcode", "=", "000-STOCK")], limit=1).id
        def _line_values(line):
            stock_quants = self.env["stock.quant"].search([("location_id", "=", source_id), ("product_id", "=", line.product_id.id)])
            sum_quantity = sum(stock_quants.mapped("quantity"))
            destination_id = line.request_id.site_id.warehouse_id.lot_stock_id.id
            return {
                "request_line_id": line.id,
                "product_id": line.product_id.id,
                "quantity": line.product_qty,
                "quantity_available": sum_quantity,
                "source_id": source_id,
                "destination_id": destination_id,
            }

        wizard = self.env["stock.picking.transfer"].create({})
        wizard.line_ids = self.env["stock.picking.transfer.line"].create([_line_values(line) for line in self])

        return {
            "name": "Transfert",
            "type": "ir.actions.act_window",
            "res_model": "stock.picking.transfer",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.depends("state")
    def _compute_state_id(self):
        for line in self:
            state_id = self.env["purchase.request.line.state"].search([("selection_id.value", "=", line.state)], limit=1)
            if state_id:
                line.state_id = state_id.id
            else:
                line.state_id = False

    def action_get_buyer_purchase_request_lines(self):
        return {
            "name": "Lignes de Demande d'Achat",
            "type": "ir.actions.act_window",
            "res_model": "purchase.request.line",
            "view_mode": "list",
            "search_view_id": (self.env.ref("purchase_igaser.purchase_request_line_view_search").id, "search"),
            "views": [(self.env.ref("purchase_igaser.purchase_request_line_view_tree").id, "list")],
            "domain": [
                "|",
                "|",
                "|",
                ("chargeby_id", "=", self.env.user.id),  # their lines
                ("product_id.categ_id.supervisor_ids", "=", self.env.user.id),  # what they supervise
                "&",  # primary buyers of
                ("product_id.categ_id.buyer_ids.user_id", "=", self.env.user.id),
                ("state", "=", "approved"),
                "&", "&",  # secondary buyers of
                ("product_id.categ_id.buyers_count", "=", 0),
                ("product_id.categ_id.secondary_buyer_ids", "=", self.env.user.id),
                ("state", "=", "approved")
            ],
            "context": {
                "search_default_group_state_id": 1,
                "search_default_approved": 1,
                "search_default_purchase_validated": 1,
                "search_default_order_established": 1,
                "search_default_transfer_validated": 1,
                "search_default_transfer_established": 1,
            },
        }

    @api.model
    def create(self, vals):
        if vals.get("has_pr"):
            vals["has_pr"] = False
        if vals.get("supplier_id"):
            vals["supplier_id"] = False        
        return super(PurchaseRequestLine, self).create(vals)