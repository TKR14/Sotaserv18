# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError
from datetime import datetime

class ReportTrasportSchedule(models.AbstractModel):
    _name = 'report.building.report_trasportschedule'
    _description = 'DLM Assign Report'

    def _get_lines(self, start_date, end_date):
        site_ids = []
        sites = None
        domain = []
        if start_date:
            domain.append(('start_date', '>=', start_date))
        if end_date:
            domain.append(('end_date', '<=', end_date))
        trasport_schedules = self.env['trasport.schedule'].search(domain)
        print ('trasport_schedules', trasport_schedules)
        return trasport_schedules
        
    @api.model
    def _get_report_values(self, docids, data=None):
        start_date = data['form']['date_from']
        end_date = data['form']['date_to']
        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        return {
            'doc_model': self.env['trasport.schedule'],
            'time': time,
            'start_date': start_date,
            'end_date': end_date,
            'lines': self._get_lines(start_date, end_date),
        }
