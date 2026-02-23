from odoo import _, api, fields, models
from odoo.exceptions import UserError


def _substrat_quantity(a, b):
  result = a - b
  
  if result > 0:
    return {"is_full": True, "quantity": result}
  else:
    return {"is_full": False, "quantity": -result}
  

def _generate_html_body(product, old_quantity, new_quantity):
  html_body = f"""
    <strong>La quantité a diminué en raison d'annulation de réception:</strong>
      <ul>
      <li>{product} : {old_quantity} <span class="fa fa-long-arrow-right"/> {new_quantity}</li>
      </ul>
  """

  return html_body

class StockPicking(models.Model):
    _inherit = "stock.picking"

    return_btn_visible = fields.Boolean(compute="_compute_return_btn_visible")
    is_returned = fields.Boolean(default=False)
    def _states(self):
        return [
            ("draft", "Brouillon"),
            ("waiting", "En attente d'une autre opération"),
            ("confirmed", "En attente"),
            ("assigned", "Envoyé"),
            ("done", "Clôturé"),
            ("cancel", "Annulé"),
        ]
    state = fields.Selection(_states)

    def button_print_outgoing(self):
        return self.env.ref("stock_plus.stock_picking_outgoing_report").report_action(self)

    @api.depends('move_ids_without_package.is_compliant')
    def _compute_return_btn_visible(self):
        for pick in self:
            return_btn_visible = False
            if pick.state == "done" and pick.is_compliant == "notcompliant" and self.is_returned == False:
                return_btn_visible = True
            pick.return_btn_visible = return_btn_visible

    def action_no_reception(self):
        self.state = "cancel"

        purchase_order = self.purchase_id
        products_ids = purchase_order.order_line.mapped("product_id")
        stock_picking_ids = self.env["stock.picking"].search([("purchase_id", "=", purchase_order.id)]).ids
        stock_moves = self.env["stock.move"].search([("picking_id", "in", stock_picking_ids)])

        if self.picking_type_id.sequence_code == "INT":
            stock_picking_ids = self.env["stock.picking"].search([("backorder_id", "=", self.id)])
            # Checks if this picking is a backorder of another
            if bool(self.backorder_id):
                self.move_ids_without_package.mapped("request_line_id").state = "transfer_done"
            else:
                self.move_ids_without_package.mapped("request_line_id").state = "approved"
        else:
            if len(stock_picking_ids) < 2:
                purchase_order.sudo().button_cancel("Pas de réception")
            if len(stock_picking_ids) > 1:
                purchase_order.sudo().button_done()

        # for product_id in products_ids:
        #     order_line = purchase_order.order_line.filtered(lambda line : line.product_id == product_id)
        #     ordered_quantity = sum(order_line.mapped("product_qty"))
        #     received_quantity = sum(stock_moves.filtered(lambda line : line.product_id == product_id and line.state == "done").mapped("quantity_done"))

        #     if received_quantity < ordered_quantity:
        #         balance_quantity = ordered_quantity - received_quantity
        #         purchase_request_lines = order_line.purchase_request_lines.sorted(key=lambda line : line.id, reverse=True)
                            
        #         for purchase_request_line in purchase_request_lines:
        #             balance_quantity = _substrat_quantity(purchase_request_line.product_qty, balance_quantity)
        #             new_quantity = balance_quantity["quantity"] if balance_quantity["is_full"] else 0
                    
        #             if purchase_request_line.product_qty != new_quantity:
        #                 body = _generate_html_body(purchase_request_line.product_id.name, purchase_request_line.product_qty, new_quantity)
        #                 purchase_request_line.update({"product_qty": new_quantity})
        #                 purchase_request_line.request_id.message_post(body=body)

        #             if balance_quantity["is_full"]:
        #                 break

        #             balance_quantity = balance_quantity["quantity"]

    def action_group_transfer(self):
        sites = list(set(self.mapped("site_id")))
        if len(sites) > 1:
            raise UserError("Merci de sélectionner des transferts du même affaire.")

        # states = list(set(self.mapped("state")))
        # if any(state != "assigned" for state in states):
        #     raise UserError("vous ne pouvez sélectionner que les transferts en statut Envoyé.")

        references = self.mapped("transfer_group_reference")
        imposter = any(bool(reference) for reference in references)
        if imposter:
            imposters = self.filtered(lambda picking: bool(picking.transfer_group_reference))
            message = "Les transferts suivants ont déjà une Référence Bon de Transfert définie:\n"
            for picking in imposters:
                message += f"\n\t• {picking.name}"
            raise UserError(message)

        reference_model = self.env["stock.picking.transfer.group.reference"]
        reference_model.search([]).unlink()
        references = self.env["stock.picking"].search([("transfer_group_reference", "!=", False), ("site_id", "=", sites[0].id)]).mapped("transfer_group_reference")
        references = list(set(references))
        reference_model.create([{"name": reference, "site_id": sites[0].id} for reference in sorted(references)])

        return {
            "name": "Groupement des Transferts",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "stock.picking.transfer.group",
            "context": {
                "default_picking_ids": self.ids,
                "default_site_id": sites[0].id,
            },
            "target": "new",
        }

    def button_print_transfer(self):
        if not self.transfer_group_reference:
            raise UserError("Veuillez d'abord ajouter une Référence Bon de Transfert.")
        
        action = self.env.ref("stock_plus.stock_picking_transfer_report")
        action.name = f"Bon de Transfert - {self.transfer_group_reference}"

        pickings = self.env["stock.picking"].search([("transfer_group_reference", "=", self.transfer_group_reference)])
        picking = pickings[0]
        line_ids = pickings.mapped("move_ids_without_package")
        product_ids = line_ids.mapped("product_id")
        lines_data = []
        for product in product_ids:
            lines = line_ids.filtered(lambda l: l.product_id.id == product.id)
            uom = lines[0].product_id.name
            total = sum(lines.mapped("product_uom_qty"))
            total = f"{total:,.2f}".replace(',', ' ').replace('.', ',')
            lines_data.append({"name": product.name, "quantity": total, "uom": uom})

        data = {
            "site": picking.site_id.name,
            "reference": picking.transfer_group_reference,
            "lines": lines_data,
        }
        return self.env.ref("stock_plus.stock_picking_transfer_report").report_action(self, data=data)