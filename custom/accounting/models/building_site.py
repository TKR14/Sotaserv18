from odoo import models, fields

class building_site(models.Model):
    _inherit = 'building.site'

    reference = fields.Text(string="Réference")
    client_to_pay = fields.Many2one('res.partner', string='Client à payer', domain="[('customer_rank', '>', 0)]")
    contract_number = fields.Char(string='Contrat N°')
    exemption_certificate_ref = fields.Text(string="Attestation d'exonération")
    is_tax_exempt = fields.Boolean('Affaire exonéré de la TVA?', compute="_compute_is_tax_exempt")

    def _compute_is_tax_exempt(self):
      BPs = self.env['building.order'].search([('site_id', '=', self.id)])
      is_exempt = False

      if BPs:
        for bp in BPs:
          if bp.tax_id.amount == 0:
            is_exempt = True
            break
      
      self.is_tax_exempt = is_exempt