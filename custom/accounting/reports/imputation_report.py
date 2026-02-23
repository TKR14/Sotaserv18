# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError
from datetime import datetime

class ReportImputation(models.AbstractModel):
    _name = 'report.accounting.report_imputation'
    _description = 'Payroll Imputation'

    #Exeple comment repmlir une ligede table a adapter selon ton besoin
    def _lines(self, start_date, end_date):
        moves = self.env['account.move'].search([('date', '>=', start_date), ('date', '<=', end_date), ('state', '=', 'posted'), ('journal_id', '=', 9)])
        move_lines = self.env['account.move.line'].search([('move_id', 'in', moves.ids)])
        move_lines = sorted(move_lines, key=lambda move_line: move_line.name + move_line.site_id.name, reverse=False)
        return move_lines
    
    # def _lines(self, start_date, end_date):
    #     moves = self.env['account.move'].search([('date', '>=', start_date), ('date', '<=', end_date), ('state', '=', 'posted'), ('journal_id', '=', 9)])
    #     move_lines = self.env['account.move.line'].search([('move_id', 'in', moves.ids)])
    #     dict_result = {}
    #     move_lines = sorted(move_lines, key=lambda move_line: move_line.name + move_line.site_id.name, reverse=False)
    #     for mv_line in move_lines:
    #         if (mv_line.site_id.id, mv_line.account_id.id, mv_line.name) not in dict_result:
    #             dict_result[(mv_line.site_id.id, mv_line.account_id.id, mv_line.name)] = [0, 0]
    #         dict_result[(mv_line.site_id.id, mv_line.account_id.id, mv_line.name)][0] += mv_line.debit
    #         dict_result[(mv_line.site_id.id, mv_line.account_id.id, mv_line.name)][1] += mv_line.credit

        # return dict_result

    def _get_paie_values(self, compte, libelle):
        sal_rule = self.env['hr.salary.rule'].search(['|', '&', ('account_debit', '=', compte), ('account_credit', '=', compte), ('name', '=', libelle)])
        return sal_rule

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') :
            raise UserError(_("Form content is missing, this report cannot be printed."))
        start_date = data['form']['date_from']
        end_date = data['form']['date_to']
        start_date = datetime.strptime(start_date, "%Y-%d-%m").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        return {
            'time': time,
            'lines': self._lines, #Exeple comment repmlir une ligede table a adapter selon ton besoin
            'get_paie_values': self._get_paie_values,
            'start_date': start_date,
            'end_date': end_date
        }

