# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError
from datetime import datetime

class ReportMaterialsWorkedHours(models.AbstractModel):
    _name = 'report.building.report_materials_worked_hours'
    _description = 'DLM Assign Report'

    def _get_list_vehicle(self, start_date, end_date, site_id):
        vehicles = []
        vehicle_ids = []
        domain = []
        if site_id:
            domain.append(('site_id', '=', site_id))
        if start_date:
            domain.append(('worked_date', '>=', start_date))
        if end_date:
            domain.append(('worked_date', '<=', end_date))
        materials_worked_hours = self.env['materials.worked.hours'].search(domain)
        if materials_worked_hours:
            for mwh in materials_worked_hours:
                if mwh.vehicle_id.id not in vehicle_ids:
                    vehicle_ids.append(mwh.vehicle_id.id)
                    vehicles.append(mwh.vehicle_id)
        print ('vihiclesvihicles', vehicles)
        return vehicles

    def _get_lines(self, start_date, end_date, vehicle_id):
        domain = [('vehicle_id', '=', vehicle_id)]
        if start_date:
            domain.append(('worked_date', '>=', start_date))
        if end_date:
            domain.append(('worked_date', '<=', end_date))
        materials_worked_hours = self.env['materials.worked.hours'].search(domain)
        return materials_worked_hours
        
    @api.model
    def _get_report_values(self, docids, data=None):
        site_id = data['form']['site_id']
        start_date = data['form']['date_from']
        end_date = data['form']['date_to']
        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        return {
            'doc_model': self.env['materials.worked.hours'],
            'time': time,
            'start_date': start_date,
            'end_date': end_date,
            'list_vehicle': self._get_list_vehicle(start_date, end_date, site_id),
            'lines': self._get_lines,
        }
