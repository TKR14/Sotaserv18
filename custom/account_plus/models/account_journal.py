from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    checkbook_ids = fields.One2many("account.journal.checkbook", "journal_id", string="Chéquiers")