from odoo import _, api, fields, models
from odoo.exceptions import UserError

class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"
    _description = "Purchase Request Line Make Purchase Order"

    @api.model
    def _check_valid_request_line(self, request_line_ids):
        res = super()._check_valid_request_line(request_line_ids)

        request_line_obj = self.env["purchase.request.line"]
        request_lines = request_line_obj.browse(request_line_ids).filtered(lambda line: not (line.state == "purchase_validated" and line.has_pr))
        
        non_purchase_validated_lines = any(line.state != 'purchase_validated' for line in request_lines)
        if non_purchase_validated_lines:
            raise UserError("Vous devez sélectionner uniquement les lignes ayant un statut Achat Validé.")
        
        category_types = set(line.category_type for line in request_lines)
        if 'other' in category_types and len(category_types) > 1:
            raise UserError("Vous ne pouvez pas mélanger le type de catégorie d'article 'Autre' avec d'autres types.")

        first_site_id = request_lines[0].site_id.id
        all_same_site_id = all(line.site_id.id == first_site_id for line in request_lines)
        if not all_same_site_id:
            raise UserError("Vous devez sélectionner des lignes de la même affaire.")

        first_product_category_id = request_lines[0].product_id.type
        all_same_product_category = all(line.product_id.type == first_product_category_id for line in request_lines)
        if not all_same_product_category:
            raise UserError("Vous devez sélectionner des lignes avec le même type d'article.")

    @api.model
    def get_items(self, request_line_ids):
        request_line_obj = self.env["purchase.request.line"]
        items = []
        request_lines = request_line_obj.browse(request_line_ids).filtered(lambda line: not line.has_pr)        
        self._check_valid_request_line(request_line_ids)
        self.check_group(request_lines)
        for line in request_lines:
            items.append([0, 0, self._prepare_item(line)])
        return items