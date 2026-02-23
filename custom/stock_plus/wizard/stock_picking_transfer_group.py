from odoo import models, fields, api


class StockPickingTransferGroupReference(models.TransientModel):
    _name = "stock.picking.transfer.group.reference"

    name = fields.Char("Référence")
    site_id = fields.Many2one("building.site", string="Affaire")


class StockPickingTransferGroup(models.TransientModel):
    _name = "stock.picking.transfer.group"

    add_to_group = fields.Boolean("Ajouter à un groupe", default=False)
    reference_id = fields.Many2one("stock.picking.transfer.group.reference", string="Référence")
    picking_ids = fields.Many2many("stock.picking", string="Transferts")
    site_id = fields.Many2one("building.site", string="Affaire")
    date = fields.Date("Date")
    reference = fields.Char("Référence")

    @api.onchange("add_to_group")
    def _onchange_add_to_group(self):
        self.date = self.reference = self.reference_id = False

    @api.onchange("site_id", "date")
    def _onchange_reference(self):
        if self.add_to_group:
            domain = [("site_id", "=", self.site_id.id)]
            if self.date:
                date = self.date.strftime("%y/%m/%d")
                domain.append(("name", "ilike", f"%{date}%"))
            return {
                "domain": {
                    "reference_id": domain
                }
            }
        elif self.date:
            reference = f"{self.site_id.code}/{self.date.strftime('%y/%m/%d')}"
            count = self.env["stock.picking"].search([("transfer_group_reference", "ilike", f"{reference}%")])
            count = len(set(count.mapped("transfer_group_reference"))) + 1
            self.reference = f"{reference}/{count}" 

    def button_regroup(self):
        if self.add_to_group:
            reference = self.reference_id.name
        else:
            reference = self.reference
        self.picking_ids.update({"transfer_group_reference": reference})