from odoo import models


class Blank(models.Model):
    _name = "blank"

    def blank(self, group):
        return {
            "name": group,
            "type": "ir.actions.act_window",
            "res_model": "blank",
            "view_mode": "list",
            "help": """
<h1 style="color: #000;">Walo!</h1>
<p style="font-weight: normal;">Vous n'avez aucun droit pour le moment,<br/>contactez votre administration.</p>""",
            "context": {
                "create": False,
                "delete": False,
                "edit": False,
            },
            "target": "current",
        }