from odoo import models, fields

from datetime import datetime
from dateutil.relativedelta import relativedelta


class TimeMachine(models.Model):
    _name = "time.machine"

    def name_get(self):
        return [(record.id, "Time Machine") for record in self]
        return [(record.id, record.today_is.strftime("%d/%m/%Y")) for record in self]

    today_is = fields.Date("Aujourd'hui", default=lambda _: datetime.today())

    def date(self):
        return self.search([], limit=1).today_is

    def today(self):
        self.today_is = datetime.today()

    def tomorrow(self):
        self.today_is += relativedelta(days=+1)

    def yesterday(self):
        self.today_is += relativedelta(days=-1)
    
    def next_week(self):
        self.today_is += relativedelta(weeks=+1)
    
    def last_week(self):    
        self.today_is += relativedelta(weeks=-1)
    
    def next_month(self):
        self.today_is += relativedelta(months=+1)
    
    def last_month(self):
        self.today_is += relativedelta(months=-1)
    
    def action_open_portal(self):
        time_machine = self.search([], limit=1)

        return {
            "name": "Time Portal",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "time.machine",
            "res_id": time_machine.id,
        }

    def big_bang(self):
        self.today()

        requests = self.env["hr.assignment.request"].search([])
        for request in requests:
            request.button_draft()
            request.button_validated()
            request.button_approved()

        self.env["hr.assignment"].search([]).unlink()
        self.env["hr.employee"].search([("is_assigned", "=", True)]).is_assigned = False