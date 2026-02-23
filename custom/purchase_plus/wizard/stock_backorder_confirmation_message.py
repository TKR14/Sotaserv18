from odoo import models, fields


class StockBackorderConfirmationMessage(models.TransientModel):
    _name = 'stock.backorder.confirmation.message'
    _description = 'Backorder Confirmation Message'

    backorder_confirmation_id = fields.Many2one('stock.backorder.confirmation')
    immediate_transfer_id = fields.Many2one('stock.immediate.transfer')

    def action_confirm(self):
        backorder = self.backorder_confirmation_id.with_context(skip_process_confirmation=True)
        immediate_transfer = self.immediate_transfer_id.with_context(skip_immediate_process_confirmation=True)
        
        if self.env.context.get('process_cancel_backorder'):
            return backorder.process_cancel_backorder()
        elif self.env.context.get('immediate_process'):
            return immediate_transfer.process()
        else:
            return backorder.process()
