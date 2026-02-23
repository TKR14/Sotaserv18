# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError
from datetime import datetime

class ReportDlmAssign(models.AbstractModel):
    _name = 'report.building.report_dlmassign'
    _description = 'DLM Assign Report'

    def _get_list_sites(self, site, start_date, end_date):
        site_ids = []
        sites = None
        if not site:
            domain = [('state', '=', 'open'), ('type_assignment', '=', 'equipment')]
            if start_date:
                domain.append(('date_start', '>=', start_date))
            if end_date:
                domain.append(('date_end', '<=', end_date))
            building_assignment_lines = self.env['building.assignment.line'].search(domain)
            if building_assignment_lines:
                for bal in building_assignment_lines:
                    if bal.site_id.id not in site_ids:
                        site_ids.append(bal.site_id.id)
                sites = self.env['building.site'].browse(site_ids)
        else:
            sites = site
        return sites

    def _get_types_assignment(self, start_date, end_date, site_id):
        types_assignment = []
        domain = [('site_id', '=', site_id), ('state', '=', 'open'), ('type_assignment', '=', 'equipment')]
        if start_date:
            domain.append(('date_start', '>=', start_date))
        if end_date:
            domain.append(('date_end', '<=', end_date))
        building_assignment_lines = self.env['building.assignment.line'].search(domain)
        if building_assignment_lines:
            for bal in building_assignment_lines:
                if bal.categ_assignment not in types_assignment:
                    types_assignment.append(bal.categ_assignment)
        types_assignment.sort()
        return types_assignment

    def _get_materiels(self, start_date, end_date, site_id, categ_assignment):
        domain = [('site_id', '=', site_id), ('state', '=', 'open'), ('type_assignment', '=', 'equipment'), ('categ_assignment', '=', categ_assignment)]
        if start_date:
            domain.append(('date_start', '>=', start_date))
        if end_date:
            domain.append(('date_end', '<=', end_date))
        building_assignment_lines = self.env['building.assignment.line'].search(domain)
        return building_assignment_lines

    def _get_value_categ_assignment_selection(self, categ_assignment):
        return dict(self.env['building.assignment.line']._fields['categ_assignment'].selection).get(categ_assignment)

    @api.model
    def _get_report_values(self, docids, data=None):
        site_id = None
        if data['form']['site_id']:
            site_id = data['form']['site_id'][0]
        start_date = data['form']['date_from']
        end_date = data['form']['date_to']
        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        site = None
        if site_id:
            site = self.env['building.site'].browse(site_id)
        
        return {
            'doc_model': self.env['building.assignment.line'],
            'time': time,
            'start_date': start_date,
            'end_date': end_date,
            'get_list_sites': self._get_list_sites(site, start_date, end_date),
            'get_types_assignment': self._get_types_assignment,
            'get_value_categ_assignment_selection': self._get_value_categ_assignment_selection,
            'get_materiels': self._get_materiels
        }
