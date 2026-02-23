from odoo import fields, models, api
from odoo.exceptions import UserError


class PurchaseVerification(models.TransientModel):
    _name = "purchase.verification"
    
    title = fields.Html(string="Titre", default="<h3 style='text-align: center;'>Vérification d'Achat</h3>")
    line_ids = fields.One2many("purchase.verification.line", "purchase_verification_id", "Lignes")

    @api.model
    def _prepare_item(self, line):
      source_id = self.env["stock.location"].search([("barcode", "=", "000-STOCK")], limit=1).id
      stock_quants = self.env["stock.quant"].search([("location_id", "=", source_id), ("product_id", "=", line.product_id.id)])
      sum_quantity = sum(stock_quants.mapped("quantity"))

      return {
        "line_id": line.id,
        "request_id": line.request_id.id,
        "product_id": line.product_id.id,
        "product_qty": line.pending_qty_to_receive,
        "available_qty": sum_quantity,
        "product_uom_id": line.product_uom_id.id,
      }

    @api.model
    def _check_valid_request_line(self, request_lines):      
      non_approved_lines = any(line.state != 'approved' for line in request_lines)
      if non_approved_lines:
          raise UserError("Vous devez sélectionner uniquement les lignes ayant un statut approuvé.")
      

    @api.model
    def get_items(self, request_line_ids):
        request_line_obj = self.env["purchase.request.line"]
        items = []
        request_lines = request_line_obj.browse(request_line_ids)
        self._check_valid_request_line(request_lines)
        for line in request_lines:
            items.append([0, 0, self._prepare_item(line)])
        return items

    @api.model
    def default_get(self, fields):
      res = super().default_get(fields)
      request_line_ids = self.env.context["active_ids"]

      if not request_line_ids:
        return res
      
      res["line_ids"] = self.get_items(request_line_ids)

      return res
    
    def validate(self):
      for line in self.line_ids:
        line.line_id.state = line.purchase_type
        line.line_id.chargeby_id = self.env.user.id