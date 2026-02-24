from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

from lxml import etree
import json


class ApprovalChain(models.Model):
    _name = "approval.chain"
    _rec_name = "model_id"

    @api.depends("step_ids")
    def _compute_steps_count(self):
        for record in self:
            record.steps_count = len(record.step_ids)

    @api.depends("line_ids")
    def _compute_lines_count(self):
        for record in self:
            record.lines_count = len(record.line_ids)

    model_id = fields.Many2one("ir.model", string="Modèle")

    step_ids = fields.One2many("approval.chain.step", "parent_id", string="Étapes")
    steps_count = fields.Integer("Nombre d'étapes", compute="_compute_steps_count")

    line_ids = fields.One2many("approval.chain.line", "parent_id", string="Lignes")
    lines_count = fields.Integer("Nombre des lignes", compute="_compute_lines_count")

    @api.model
    def create(self, values):
        result = super(ApprovalChain, self).create(values)
        return result

    def write(self, values):
        return super(ApprovalChain, self).write(values)

    def action_get_lines(self):
        context = {
            "default_parent_id": self.id,
            "default_steps_count": self.steps_count,
        }

        for i in range(1, 7):
            if i <= self.steps_count:
                step = self.step_ids.filtered(lambda s: s.order == i)
                context[f"step_{i}"] = step.name
                context[f"step_{i}_group"] = step.group_id.id

        # search_view = self.env.ref("purchase_igaser.approval_chain_line_view_search")
        # arch = etree.XML("""
        #     <search>
        #         <group expand="0" string="Group By">
        #             <filter name="step_1" context="{'group_by': 'step_1'}"/>
        #             <filter name="step_2" context="{'group_by': 'step_2'}"/>
        #             <filter name="step_3" context="{'group_by': 'step_3'}"/>
        #             <filter name="step_4" context="{'group_by': 'step_4'}"/>
        #             <filter name="step_5" context="{'group_by': 'step_5'}"/>
        #             <filter name="step_6" context="{'group_by': 'step_6'}"/>
        #         </group>
        #     </search>
        # """)

        # for filter in arch.xpath("//filter"):
        #     filter_name = filter.get("name")
        #     if filter_name in context.keys():
        #         filter.set("string", context.get(filter_name))
        #     elif filter_name in ["step_1", "step_2", "step_3", "step_4", "step_5"]:
        #         filter.getparent().remove(filter)

        # search_view["arch"] = etree.tostring(arch)

        return {
            "name": "Lignes",
            "type": "ir.actions.act_window",
            "res_model": "approval.chain.line",
            "view_mode": "list,search",
            "domain": [("parent_id", "=", self.id)],
            "context": context,
            "target": "current",
            # "search_view_id": search_view.id,
        }

    def action_get_steps(self):
        return {
            "name": "Étapes",
            "type": "ir.actions.act_window",
            "res_model": "approval.chain.step",
            "view_mode": "list",
            "domain": [("parent_id", "=", self.id)],
            "context": {
                "default_parent_id": self.id,
            },
            "target": "current",
        }


class ApprovalChainStep(models.Model):
    _name = "approval.chain.step"
    _order = "order"

    parent_id = fields.Many2one("approval.chain", string="Chaîne parente")
    order = fields.Integer("#", default=1)
    name = fields.Char("Nom")
    group_id = fields.Many2one("res.groups", string="Action")

    @api.onchange("parent_id")
    def _depends_parent_id_step_ids(self):
        if self.parent_id.model_id:
            already_selected = self.parent_id.step_ids.mapped("group_id").ids

            return {
                "domain": {
                    "group_id": [("model_id", "=", self.parent_id.model_id.id), ("type", "=", "button"), ("id", "not in", already_selected)]
                }
            }

    @api.model
    def default_get(self, fields):
        result = super(ApprovalChainStep, self).default_get(fields)

        last_step = self.search([("parent_id", "=", self._context.get("default_parent_id"))], order="id desc", limit=1)
        if last_step:
            result["order"] = last_step.order + 1

        return result


STEPS = ["step_1", "step_2", "step_3", "step_4", "step_5", "step_6"]
class ApprovalChainLine(models.Model):
    _name = "approval.chain.line"

    @api.model
    def fields_get(self, fields=None):
        result = super(ApprovalChainLine, self).fields_get(fields)

        for field in STEPS:
            enabled = False
            if field in self._context.keys():
                result[field]["string"] = self._context.get(field)
                enabled = True

            result[field]["required"] = result[field]["searchable"] = result[field]["sortable"] = enabled

        return result

    @api.model
    def default_get(self, fields):
        result = super(ApprovalChainLine, self).default_get(fields)
        last_line = self.search([("parent_id", "=", self._context.get("default_parent_id"))], order="id desc", limit=1)
        for field in STEPS:
            result[field] = last_line[field].id or None

        return result

    def _onsave(self, values, id):
        for field in values.keys():
            if values[field]:
                parent = self.env["approval.chain"].browse(self._context.get("default_parent_id"))
                group = self.env["res.groups"].browse(self._context.get(f"{field}_group"))
                user = self.env["res.users"].browse(values[field])
                group.users = parent.line_ids.filtered(lambda line: line.id != id).mapped(field) + user

    @api.model
    def create(self, values):
        result = super(ApprovalChainLine, self).create(values)
        self._onsave(values, result["id"])
        return result
        
    def write(self, values):
        self._onsave(values, self.id)
        return super(ApprovalChainLine, self).write(values)
    
    def unlink(self):
        for step in STEPS:
            parent = self.env["approval.chain"].browse(self._context.get("default_parent_id"))
            group = self.env["res.groups"].browse(self._context.get(f"{step}_group"))
            group.users = parent.line_ids.filtered(lambda line: line.id not in self.ids).mapped(step)

        return super(ApprovalChainLine, self).unlink()

    parent_id = fields.Many2one("approval.chain", string="Chaîne parente")
    step_1 = fields.Many2one("res.users", string="Étape 1")
    step_2 = fields.Many2one("res.users", string="Étape 2")
    step_3 = fields.Many2one("res.users", string="Étape 3")
    step_4 = fields.Many2one("res.users", string="Étape 4")
    step_5 = fields.Many2one("res.users", string="Étape 5")
    step_6 = fields.Many2one("res.users", string="Étape 6")