from odoo import models, _, api, fields
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

from lxml import etree


class StockPicking(models.Model):
    _inherit = "stock.picking"

    return_to_mg = fields.Boolean(default=False, readonly=True)
    is_invoiced = fields.Boolean(default=False)
    invoice_id = fields.Many2one("account.move", string="Facture")

    def fixe(self):
        all_stock_pickings = self.env["stock.picking"].search([("state", "=", "done"), ("is_invoiced", "=", True)])
        for rec in all_stock_pickings:
            if not rec.invoice_id:
                pickings = self.env["stock.picking"].search([("origin", "=", rec.origin), ("state", "=", "done"), ("is_invoiced", "=", True)])
                invoices = self.env["account.move"].search([("invoice_origin", "=", rec.origin), ("state", "!=", "cancel"), ("move_type_code", "=", "inv_reception_supply")])
                if len(invoices) == 1:
                    pickings.invoice_id = invoices.id

    def correct_quantities(self):
        stock_id = self
        stock_moves = self.env["stock.move"].search([("picking_id", "=", stock_id.id)])
        stock_move_lines = self.env["stock.move.line"].search([("picking_id", "=", stock_id.id)])

        stock_id.state = stock_moves.state = stock_move_lines.state = "assigned"
        self.env["purchase.order"].search([("name", "=", self.origin)], limit=1).sudo().return_to_mg = self.return_to_mg = False    

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self.picking_type_id.sequence_code == "INT" and self.location_dest_id.usage == "transit":
            code = self.location_dest_id.barcode[:3]
            new_destination_id = self.env["stock.location"].search([("barcode", "=", f"{code}-STOCK")], limit=1).id            
            self.location_dest_id = self.move_ids_without_package.location_dest_id = self.move_line_ids_without_package.location_dest_id = new_destination_id

        for picking in self:
            picking.write({"return_to_mg": False})

        if not self._check_immediate() and not self._check_backorder():
            if self.picking_type_id.sequence_code == "INT":
                self.move_ids_without_package.mapped("request_line_id").state = "transfer_done"
            else:
                self.purchase_id.sudo().button_done()

        self.purchase_id.sudo().button_done()
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        result = super(StockPicking, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        
        arch = etree.fromstring(result["arch"])
        if not self.env.context.get("outgoing_process") and not self.env.context.get("scrap_process") and not self.env.context.get("return_process") and not self.env.context.get("internal_transfer_process"):
            arch.set("create", "false")
        result["arch"] = etree.tostring(arch)
        if result.get("toolbar", False):
            result["toolbar"]["print"] = []
            if self.env.context.get('hide_actions'):
                result['toolbar']['action'] = []
        return result
    
    def action_generate_invoice(self):
        order_id = self.env["purchase.order"].search([("name", "=", self[0].origin)])
        invoice = order_id.action_create_invoice(self, reception=True, advance=sum(self.mapped("amount_advance_deduction")))
        order_id.button_done()
        self.sudo().write({"invoice_id": invoice.id, "is_invoiced": True, "certification_state": "invoiced"})