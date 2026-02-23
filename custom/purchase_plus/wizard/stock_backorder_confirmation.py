from odoo import _, api, fields, models


def _substrat_quantity(a, b):
    result = a - b
    if result > 0:
        return {"is_full": True, "quantity": result}
    else:
        return {"is_full": False, "quantity": -result}
  
def _generate_html_body(product, old_quantity, new_quantity):
    html_body = f"""
        <strong>La quantité a diminué en raison d'un reliquat:</strong>
        <ul>
            <li>{product} : {old_quantity} <span class="fa fa-long-arrow-right"/> {new_quantity}</li>
        </ul>
    """

    return html_body

class StockBackorderConfirmation(models.TransientModel):
    _inherit = "stock.backorder.confirmation"

    def show_success_notification(self, message):
        return {
            'type': 'ir.actions.act_multi',
            'actions': [
                {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Succès"),
                        'message': message,
                        'type': 'success',
                        'sticky': False,
                    }
                },
                {'type': 'ir.actions.act_window_close'}
            ]
        }

    def process(self):
        pickings_to_do = self.env['stock.picking']
        pickings_not_to_do = self.env['stock.picking']

        for line in self.backorder_confirmation_line_ids:
            if line.to_backorder is True:
                pickings_to_do |= line.picking_id
            else:
                pickings_not_to_do |= line.picking_id

        picking_id = self.env.context.get('button_validate_picking_ids')
        picking = self.env['stock.picking'].browse(picking_id) if picking_id else False

        if (
            not self.env.context.get('skip_process_confirmation')
            and picking
            and picking.create_vehicle
        ):
            return {
                'name': "Assistance de confirmation",
                'type': 'ir.actions.act_window',
                'res_model': 'stock.backorder.confirmation.message',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_backorder_confirmation_id': self.id,
                }
            }

        if picking:
            picking = picking.with_context(skip_backorder=True)
            if pickings_not_to_do:
                self._check_less_quantities_than_expected(pickings_not_to_do)
                picking = picking.with_context(
                    picking_ids_not_to_backorder=pickings_not_to_do.ids
                )
            result = picking.button_validate()
            message = picking.action_create_vehicles()

            if message:
                return self.show_success_notification(message)
            return result
        
        if self.env.context.get('pickings_to_detach'):
            self.env['stock.picking'].browse(self.env.context['pickings_to_detach']).batch_id = False
        return True
    
    def open_process_cancel_backorder_wizard(self):
        picking = self.pick_ids[0]
        if (
            not self.env.context.get('skip_process_confirmation')
            and picking
            and picking.create_vehicle
        ):
            return {
                'name': "Assistance de confirmation",
                'type': 'ir.actions.act_window',
                'res_model': 'stock.backorder.confirmation.message',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_backorder_confirmation_id': self.id,
                    'process_cancel_backorder': True,
                }
            }
        else:
            return self.process_cancel_backorder()

    def process_cancel_backorder(self):
        res = super(StockBackorderConfirmation, self).process_cancel_backorder()

        purchase_order = self.pick_ids[0].purchase_id
        products_ids = purchase_order.order_line.mapped("product_id")

        stock_picking_ids = self.env["stock.picking"].search([("purchase_id", "=", purchase_order.id)]).ids
        stock_moves = self.env["stock.move"].search([("picking_id", "in", stock_picking_ids)])

        for product_id in products_ids:
            order_line = purchase_order.order_line.filtered(lambda line : line.product_id == product_id)
            ordered_quantity = sum(order_line.mapped("product_qty"))
            received_quantity = sum(stock_moves.filtered(lambda line : line.product_id == product_id and line.state == "done").mapped("quantity_done"))

            if received_quantity < ordered_quantity:
                balance_quantity = ordered_quantity - received_quantity
                purchase_request_lines = order_line.purchase_request_lines.sorted(key=lambda line : line.id, reverse=True)
                                        
                for purchase_request_line in purchase_request_lines:
                    balance_quantity = _substrat_quantity(purchase_request_line.product_qty, balance_quantity)
                    new_quantity = balance_quantity["quantity"] if balance_quantity["is_full"] else 0
            
                    if purchase_request_line.product_qty != new_quantity:
                        body = _generate_html_body(purchase_request_line.product_id.name, purchase_request_line.product_qty, new_quantity)
                        purchase_request_line.update({"product_qty": new_quantity})
                        purchase_request_line.request_id.message_post(body=body)

                    if balance_quantity["is_full"]:
                        break

                    balance_quantity = balance_quantity["quantity"]

            for line in order_line.purchase_request_lines:
                line.state = "received"

        if self.pick_ids[0].picking_type_id.sequence_code == "INT":
            self.pick_ids[0].move_ids_without_package.mapped("request_line_id").state = "transfer_done"
        else:
            purchase_order.sudo().button_done()

        message = self.pick_ids[0].action_create_vehicles()
        if message:
            return self.show_success_notification(message)
        return res