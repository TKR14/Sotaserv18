# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.misc import get_lang


class DLMCommonReport(models.TransientModel):
    _name = "dlm.common.report"
    _description = "DLM Common Report"

    site_id = fields.Many2one("building.site", string="Affaire", domain=[('state', '=', 'open')])
    date_from = fields.Date(string='Date Début')
    date_to = fields.Date(string='Date de fin')
    report_name = fields.Selection([('dlm_assign', 'Affectations Matériels'),
                                    ('dlm_trasport_schedule', 'Planning de Transport Logistique'),
                                    ('dlm_materials_worked_hours', 'Pointages Matériels'),], string='Rapport à imprimer', required=True, default='dlm_assign')

    def _build_contexts(self, data):
        result = {}
        result['site_id'] = data['form']['site_id'] or False
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['report_name'] = data['form']['report_name'] or False
        return result

    def _print_report(self, data):
        report_name = data['form']['report_name']
        if report_name == 'dlm_assign':
            return self.env.ref('building.action_report_dlmassign').report_action(self, data=data)
        if report_name == 'dlm_trasport_schedule':
            return self.env.ref('building.action_report_trasportschedule').report_action(self, data=data)
        if report_name == 'dlm_materials_worked_hours':
            return self.env.ref('building.action_report_materials_worked_hours').report_action(self, data=data)

    def check_report(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['site_id', 'date_from', 'date_to', 'report_name'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
        return self.with_context(discard_logo_check=True)._print_report(data)
