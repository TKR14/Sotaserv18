# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from datetime import datetime

def generate_code(sequence_number):
    """
    Generates a code with the prefix 'DDP', followed by the current year, month,
    and a sequence number.

    Args:
    sequence_number (int): The current sequence number.

    Returns:
    str: The generated code.
    """
    # Get the current year and month
    now = datetime.now()
    year = now.year
    month = f"{now.month:02d}"  # Format the month as a two-digit number with leading zeros
    
    # Format the sequence number, e.g., as a three-digit number with leading zeros
    sequence_str = f"{sequence_number:04d}"
    
    # Construct the final code
    code = f"DDP/{year}/{month}/{sequence_str}"
    
    return code

def get_next_sequence(env):
    """
    Fetches the next sequence number for a new purchase order based on the latest record.

    Args:
    env: Access to the Odoo environment (database and models).

    Returns:
    int: The next sequence number to be used.
    """
    # Get the current year and month
    now = datetime.now()
    year = now.year
    month = f"{now.month:02d}"  # Format the month as a two-digit number with leading zeros
    
    # Search for the latest purchase order with the pattern 'DDP/YEAR/MONTH/%'
    PurchaseOrder = env['purchase.order']
    pattern = f"DDP/{year}/{month}/%"
    latest_order = PurchaseOrder.search([('purchase_order_code', 'like', pattern)], order='id desc', limit=1)

    if not latest_order:
        # If no order is found, start the sequence at 1
        return 1

    # Extract the sequence number from the latest order purchase_order_code
    last_code = latest_order.purchase_order_code
    # Assuming the sequence is always the last 4 digits after the last '/'
    last_sequence = int(last_code.split('/')[-1])

    # Return the next sequence number
    return last_sequence + 1

class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    supplier_ids = fields.Many2many('res.partner', 'partner_request', 'partner_id', 'request_id', 'Fournisseurs', required=True, domain=[('supplier_rank', '>', 0)])
    supplier_id = fields.Many2one(
        comodel_name="res.partner",
        string="Supplier",
        required=False,
        domain=[("is_company", "=", True)],
        context={"res_partner_search_mode": "supplier", "default_is_company": True},
    )
    used_code = fields.Char()

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin, site_id, vehicle_id):
        list_data = []
        if not self.supplier_ids:
            raise UserError(_("Enter a supplier."))
        suppliers = self.supplier_ids

        is_multiple_suppliers = len(suppliers) > 1
        code = None

        if is_multiple_suppliers:
            sequence_number = get_next_sequence(self.env)
            code = generate_code(sequence_number)
        
        self.used_code = code

        for supplier in suppliers:
            data = {
                "origin": origin,
                "partner_id": supplier.id,
                "payment_term_id": supplier.property_supplier_payment_term_id.id,
                "fiscal_position_id": supplier.property_account_position_id
                and supplier.property_account_position_id.id
                or False,
                "responsible_for_cancellation": self.env.user.id,
                "picking_type_id": picking_type.id,
                "company_id": company.id,
                "group_id": group_id.id,
                "site_id" : site_id or False,
                "vehicle_id" : vehicle_id or False
            }

            if is_multiple_suppliers:
                data.update({
                    "purchase_order_code": code,
                    "is_po_multiple": True
                })

            list_data.append(data)
        return list_data


    def make_purchase_order(self):
        res = []
        purchase_obj = self.env["purchase.order"]
        po_line_obj = self.env["purchase.order.line"]
        pr_line_obj = self.env["purchase.request.line"]
        purchase = False

        active_id = self._context.get("active_id")
        active_model = self._context.get("active_model")
        request = self.env[active_model].browse(active_id)
        if active_model == "purchase.request.line":
            request = request.request_id

        site_id = request.site_id.id
        vehicle_id = request.vehicle_id.id
        po_datas = self._prepare_purchase_order(
            request.picking_type_id,
            request.group_id,
            request.company_id,
            request.origin,
            site_id,
            vehicle_id
        )
        purchases = purchase_obj.create(po_datas)

            # Look for any other PO line in the selected PO with same
            # product and UoM to sum quantities instead of creating a new
            # po line
        for purchase in purchases:
            for item in self.item_ids:
                line = item.line_id
                line.has_pr = True
                line.purchase_order_code = self.used_code
                if item.product_qty <= 0.0:
                    raise UserError(_("Enter a positive quantity."))
        # if self.purchase_order_id:
        #     purchases = self.purchase_order_id
        # if not purchase:
                domain = self._get_order_line_search_domain(purchase, item)
                available_po_lines = po_line_obj.search(domain)
                new_pr_line = True
                # If Unit of Measure is not set, update from wizard.
                if not line.product_uom_id:
                    line.product_uom_id = item.product_uom_id
                # Allocation UoM has to be the same as PR line UoM
                alloc_uom = line.product_uom_id
                wizard_uom = item.product_uom_id
                if available_po_lines and not item.keep_description:
                    new_pr_line = False
                    po_line = available_po_lines[0]
                    po_line.purchase_request_lines = [(4, line.id)]
                    po_line.move_dest_ids |= line.move_dest_ids
                    po_line_product_uom_qty = po_line.product_uom._compute_quantity(
                        po_line.product_uom_qty, alloc_uom
                    )
                    wizard_product_uom_qty = wizard_uom._compute_quantity(
                        item.product_qty, alloc_uom
                    )
                    all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
                    self.create_allocation(po_line, line, all_qty, alloc_uom)
                
                else:
                    po_line_data = self._prepare_purchase_order_line(purchase, item)
                    po_line_data["price_unit"] = 0
                    if item.keep_description:
                        po_line_data["name"] = item.name
                    po_line = po_line_obj.create(po_line_data)
                    po_line_product_uom_qty = po_line.product_uom._compute_quantity(
                        po_line.product_uom_qty, alloc_uom
                    )
                    wizard_product_uom_qty = wizard_uom._compute_quantity(
                        item.product_qty, alloc_uom
                    )
                    all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
                    self.create_allocation(po_line, line, all_qty, alloc_uom)

                # TODO: Check propagate_uom compatibility:
                new_qty = pr_line_obj._calc_new_qty(
                    line, po_line=po_line, new_pr_line=new_pr_line
                )
                po_line.product_qty = new_qty
                # po_line._onchange_quantity()
                # raise Exception(po_line, po_line.read())
                # The onchange quantity is altering the scheduled date of the PO
                # lines. We do not want that:
                date_required = item.line_id.date_required
                po_line.date_planned = datetime(
                    date_required.year, date_required.month, date_required.day
                )
                if item.product_id.type == 'service':
                    purchase.is_attachment = True

        if len(purchases) > 1:
            year = str(datetime.today().year)
            count = self.env["purchase.price.comparison"].search_count([("year", "=", year)])
            code = purchases.mapped("purchase_order_code")[0]

            new_comparison = self.env["purchase.price.comparison"].create({
                "name": f"{count + 1}/{year}",
                "date_comparison": datetime.today(),
                "purchase_order_code": code,
                "year": year,
            })

            purchases.update({
                "state": "compare_offers",
                "price_comparison_id": new_comparison.id,
            })
            purchases.mapped("order_line").update({
                "price_comparison_id": new_comparison.id,
            })

            return {
                "type": "ir.actions.act_window",
                "name": "Comparaison des demandes de prix",
                "res_model": "purchase.price.comparison",
                "view_mode": "form",
                "target": "current",
                "res_id": new_comparison.id,
            }

        new_purchase = purchases[0]
        return {
            "type": "ir.actions.act_window",
            "name": new_purchase.name,
            "res_model": "purchase.order",
            "view_mode": "form",
            "target": "current",
            "res_id": new_purchase.id,
        }