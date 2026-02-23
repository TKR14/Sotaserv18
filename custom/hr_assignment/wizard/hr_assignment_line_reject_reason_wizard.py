from odoo import api, fields, models
from odoo.exceptions import UserError


class HrAssignmentLineRejectReasonWizard(models.TransientModel):
    _name = "hr.assignment.line.reject.reason.wizard"
    _description = "HR Assignment Line Reject Reason Wizard"

    reason = fields.Text(string="Motif", required=True)
    assignment_line_ids = fields.Many2many(
        "hr.assignment.line", string="Assignment Lines", required=True
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            res["assignment_line_ids"] = [(6, 0, active_ids)]
        return res

    def action_confirm_rejection(self):
        self.assignment_line_ids.write({
            "state": "rejected",
            "rejection_reason": self.reason,
        })

