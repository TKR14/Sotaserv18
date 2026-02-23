from odoo import models, _


class StockImmediateTransfer(models.TransientModel):
    _inherit = "stock.immediate.transfer"

    def open_process_wizard(self):
        picking = self.pick_ids[0]
        if (
            not self.env.context.get('skip_immediate_process_confirmation')
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
                    'default_immediate_transfer_id': self.id,
                    'immediate_process': True,
                }
            }
        else:
            return self.process()

    def process(self):
        res = super(StockImmediateTransfer, self).process()        
        picking = self.pick_ids[0]
        if picking[0].picking_type_id.sequence_code == "INT":
            self.pick_ids[0].move_ids_without_package.mapped("request_line_id").state = "transfer_done"
        else:
            picking.purchase_id.sudo().button_done()
            message = picking.action_create_vehicles()
            if message:
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
        return res