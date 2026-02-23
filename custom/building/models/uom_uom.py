from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

from lxml import etree


class UomUom(models.Model):
    _inherit = "uom.uom"

    @api.constrains('name')
    def check_name(self):
        for uom_uom in self:
            uom_uom_id = self.env['uom.uom'].search([('name', '=', uom_uom.name),
                                                     ('id', '!=', uom_uom.id),
                                                     ('category_id', '=', uom_uom.category_id.id)])
            if uom_uom_id:
                raise ValidationError(_('Il existe deja une unité de mesure avec le même nom %s!', uom_uom.name))

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if not self.env.user.has_group("building.uom_uom_group_can_edit"):
            doc = etree.XML(res["arch"])
            doc.set("edit", "false")
            doc.set("create", "false")
            doc.set("delete", "false")
            res["arch"] = etree.tostring(doc, encoding="unicode")
        return res