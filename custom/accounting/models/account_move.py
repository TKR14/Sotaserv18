from odoo import models, fields

class account_move(models.Model):
    _inherit = 'account.move'
    reference = fields.Text(string="Réference")
    invoice_object = fields.Char(string="Objet")
    client_to_pay_id = fields.Many2one('res.partner', string='Client à payer', domain="[('customer_rank', '>', 0)]",related="site_id.client_to_pay")
    can_be_returned = fields.Boolean('Peut être retourné', compute="_compute_can_be_returned")
    
    def prev_fac(self, fac_id, partner_id):
      return self.search([('id', '<', fac_id), ('partner_id.id', '=', partner_id.id)])

    def amount_in_word(self, amount):
        word_num = str(self.currency_id.amount_to_text(amount))
        return word_num

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #   result = super(account_move, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
    #   doc = etree.XML(result['arch'])

    #   if view_type == 'form':
    #     for node in doc.xpath("//field"):
    #       domain = [('id', '!=', False)]
    #       if node.attrib.get('modifiers') and node.attrib.get('name') != 'invoice_date' and node.attrib.get('name') != 'invoice_payment_term_id'and node.attrib.get('name') != 'invoice_date_due' and node.attrib.get('name') != 'name' and node.attrib.get('name') != 'invoice_object':
    #           attr = json.loads(node.attrib.get('modifiers'))
    #           if attr.get('readonly'):
    #             value_readonly = attr.get('readonly')
    #             if str(attr.get('readonly')) != "True":
    #               value_readonly.insert(0, "|")
    #               domain = value_readonly + domain
    #           attr['readonly'] = domain
    #           node.set('modifiers', json.dumps(attr))
    #   result['arch'] = etree.tostring(doc)
    #   return result
    
    def _compute_can_be_returned(self):
      next_attachments = self.env['building.attachment'].search([('create_date', '>=', self.create_date), ('site_id.id', '=', self.site_id.id)])
      if self.inv_type == 'inv_attachment' and self.state != "posted" and self.payment_state != 'paid' and not next_attachments:
        self.can_be_returned = True
      else:
        self.can_be_returned = False

    def return_account_action(self):
      self.attachment_id.state = 'customer_validated'
      self.button_cancel()
      self.unlink()

      action_id = self.env.ref('account.action_move_out_invoice_type').read()[0]
      action_id['target'] = 'main'

      return action_id
    
    def prev_fac(self, fac_id, partner_id):
      return self.search([('id', '<', fac_id), ('partner_id.id', '=', partner_id.id)])

    def amount_in_word(self, amount):
        word_num = str(self.currency_id.amount_to_text(amount))
        return word_num
      
    def get_invoice_statement_lines(self):
      lines = []

      for line in self.invoice_line_enter_ids:
        if line.price_subtotal != 0 or line.display_type:
          lines.append(line)

      return lines