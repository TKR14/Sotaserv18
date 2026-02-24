
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (http://tiny.be). All Rights Reserved
#
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from pytz import timezone
import xml.etree.ElementTree as ET
import base64
import xlsxwriter
import io
import math



class hr_employee(models.Model):

    _inherit = 'hr.employee'

    address = fields.Text('Adresse')
    civility = fields.Selection([('mr', 'Monsieur'), ('mlle', 'Mademoiselle'), (
        'mme', 'Madame')], 'Civilité', select=True, readonly=False, default='mr')
    first_name  = fields.Char(string="Prénom")
    last_name  = fields.Char(string="Nom")
    gender_code = fields.Integer(compute="_compute_gender_code")
    marital_code = fields.Integer(compute="_compute_marital_code")
    nationality_code = fields.Selection([
        ('I', 'Ivoirien'),
        ('AA', 'Autre Africain'),
        ('F', 'Français'),
        ('SL', 'Syrien ou Libanais'),
        ('A', 'Autres'),
    ], string="Code Nationalité")
    category = fields.Selection([
        ('local', 'Local'),
        ('expat', 'Expatrié'),
    ], string="Catégorie", default='local')
    first_contract_date = fields.Date(compute='_compute_first_contract_date', groups="hr.group_hr_user,building_plus.sotaserv_daf")
    contract_warning = fields.Boolean(string='Contract Warning', store=True, compute='_compute_contract_warning', groups="hr.group_hr_user,building_plus.sotaserv_daf")
    barcode = fields.Char(string="Badge ID", help="ID used for employee identification.", groups="hr.group_hr_user,building_plus.sotaserv_daf", copy=False)

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(hr_employee, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if toolbar and self._context.get('hide_actions'):
            if 'toolbar' in res and 'action' in res['toolbar']:
                res['toolbar']['action'] = []
                res['toolbar']['print'] = []
        return res
    
    @api.depends("gender")
    def _compute_gender_code(self):
        for employee in self:
            employee.gender_code = None
            if employee.gender == "male":
                employee.gender_code = 0
            elif employee.gender == "female":
                employee.gender_code = 1

    @api.depends("marital")
    def _compute_marital_code(self):
        for employee in self:
            employee.marital_code = None
            if employee.marital == "signle":
                employee.marital_code = 0
            elif employee.marital == "married":
                employee.marital_code = 1
            elif employee.marital == "widower":
                employee.marital_code = 2
            elif employee.marital == "divorced":
                employee.marital_code = 3

    @api.onchange('first_name', 'last_name')
    def onchange_first_last_name(self):
        if self.first_name and self.last_name:
            self.name = self.last_name +' '+ self.first_name

class hr_general_income_tax(models.Model):

    _name = 'hr.payroll_ma.general_income_tax'

    _description = 'Config IR'

    name = fields.Char('Nom', size=20)
    slace_start = fields.Float("Debut de Tranche")
    slace_end = fields.Float("Fin de Tranche")
    rate = fields.Float("Taux")
    package_to_be_deducted = fields.Float("Forfait à déduire")


class hr_senrioty(models.Model):

    _name = 'hr.payroll_ma.senrioty'

    _description = 'Configurer les tranches de la prime d\'anciennete'

    name = fields.Char('Nom', size=100)
    slace_start = fields.Float("Debut de Tranche")
    slace_end = fields.Float("Fin de Tranche")
    rate = fields.Float("Taux")

# class hr_additional_hour_categ(models.Model):

#     _name = 'hr.payroll_ma.additional_hour.categ'

#     _description = 'Config des heures supplementaires'

#     @api.multi
#     def name_get(self):
#         result = []
#         for h in self:
#             result.append((h.id, "%s %s" % ('['+h.type_day+']', h.name)))
#         return result

#     name = fields.Char('Nom', size=100)
#     type_day = fields.Selection([('working_day', 'Jour Ouvrable'), ('day_off', 'Jour de repos/firié'), ],'Type du jour')
#     rate = fields.Float("Taux")

# class hr_additional_hour(models.Model):

#     _name = 'hr.payroll_ma.additional_hour'

#     _description = 'Gestion des heures supplementaires'

#     date = fields.Date('Date')
#     categ_id = fields.Many2one('hr.payroll_ma.additional_hour.categ', string='Catégorie Heure Supplémentaire')
#     emp_id = fields.Many2one('hr.employee', string='Employée')
#     nb_hour = fields.Float("Nombre des heurs")
#     state = fields.Selection([('draft', 'Brouillon'), ('validated', 'Validé'),('payed', 'Payé'), ],'Status',default='draft')

#     @api.multi
#     def action_validate(self):
#         self.state = 'validated'
#         return True


class hr_salary_band(models.Model):

    _name = 'hr.payroll_ma.salary.band'

    _description = 'Tranches de salaire'

    name = fields.Char('Nom', size=100)
    code = fields.Char('Code Rubrique', size=100)
    slace_start = fields.Float("Debut de Tranche")
    slace_end = fields.Float("Fin de Tranche")
    # value_slace = fields.Float("Valeur tranche", compute='_compute_value_slace')
    value_slace = fields.Float("Plafond Tranche")

    # @api.depends('slace_start', 'slace_end')
    # def _compute_value_slace(self):
    #     for band in self:
    #         band.value_slace = band.slace_end - band.slace_start


class hr_payday_advance(models.Model):

    _name = 'hr.payroll_ma.payday_advance'

    _description = 'Gestion des avances sur salaire'

    date = fields.Date('Date')
    emp_id = fields.Many2one('hr.employee', string='Employée')
    amount = fields.Float("Montant")
    state = fields.Selection([('draft', 'Brouillon'), ('validated',
                             'Validé'), ('payed', 'Payé'), ], 'Status', default='draft')

    def action_validate(self):
        for advance in self:
            advance.state = 'validated'
        return True

    def action_payed(self):
        for advance in self:
            advance.state = 'payed'
        return True


class hr_loan(models.Model):

    _name = 'hr.payroll_ma.loan'

    _description = 'Gestion des prets'

    date = fields.Date('Date')
    emp_id = fields.Many2one('hr.employee', string='Employée')
    amount = fields.Float("Montant")
    state = fields.Selection([('draft', 'Brouillon'), ('granted', 'Octroyé'),
                             ('refunded', 'Remboursé'), ], 'Status', default='draft')

    def action_granted(self):
        self.state = 'granted'
        return True

    def action_refunded(self):
        self.state = 'refunded'
        return True


class hr_time_payroll(models.Model):

    _name = 'hr.time.payroll'
    _description = 'Gestion des temps de paie'
    _rec_name = 'description'

    date_from = fields.Date(string="Date de début", compute="_compute_dates", store=True)
    date_to = fields.Date(string="Date de fin", compute="_compute_dates", store=True)
    emp_id = fields.Many2one('hr.employee', string='Employée')
    total_hours = fields.Float("Heurs travaillées")

    payslip_year = fields.Char(string="Année", required=True)
    payslip_month = fields.Selection(
        selection=[('1', 'Janvier'), ('2', 'Février'), ('3', 'Mars'),
                ('4', 'Avril'), ('5', 'Mai'), ('6', 'Juin'),
                ('7', 'Juillet'), ('8', 'Août'), ('9', 'Septembre'),
                ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Décembre')],
        string='Mois',
        required=True
    )
    description = fields.Text(string="Description")
    lines_count = fields.Integer(string="Total des lignes", compute="_compute_lines_count", store=True)
    payroll_line_ids = fields.One2many('hr.time.payroll.line', 'payroll_id', string="Détails du pointage")
    state = fields.Selection(
        [
            ('draft', 'Brouillon'),
            ('confirmed', 'Confirmé'),
            ('done', 'Validé'),
        ],
        string="Statut",
        default='draft'
    )

    @api.model
    def create(self, vals):
        existing_record = self.search([
            ('payslip_year', '=', vals.get('payslip_year')),
            ('payslip_month', '=', vals.get('payslip_month')),
        ], limit=1)
        
        if existing_record:
            raise ValidationError(_(
                "Un pointage existe déjà pour le mois {month} de l'année {year}.".format(
                    month=dict(self._fields['payslip_month'].selection).get(vals.get('payslip_month')),
                    year=vals.get('payslip_year')
                )
            ))

        return super(hr_time_payroll, self).create(vals)

    # @api.onchange('payslip_year', 'payslip_month')
    # def _onchange_payslip_date(self):
    #     """Génère automatiquement les lignes en fonction de l'année et du mois choisis."""
    #     if not self.payslip_year or not self.payslip_month:
    #         return

    #     try:
    #         month = int(self.payslip_month)
    #         year = int(self.payslip_year)
    #     except ValueError:
    #         raise UserError(_("L'année ou le mois sélectionné est invalide. Veuillez corriger votre sélection."))

    #     if year < 1900 or year > 2100:
    #         raise UserError(_("L'année sélectionnée est hors des limites raisonnables (1900-2100)."))

    #     try:
    #         start_date = datetime(year, month, 1)
    #         end_date = start_date + relativedelta(months=1, days=-1)
    #     except Exception:
    #         raise UserError(_("Erreur lors du calcul des dates. Veuillez vérifier vos entrées."))

    #     contracts = self.env['hr.contract'].search([
    #         ('date_start', '<=', end_date),
    #         '|',
    #         ('date_end', '>=', start_date),
    #         ('date_end', '=', False),
    #         ('state', '=', 'open')
    #     ])

    #     lines = []
    #     for contract in contracts:
    #         lines.append((0, 0, {
    #             'employee_id': contract.employee_id.id,
    #             'worked_days': 30,
    #             'holiday_days': 0,
    #             'sickness_days': 0,
    #             'absence_days': 0,
    #             'stc_amount': 0.0,
    #         }))

    #     self.payroll_line_ids = lines

    @api.depends('payslip_year', 'payslip_month')
    def _compute_dates(self):
        for record in self:
            if not record.payslip_year or not record.payslip_month:
                record.date_from = False
                record.date_to = False
                continue

            try:
                year = int(record.payslip_year)
                month = int(record.payslip_month)
                record.date_from = datetime(year, month, 1).date()
                record.date_to = (datetime(year, month, 1) + relativedelta(months=1, days=-1)).date()
            except ValueError:
                raise UserError(_("L'année ou le mois sélectionné est invalide. Veuillez vérifier vos entrées."))

    def _get_worked_days(self, contract, date_from, date_to):
        """
        Calcule les jours travaillés selon la date de début du contrat.
        Si le contrat commence après le 1er du mois, on calcule la différence.
        Sinon, c'est 30 jours.
        """
        first_day_of_month = date_from.replace(day=1)
        if contract.date_start and contract.date_start > first_day_of_month:
            start_date = max(contract.date_start, date_from)
            return (date_to - start_date).days + 1
        return 30
        
    # @api.onchange('payslip_year', 'payslip_month')
    # def _onchange_generate_lines(self):
    #     """Génère automatiquement les lignes en fonction de l'année et du mois choisis."""
    #     if not self.date_from or not self.date_to:
    #         self.payroll_line_ids = False
    #         return

    #     contracts = self.env['hr.contract'].search([
    #         ('state', '=', 'open'),  
    #         ('date_start', '<=', self.date_to), 
    #         '|', 
    #         ('date_end', '>=', self.date_from), 
    #         ('date_end', '=', False),
    #         ('employee_id.active', '=', True)   
    #     ])

    #     lines = []
    #     for contract in contracts:
    #         # start_date = max(contract.date_start, self.date_from)
    #         # worked_days = (self.date_to - start_date).days + 1 

    #         lines.append((0, 0, {
    #             'employee_id': contract.employee_id.id,
    #             # 'worked_days': worked_days,  
    #             'worked_days': 30,  
    #             'holiday_days': 0,  
    #             'sickness_days': 0,  
    #             'absence_days': 0,  
    #             'stc_amount': 0.0,  
    #         }))

    #     self.payroll_line_ids = lines

    @api.onchange('payslip_year', 'payslip_month')
    def _onchange_generate_lines(self):
        if not self.date_from or not self.date_to:
            self.payroll_line_ids = False
            return

        contracts = self.env['hr.contract'].search([
            ('state', '=', 'open'),
            ('date_start', '<=', self.date_to),
            '|',
            ('date_end', '>=', self.date_from),
            ('date_end', '=', False),
            ('employee_id.active', '=', True)
        ])

        lines = []
        for contract in contracts:
            worked_days = self._get_worked_days(contract, self.date_from, self.date_to)
            lines.append((0, 0, {
                'employee_id': contract.employee_id.id,
                'worked_days': worked_days,
                'holiday_days': 0,
                'sickness_days': 0,
                'absence_days': 0,
                'stc_amount': 0.0,
            }))

        self.payroll_line_ids = lines
        
    # @api.onchange('payslip_year', 'payslip_month')
    # def _onchange_payslip_date(self):
    #     """Génère automatiquement les lignes en fonction de l'année et du mois choisis."""
    #     if not self.payslip_year or not self.payslip_month:
    #         return

    #     try:
    #         month = int(self.payslip_month)
    #         year = int(self.payslip_year)
    #     except ValueError:
    #         raise UserError(_("L'année ou le mois sélectionné est invalide. Veuillez corriger votre sélection."))

    #     if year < 1900 or year > 2100:
    #         raise UserError(_("L'année sélectionnée est hors des limites raisonnables (1900-2100)."))

    #     try:
    #         start_date = datetime(year, month, 1)
    #         end_date = start_date + relativedelta(months=1, days=-1)
    #     except Exception:
    #         raise UserError(_("Erreur lors du calcul des dates. Veuillez vérifier vos entrées."))

    #     self.start_date = start_date.date()
    #     self.end_date = end_date.date()

    #     contracts = self.env['hr.contract'].search([
    #         ('date_start', '<=', end_date),
    #         '|',
    #         ('date_end', '>=', start_date),
    #         ('date_end', '=', False),
    #         ('state', '=', 'open')
    #     ])

    #     lines = []
    #     for contract in contracts:
    #         lines.append((0, 0, {
    #             'employee_id': contract.employee_id.id,
    #             'worked_days': 30,
    #             'holiday_days': 0,
    #             'sickness_days': 0,
    #             'absence_days': 0,
    #             'stc_amount': 0.0,
    #         }))

    #     self.payroll_line_ids = lines

    @api.depends('payroll_line_ids')
    def _compute_lines_count(self):
        for record in self:
            record.lines_count = len(record.payroll_line_ids)
    
    # def action_regenerate(self):
    #     for record in self:
    #         if record.state == 'done':
    #             raise ValidationError(_("Le pointage ne peut pas être regénéré lorsque l'état est 'Fait'."))

    #         if not record.date_from or not record.date_to:
    #             raise ValidationError(_("Les dates de début et de fin doivent être définies pour regénérer les lignes."))

    #         contracts = self.env['hr.contract'].search([
    #             ('state', '=', 'open'),
    #             ('date_start', '<=', record.date_to),
    #             '|',
    #             ('date_end', '>=', record.date_from),
    #             ('date_end', '=', False),
    #             ('employee_id.active', '=', True)
    #         ])

    #         lines = []
    #         existing_employees = record.payroll_line_ids.mapped('employee_id')
    #         for contract in contracts:
    #             if contract.employee_id not in existing_employees:
    #                 # start_date = max(contract.date_start, record.date_from)  
    #                 # worked_days = (record.date_to - start_date).days + 1 

    #                 lines.append((0, 0, {
    #                     'employee_id': contract.employee_id.id,
    #                     # 'worked_days': worked_days,
    #                     'worked_days': 30,
    #                     'holiday_days': 0,
    #                     'sickness_days': 0,
    #                     'absence_days': 0,
    #                     'stc_amount': 0.0,
    #                 }))

    #         if lines:
    #             record.payroll_line_ids = record.payroll_line_ids + lines  

    #         record.description = _("Lignes de pointage regénérées avec succès.")
    #     return True

    def action_regenerate(self):
        for record in self:
            if record.state == 'done':
                raise ValidationError(_("Le pointage ne peut pas être regénéré lorsque l'état est 'Fait'."))

            if not record.date_from or not record.date_to:
                raise ValidationError(_("Les dates de début et de fin doivent être définies pour regénérer les lignes."))

            contracts = self.env['hr.contract'].search([
                ('state', '=', 'open'),
                ('date_start', '<=', record.date_to),
                '|',
                ('date_end', '>=', record.date_from),
                ('date_end', '=', False),
                ('employee_id.active', '=', True)
            ])

            lines = []
            existing_employees = record.payroll_line_ids.mapped('employee_id')
            for contract in contracts:
                if contract.employee_id not in existing_employees:
                    worked_days = self._get_worked_days(contract, record.date_from, record.date_to)
                    lines.append((0, 0, {
                        'employee_id': contract.employee_id.id,
                        'worked_days': worked_days,
                        'holiday_days': 0,
                        'sickness_days': 0,
                        'absence_days': 0,
                        'stc_amount': 0.0,
                        'avance': 0.0,
                        'gratification': 0.0,
                        'ind_licenciement': 0.0,
                        'ind_fin_contrat': 0.0,
                        'preavis': 0.0,
                        'rappel': 0.0,
                    }))

            if lines:
                record.payroll_line_ids = record.payroll_line_ids + lines

            record.description = _("Lignes de pointage regénérées avec succès.")
        return True
    
    def action_open_details(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Détails du Pointage',
            'view_mode': 'list,form',
            'res_model': 'hr.time.payroll.line',
            'domain': [('payroll_id', '=', self.id)],
            'context': {'default_payroll_id': self.id},
            'target': 'current',
        }

    # def action_open_details(self):
    #     return {
    #         'name': 'Détail Pointage',
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'list,form',
    #         'res_model': 'hr.time.payroll.line',
    #         'target': 'new',
    #         'context': {'default_payroll_id': self.id},
    #     }

class HrTimePayrollLine(models.Model):
    _name = 'hr.time.payroll.line'
    _description = 'Détail du pointage'

    payroll_id = fields.Many2one('hr.time.payroll', string="Temps de paie", ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string="Employé", required=True)
    worked_days = fields.Integer(string="Jrs Trav.", compute="_compute_worked_days", store=True,)
    holiday_days = fields.Integer(string="Jrs Congé", default=0)
    sickness_days = fields.Integer(string="Jrs Congé Maladie", default=0)
    absence_days = fields.Integer(string="Jrs Absence", default=0)
    stc_amount = fields.Float(string="Jrs STC", default=0.0)
    stc = fields.Float(string="STC", default=0.0)
    avance = fields.Float(string="Avance", default=0.0)
    date_from = fields.Date(related='payroll_id.date_from', string="Date début")
    date_to = fields.Date(related='payroll_id.date_to', string="Date fin")

    preavis = fields.Float(string="Préavis", default=0.0)
    ind_licenciement = fields.Float(string="Ind licenciement", default=0.0)
    ind_fin_contrat = fields.Float(string=" Ind. fin de contrat", default=0.0)
    gratification = fields.Float(string="Gratification", default=0.0)
    rappel = fields.Float(string="Rappel", default=0.0)

    # @api.depends('holiday_days', 'sickness_days', 'absence_days')
    # def _compute_worked_days(self):
    #     """
    #     Calculer le nombre de jours travaillés en fonction des autres champs.
    #     """
    #     for record in self:
    #         # contract = self.env['hr.contract'].search([
    #         #     ('employee_id', '=', record.employee_id.id),
    #         #     ('state', '=', 'open')
    #         # ], order='date_start desc', limit=1)

    #         # if contract and contract.date_start:
    #         #     start_date = max(contract.date_start, record.date_from)
    #         # else:
    #         #     start_date = record.date_from

    #         # total_days = (record.date_to - start_date).days + 1
    #         total_days_off = (record.holiday_days or 0) + (record.sickness_days or 0) + (record.absence_days or 0)
    #         record.worked_days = 30 - total_days_off if total_days_off <= 30 else 0
    #         # record.worked_days = max(total_days - total_days_off, 0) 


    def _get_worked_days(self, contract, date_from, date_to):
        """
        Calcule les jours travaillés selon la date de début du contrat.
        Si le contrat commence après le 1er du mois, on calcule la différence.
        Sinon, c'est 30 jours.
        """
        first_day_of_month = date_from.replace(day=1)
        if contract.date_start and contract.date_start > first_day_of_month:
            start_date = max(contract.date_start, date_from)
            return (date_to - start_date).days + 1
        return 30

    @api.depends('holiday_days', 'sickness_days', 'absence_days')
    def _compute_worked_days(self):
        for record in self:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', record.employee_id.id),
                ('state', '=', 'open')
            ], order='date_start desc', limit=1)

            worked_days = self._get_worked_days(contract, record.date_from, record.date_to) if contract else 30
            total_days_off = (record.holiday_days or 0) + (record.sickness_days or 0) + (record.absence_days or 0)
            record.worked_days = max(worked_days - total_days_off, 0)

# class hr_absence(models.Model):

#     _name = 'hr.payroll_ma.absence'

#     _description = 'Gestion des absences'

#     date = fields.Date('Date')
#     emp_id = fields.Many2one('hr.employee', string='Employée')
#     nb_hours = fields.Float("Nombre des heurs")
#     note = fields.Text("Motif")
#     state = fields.Selection([('draft', 'Brouillon'), ('validated', 'Validé'), ('done', 'Traité'), ], 'Status',default='draft')

#     @api.multi
#     def action_validate(self):
#         self.state = 'validated'
#         return True


class hr_contract(models.Model):

    _inherit = 'hr.contract'

    hourly_wage = fields.Float("Salaire de base par heure", required=False)
    wage_per_day = fields.Float("Salaire de base par jour", required=False)
    contract_type = fields.Selection([('cdi', 'CDI'), ('cdd', 'CDD'), ('cdc', 'CDC'), ('cdc-e', 'CDC-E'),
                                     ('fulltime', 'Plein temps'), ('parttime', 'Temps Partiel'), ('training', 'Stage')], 'Type', required=False)
    workplace = fields.Char("Lieu de travail")
    material_resources = fields.Text("Moyens Matériels")
    allowance_leave = fields.Float("Reliquat Congé", default=0)
    net_hourly_wage = fields.Float("Salaire Net par heure", required=False)
    salary_supplement = fields.Float("Complément de salaire", default=0)
    salaire_c = fields.Float(string="Salaire catégoriel")
    s_salaire = fields.Float(string="Sur salaire")
    a_p_imposable = fields.Float(string="Autre prime imposable")
    wage = fields.Float(default=0)
    wage_type = fields.Selection([
        ('H', 'Horaire'),
        ('M', 'Mensuel')
    ], string="Type de Salaire", required=True, default='M')

    @api.onchange("salaire_c")
    def _onchange_salaire_c(self):
        self.wage = self.salaire_c

class hr_salary_rule(models.Model):

    _inherit = 'hr.salary.rule'

    is_deduction = fields.Boolean("Retenue ?")
    is_gain = fields.Boolean("Gain ?")


DICT_CODE_RUB_FIELDS_CONTRACT = {
    '45': 'other_allowance',
    '46': 'hra',
    '49': 'da',
    '53': 'travel_allowance',
    '54': 'meal_allowance',
    '56': 'medical_allowance'
}


class hr_payslip(models.Model):

    _inherit = 'hr.payslip'

    amount_advance = fields.Float("Avance", default=0)
    amount_loan = fields.Float("Prêt", default=0)
    cumulative_sbi = fields.Float("Cumul SBI", default=0)
    cumulative_ded = fields.Float("Cumul Retenues", default=0)
    cumulative_professional_fees = fields.Float("Cumul Abbatements", default=0)
    cumulative_sni = fields.Float("Cumul SNI", default=0)
    cumulative_ir = fields.Float("Cumul IR", default=0)
    cumulative_cnss_amo = fields.Float("Cumul CNSS/AMO", default=0)
    cumulative_worked_days = fields.Float("Cumul jours travailles", default=0)
    cumulative_deduction_family = fields.Float(
        "Cumul Charges Familiales", default=0)
    prev_cumulative_sbi = fields.Float("Cumul Mois Précédent SBI", default=0)
    prev_cumulative_ded = fields.Float(
        "Cumul Mois Précédent Retenues", default=0)
    prev_cumulative_professional_fees = fields.Float(
        "Cumul Mois Précédent Abbatements", default=0)
    prev_cumulative_sni = fields.Float("Cumul Mois Précédent SNI", default=0)
    prev_cumulative_ir = fields.Float("Cumul Mois Précédent IR", default=0)
    prev_cumulative_cnss_amo = fields.Float(
        "Cumul Mois Précédent CNSS/AMO", default=0)
    prev_cumulative_worked_days = fields.Float(
        "Cumul Mois Précédent jours travailles", default=0)
    prev_cumulative_deduction_family = fields.Float(
        "Cumul Mois Précédent Charges Familiales", default=0)
    year = fields.Char("Année")
    month = fields.Char("Mois")
    ir_factor = fields.Float("Facteur IR")
    nb_year = fields.Float("Ancienneté")
    nb_months = fields.Integer("Ancienneté en mois", compute="_compute_nb_months", store=True)
    rate_senrioty = fields.Float("Taux d'Ancienneté")
    allowance_leave = fields.Float("Reliquat Congé", default=0)
    cumulative_nb_days_leave = fields.Float("Droit de congé", default=0)
    leaves_taken = fields.Float("Congés pris", default=0)
    total_days_leave = fields.Float("Total congé", default=0)
    display_days_leave = fields.Float("Solde de congé", default=0)

    worked_days_computed = fields.Float(string="Jours Travaillés Calculés", compute="_compute_days")
    holiday_days_computed = fields.Float(string="Jours de Congés Calculés", compute="_compute_days")
    sickness_days_computed = fields.Float(string="Jours de Maladie Calculés", compute="_compute_days")
    absence_days_computed = fields.Float(string="Jours d'Absence Calculés", compute="_compute_days")
    journal_id = fields.Many2one("account.journal", default=lambda self: self.env['account.journal'].search([("name", "=", "Paie")], limit=1).id)
    avance_computed = fields.Float(string="Avance", compute="_compute_days")
    stc_amount_computed = fields.Float(string="Jrs STC", compute="_compute_days")
    stc_computed = fields.Float(string="STC", compute="_compute_days")

    preavis_computed = fields.Float(string="Préavis", compute="_compute_days")
    ind_licenciement_computed = fields.Float(string="Indemnité de licenciement", compute="_compute_days")
    ind_fin_contrat_computed = fields.Float(string="Ind. fin de contrat", compute="_compute_days")
    gratification_computed = fields.Float(string="Gratification", compute="_compute_days")
    rappel_computed = fields.Float(string="Rappel", compute="_compute_days")

    @api.depends('date_from', 'date_to', 'employee_id')
    def _compute_days(self):
        for payslip in self:
            if not (payslip.date_from and payslip.date_to and payslip.employee_id):
                payslip.worked_days_computed = 0
                payslip.holiday_days_computed = 0
                payslip.sickness_days_computed = 0
                payslip.absence_days_computed = 0
                payslip.avance_computed = 0
                payslip.stc_amount_computed = 0
                payslip.stc_computed = 0
                payslip.preavis_computed = 0
                payslip.ind_licenciement_computed = 0
                payslip.ind_fin_contrat_computed = 0
                payslip.gratification_computed = 0
                payslip.rappel_computed = 0
                continue

            contracts = self.env['hr.contract'].search([
                ('employee_id', '=', payslip.employee_id.id),
                ('state', '=', 'open'),
                ('date_start', '<=', payslip.date_to),
                '|', ('date_end', '>=', payslip.date_from), ('date_end', '=', False)
            ])

            if not contracts:
                payslip.worked_days_computed = 0
                payslip.holiday_days_computed = 0
                payslip.sickness_days_computed = 0
                payslip.absence_days_computed = 0
                payslip.avance_computed = 0
                payslip.stc_amount_computed = 0
                payslip.stc_computed = 0
                payslip.preavis_computed = 0
                payslip.ind_licenciement_computed = 0
                payslip.ind_fin_contrat_computed = 0
                payslip.gratification_computed = 0
                payslip.rappel_computed = 0
                continue

            time_payroll_line = self.env['hr.time.payroll.line'].search([
                ('employee_id', '=', payslip.employee_id.id),
                ('date_from', '>=', payslip.date_from),
                ('date_to', '<=', payslip.date_to),
            ], limit=1)

            payslip.worked_days_computed = time_payroll_line.worked_days
            payslip.holiday_days_computed = time_payroll_line.holiday_days
            payslip.sickness_days_computed = time_payroll_line.sickness_days
            payslip.absence_days_computed = time_payroll_line.absence_days
            payslip.avance_computed = time_payroll_line.avance
            payslip.stc_amount_computed = time_payroll_line.stc_amount
            payslip.stc_computed = time_payroll_line.stc
            payslip.preavis_computed = time_payroll_line.preavis
            payslip.ind_licenciement_computed = time_payroll_line.ind_licenciement
            payslip.ind_fin_contrat_computed = time_payroll_line.ind_fin_contrat
            payslip.gratification_computed = time_payroll_line.gratification
            payslip.rappel_computed = time_payroll_line.rappel

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee_dates(self):
        advances = self.env['hr.payroll_ma.payday_advance'].search([('emp_id', '=', self.employee_id.id), (
            'date', '>=', self.date_from), ('date', '<=', self.date_to), ('state', '=', 'payed')])
        amount_advance = 0
        if advances:
            amount_advance = sum(adv.amount for adv in advances)
        self.amount_advance = amount_advance
        loans = self.env['hr.payroll_ma.loan'].search([('emp_id', '=', self.employee_id.id), (
            'date', '>=', self.date_from), ('date', '<=', self.date_to), ('state', '=', 'granted')])
        amount_loan = 0
        if loans:
            amount_loan = sum(loan.amount for loan in loans)
        self.amount_loan = amount_loan

        prev_cumulative_sbi = 0
        prev_cumulative_ded = 0
        prev_cumulative_professional_fees = 0
        prev_cumulative_sni = 0
        prev_cumulative_ir = 0
        prev_cumulative_cnss_amo = 0
        prev_cumulative_worked_days = 0
        prev_cumulative_deduction_family = 0

        all_payslip_emp = self.search([('year', '=', self.date_to.year), ('date_to', '<', self.date_to), (
            'employee_id', '=', self.employee_id.id), ('state', '!=', 'cancel'), ('id', '!=', self._origin.id)])
        nb_paid_month = len(all_payslip_emp) + 1
        self.ir_factor = 12/nb_paid_month
        self.month = nb_paid_month
        last_payslip_emp = self.search([('year', '=', self.date_to.year), ('month', '=', int(
            nb_paid_month - 1)), ('employee_id', '=', self.employee_id.id), ('state', '!=', 'cancel'), ('id', '!=', self._origin.id)])
        if last_payslip_emp:
            prev_cumulative_sbi = last_payslip_emp.cumulative_sbi
            prev_cumulative_ded = last_payslip_emp.cumulative_ded
            prev_cumulative_professional_fees = last_payslip_emp.cumulative_professional_fees
            prev_cumulative_sni = last_payslip_emp.cumulative_sni
            prev_cumulative_ir = last_payslip_emp.cumulative_ir
            prev_cumulative_cnss_amo = last_payslip_emp.cumulative_cnss_amo
            prev_cumulative_worked_days = last_payslip_emp.cumulative_worked_days
            prev_cumulative_deduction_family = last_payslip_emp.cumulative_deduction_family
        self.prev_cumulative_sbi = prev_cumulative_sbi
        self.prev_cumulative_ded = prev_cumulative_ded
        self.prev_cumulative_professional_fees = prev_cumulative_professional_fees
        self.prev_cumulative_sni = prev_cumulative_sni
        self.prev_cumulative_ir = prev_cumulative_ir
        self.prev_cumulative_cnss_amo = prev_cumulative_cnss_amo
        self.prev_cumulative_worked_days = prev_cumulative_worked_days
        self.prev_cumulative_deduction_family = prev_cumulative_deduction_family

        date_to = fields.Date.to_string(
            (self.date_from + relativedelta(months=+1, day=1, days=-1)))
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        self.date_to = date_to
        self.year = date_to.year

        # if self.contract_id:
        #     nb_year = ((((date_to-self.contract_id.date_start).days)*12)/365)
        #     self.nb_year = nb_year
        #     rate_senrioty = 0
        #     senrioty = self.env['hr.payroll_ma.senrioty'].search(
        #         [('slace_start', '<=', nb_year), ('slace_end', '>', nb_year)])
        #     if senrioty:
        #         rate_senrioty = senrioty.rate
        #     self.rate_senrioty = rate_senrioty
        if self.contract_id:
            delta = relativedelta(date_to, self.contract_id.date_start)
            nb_year = delta.years  
            self.nb_year = nb_year

            rate_senrioty = 0
            senrioty = self.env['hr.payroll_ma.senrioty'].search(
                [('slace_start', '<=', nb_year), ('slace_end', '>', nb_year)]
            )
            if senrioty:
                rate_senrioty = senrioty.rate
            self.rate_senrioty = rate_senrioty

    @api.depends('nb_year')
    def _compute_nb_months(self):
        for rec in self:
            if rec.nb_year:
                rec.nb_months = math.floor(rec.nb_year * 12)
            else:
                rec.nb_months = 0

    def compute_prev_vals(self, employee_id, contract_id, date_from, date_to):
        res = {}
        advances = self.env['hr.payroll_ma.payday_advance'].search(
            [('emp_id', '=', employee_id), ('date', '>=', date_from), ('date', '<=', date_to), ('state', '=', 'payed')])
        amount_advance = 0
        if advances:
            amount_advance = sum(adv.amount for adv in advances)

        loans = self.env['hr.payroll_ma.loan'].search([('emp_id', '=', self.employee_id.id), (
            'date', '>=', self.date_from), ('date', '<=', self.date_to), ('state', '=', 'granted')])
        amount_loan = 0
        if loans:
            amount_loan = sum(loan.amount for loan in loans)

        prev_cumulative_sbi = 0
        prev_cumulative_ded = 0
        prev_cumulative_professional_fees = 0
        prev_cumulative_sni = 0
        prev_cumulative_ir = 0
        prev_cumulative_cnss_amo = 0
        prev_cumulative_worked_days = 0
        prev_cumulative_deduction_family = 0

        all_payslip_emp = self.search(
            [('year', '=', date_to.year), ('employee_id', '=', employee_id), ('state', '!=', 'cancel')])
        nb_paid_month = len(all_payslip_emp) + 1

        last_payslip_emp = self.search([('year', '=', date_to.year), ('month', '=', int(
            nb_paid_month - 1)), ('employee_id', '=', employee_id), ('state', '!=', 'cancel')])

        if last_payslip_emp:
            prev_cumulative_sbi = last_payslip_emp.cumulative_sbi
            prev_cumulative_ded = last_payslip_emp.cumulative_ded
            prev_cumulative_professional_fees = last_payslip_emp.cumulative_professional_fees
            prev_cumulative_sni = last_payslip_emp.cumulative_sni
            prev_cumulative_ir = last_payslip_emp.cumulative_ir
            prev_cumulative_cnss_amo = last_payslip_emp.cumulative_cnss_amo
            prev_cumulative_worked_days = last_payslip_emp.cumulative_worked_days
            prev_cumulative_deduction_family = last_payslip_emp.cumulative_deduction_family

        # nb_year = 0
        # rate_senrioty = 0
        # contract = self.env['hr.contract'].browse(contract_id)
        # if contract:
        #     nb_year = ((((date_to-contract.date_start).days)*12)/365)
        #     senrioty = self.env['hr.payroll_ma.senrioty'].search(
        #         [('slace_start', '<=', nb_year), ('slace_end', '>', nb_year)])
        #     if senrioty:
        #         rate_senrioty = senrioty.rate
        
        nb_year = 0
        rate_senrioty = 0
        contract = self.env['hr.contract'].browse(contract_id)

        if contract and contract.date_start:
            delta = relativedelta(date_to, contract.date_start)
            nb_year = delta.years 

            senrioty = self.env['hr.payroll_ma.senrioty'].search(
                [('slace_start', '<=', nb_year), ('slace_end', '>', nb_year)]
            )
            if senrioty:
                rate_senrioty = senrioty.rate

        self.nb_year = nb_year
        self.rate_senrioty = rate_senrioty

        res.update({
            'prev_cumulative_sbi': prev_cumulative_sbi,
            'prev_cumulative_ded': prev_cumulative_ded,
            'prev_cumulative_professional_fees': prev_cumulative_professional_fees,
            'prev_cumulative_sni': prev_cumulative_sni,
            'prev_cumulative_ir': prev_cumulative_ir,
            'prev_cumulative_cnss_amo': prev_cumulative_cnss_amo,
            'prev_cumulative_worked_days': prev_cumulative_worked_days,
            'prev_cumulative_deduction_family': prev_cumulative_deduction_family,
            'year': date_to.year,
            'nb_year': nb_year,
            'amount_advance': amount_advance,
            'amount_loan': amount_loan,
            'ir_factor': 12/nb_paid_month,
            'month': nb_paid_month,
            'rate_senrioty': rate_senrioty
        })
        return res

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(
                fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(
                fields.Date.from_string(date_to), time.max)

            # compute leave days
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(
                day_from, day_to, calendar=contract.resource_calendar_id)
            for day, hours, leave in day_leave_intervals:
                holiday = leave.holiday_id
                current_leave_struct = leaves.setdefault(holiday.holiday_status_id, {
                    'name': holiday.holiday_status_id.name or _('Global Leaves'),
                    'sequence': 5,
                    'code': holiday.holiday_status_id.code or 'GLOBAL',
                    'number_of_days': 0.0,
                    'number_of_hours': 0.0,
                    'contract_id': contract.id,
                })
                current_leave_struct['number_of_hours'] += hours
                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.combine(day, time.min)),
                    tz.localize(datetime.combine(day, time.max)),
                    compute_leaves=False,
                )
                if work_hours:
                    current_leave_struct['number_of_days'] += hours / work_hours

            # compute worked days
            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'contract_id': contract.id,
                'number_of_days': 0,
                'number_of_hours': 0

            }

            if contract.contract_type == 'cdc':
                attendances_obj = self.env['hr.time.payroll'].search(
                    [('emp_id', '=', contract.employee_id.id), ('start_date', '>=', date_from), ('end_date', '<=', date_to)])
                nb_hours = 0
                nb_days = 0
                if attendances:
                    nb_hours = sum(
                        attendance.total_hours for attendance in attendances_obj)
                    nb_days = nb_hours/8
                attendances['number_of_days'] = nb_days
                attendances['number_of_hours'] = nb_hours
            else:
                work_data = contract.employee_id._get_work_days_data(
                    day_from, day_to, calendar=contract.resource_calendar_id)
                if work_data['days'] != 26:
                    work_data['days'] = 26
                attendances['number_of_days'] = work_data['days']
                attendances['number_of_hours'] = work_data['days']*7.35
            res.append(attendances)
            res.extend(leaves.values())
        return res

    def compute_sheet(self):

        for payslip in self:
            ####################### MAJ PRIMES CONTRATS######################
            payslip.contract_id.salary_supplement = 0
            if payslip.contract_id.contract_type == 'cdc':
                dict_contract = {
                    'other_allowance': 0,
                    'hra': 0,
                    'da': 0,
                    'travel_allowance': 0,
                    'meal_allowance': 0,
                    'medical_allowance': 0,
                    'salary_supplement': 0
                }
                payslip.contract_id.write(dict_contract)
                worked_hours = sum(
                    line.number_of_hours for line in payslip.worked_days_line_ids if line.code == 'WORK100')
                if worked_hours > 191:
                    salary_bands = self.env['hr.payroll_ma.salary.band'].search([
                    ])
                    remaining_worked_hours = worked_hours - 191
                    value_remaining_worked_hours = remaining_worked_hours * \
                        payslip.contract_id.net_hourly_wage
                    if salary_bands:
                        for band in salary_bands:
                            if value_remaining_worked_hours > band.value_slace:
                                if band.code in DICT_CODE_RUB_FIELDS_CONTRACT:
                                    dict_contract[DICT_CODE_RUB_FIELDS_CONTRACT[band.code]
                                                  ] = band.value_slace
                                    value_remaining_worked_hours = value_remaining_worked_hours - band.value_slace
                                else:
                                    continue
                            else:
                                if band.code in DICT_CODE_RUB_FIELDS_CONTRACT:
                                    dict_contract[DICT_CODE_RUB_FIELDS_CONTRACT[band.code]
                                                  ] = value_remaining_worked_hours
                                    value_remaining_worked_hours = 0
                                else:
                                    continue

                        if value_remaining_worked_hours > 0:
                            dict_contract['salary_supplement'] = (remaining_worked_hours-(((remaining_worked_hours*payslip.contract_id.net_hourly_wage) -
                                                                  value_remaining_worked_hours)/payslip.contract_id.net_hourly_wage))*(payslip.contract_id.wage/191)
                        payslip.contract_id.write(dict_contract)
            res = super(hr_payslip, self).compute_sheet()
            ################################################################
            tot_sbi = sum(
                line.total for line in payslip.line_ids if line.category_id.code == 'SBI')
            payslip.cumulative_sbi = payslip.prev_cumulative_sbi + tot_sbi
            tot_ded = sum(
                line.total for line in payslip.line_ids if line.category_id.code == 'TDED')
            payslip.cumulative_ded = payslip.prev_cumulative_ded + tot_ded
            tot_professional_fees = sum(
                line.total for line in payslip.line_ids if line.category_id.code == 'ABT')
            payslip.cumulative_professional_fees = payslip.prev_cumulative_professional_fees + \
                tot_professional_fees
            tot_sni = sum(
                line.total for line in payslip.line_ids if line.category_id.code == 'SNI')
            payslip.cumulative_sni = payslip.prev_cumulative_sni + tot_sni
            tot_ir = sum(
                line.total for line in payslip.line_ids if line.category_id.code == 'IRNET')
            payslip.cumulative_ir = payslip.prev_cumulative_ir + tot_ir
            tot_cnss = sum(
                line.total for line in payslip.line_ids if line.category_id.code == 'CNSS')
            tot_amo = sum(
                line.total for line in payslip.line_ids if line.category_id.code == 'AMO')
            payslip.cumulative_cnss_amo = payslip.prev_cumulative_cnss_amo + tot_cnss + tot_amo
            tot_days = sum(
                line.total for line in payslip.line_ids if line.category_id.code == 'WORKEDDAYS')
            payslip.cumulative_worked_days = payslip.prev_cumulative_worked_days + tot_days
            tot_ded_fam = sum(
                line.total for line in payslip.line_ids if line.category_id.code == 'DED')
            payslip.cumulative_deduction_family = payslip.prev_cumulative_deduction_family + tot_ded_fam
            for line in payslip.line_ids:
                if line.salary_rule_id.is_gain:
                    line.is_gain = True
                if line.salary_rule_id.is_deduction:
                    line.is_deduction = True

            allowance_leave = payslip.contract_id.allowance_leave
            cumulative_nb_days_leave = 1.5*int(payslip.month)
            leaves_taken = 0
            for l in payslip.worked_days_line_ids:
                if l.code == 'PAYEDLEAVE':
                    leaves_taken = leaves_taken + l.number_of_days
            total_days_leave = allowance_leave + cumulative_nb_days_leave
            display_days_leave = total_days_leave - leaves_taken

            payslip.allowance_leave = allowance_leave
            payslip.cumulative_nb_days_leave = cumulative_nb_days_leave
            payslip.leaves_taken = leaves_taken
            payslip.total_days_leave = total_days_leave
            payslip.display_days_leave = display_days_leave

        return res

    def action_payslip_done(self):
        res = super(hr_payslip, self).action_payslip_done()
        for payslip in self:
            loans = self.env['hr.payroll_ma.loan'].search([('emp_id', '=', payslip.employee_id.id), (
                'date', '>=', payslip.date_from), ('date', '<=', payslip.date_to), ('state', '=', 'granted')])
            if loans:
                loans.action_refunded()
                # for loan in loans:
                #     loan.action_refunded()
        return res

    def action_payslip_cancel(self):
        if self.move_id:
            self.move_id.button_draft()
            self.move_id.button_cancel()
            self.move_id.unlink()
        return self.write({'state': 'cancel'})


class hr_payslip_line(models.Model):

    _inherit = 'hr.payslip.line'

    rate_amount = fields.Float(
        string='Taux', compute='_compute_rate_base_amount')
    base_amount = fields.Float(
        string='Base', compute='_compute_rate_base_amount')
    run_slip_id = fields.Many2one('hr.payslip.run', string='Lots de bulletins de paie',
                                  related='slip_id.payslip_run_id', store=True, readonly=True)

    def _compute_rate_base_amount(self):
        rate_ir = 0
        amount_ir = 0
        for line in self:
            if line.category_id.code == 'SNI':
                amount_ir = line.total
            if line.category_id.code == 'IRTX':
                rate_ir = line.total*100

        for line in self:
            rate_amount = 0
            base_amount = 0

            if line.category_id.code == 'SB':
                if line.contract_id.contract_type == 'cdc':
                    rate_amount = line.contract_id.wage/191
                else:
                    rate_amount = line.contract_id.wage/26
                base_amount = line.total/rate_amount if rate_amount > 0 else 0

            if line.category_id.code == 'CNSS':
                rate_amount = 4.48
                base_amount = line.total/0.0448

            if line.category_id.code == 'AMO':
                rate_amount = 2.26
                base_amount = line.total/0.0226

            if line.category_id.code == 'IRNET':
                rate_amount = rate_ir
                base_amount = amount_ir

            if line.category_id.code == 'ANC':
                rate_amount = line.slip_id.rate_senrioty
                base_amount = (line.total/rate_amount) * \
                    100 if rate_amount > 0 else 0
            line.rate_amount = rate_amount
            line.base_amount = base_amount


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def _domain_emp(self):
        active_id = self.env.context.get('active_id')
        payslip_run = self.env['hr.payslip.run'].browse(active_id)
        return "[('id', 'in', %s)]" % [contract.employee_id.id for contract in self.env['hr.contract'].search([('state', '=', 'open'), ('date_start', '<=', payslip_run.date_end)])]

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel',
                                    'payslip_id', 'employee_id', 'Employees', domain=_domain_emp)

    def compute_sheet(self):
        payslips = self.env['hr.payslip']
        [data] = self.read()
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = self.env['hr.payslip.run'].browse(
                active_id).read(['date_start', 'date_end', 'credit_note'])
        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')
        if not data['employee_ids']:
            raise UserError(
                _("You must select employee(s) to generate payslip(s)."))
        for employee in self.env['hr.employee'].browse(data['employee_ids']):
            slip_data = self.env['hr.payslip'].onchange_employee_id(
                from_date, to_date, employee.id, contract_id=False)
            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'struct_id': slip_data['value'].get('struct_id'),
                'contract_id': slip_data['value'].get('contract_id'),
                'payslip_run_id': active_id,
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': run_data.get('credit_note'),
                'company_id': employee.company_id.id,
            }
            ######################## MAJ PAR AZIZ############################
            prev_vals = self.env['hr.payslip'].compute_prev_vals(
                employee.id, slip_data['value'].get('contract_id'), from_date, to_date)
            res.update({
                'prev_cumulative_sbi': prev_vals.get('prev_cumulative_sbi'),
                'prev_cumulative_ded': prev_vals.get('prev_cumulative_ded'),
                'prev_cumulative_professional_fees': prev_vals.get('prev_cumulative_professional_fees'),
                'prev_cumulative_sni': prev_vals.get('prev_cumulative_sni'),
                'prev_cumulative_ir': prev_vals.get('prev_cumulative_ir'),
                'prev_cumulative_cnss_amo': prev_vals.get('prev_cumulative_cnss_amo'),
                'prev_cumulative_worked_days': prev_vals.get('prev_cumulative_worked_days'),
                'prev_cumulative_deduction_family': prev_vals.get('prev_cumulative_deduction_family'),
                'year': prev_vals.get('year'),
                'nb_year': prev_vals.get('nb_year'),
                'amount_advance': prev_vals.get('amount_advance'),
                'amount_loan': prev_vals.get('amount_loan'),
                'ir_factor': prev_vals.get('ir_factor'),
                'month': prev_vals.get('month'),
                'rate_senrioty': prev_vals.get('rate_senrioty')
            })
            ################################################################
            payslip = self.env['hr.payslip'].create(res)
            payslip.compute_sheet()
        return {'type': 'ir.actions.act_window_close'}


class AccountMove(models.Model):
    _inherit = "account.move"

    def unlink(self):
        cancelled_moves = self.filtered(lambda m: m.state == "cancel")
        super(AccountMove, cancelled_moves.with_context(
            force_delete=True)).unlink()
        return super(AccountMove, self - cancelled_moves).unlink()


# CNSS
class hr_payslip_run(models.Model):
    _inherit = 'hr.payslip.run'

    move_id = fields.Many2one("account.move", string="Entrée comptable")

    def compute_sheet(self):
        for slip in self.slip_ids:
            slip.compute_sheet()

    def calculer_bds(self):
        for payslip in self.slip_ids:
            bds_cnss = self.env['cnss.bds'].search([('l_status', '=', 'NEW')])
            ps_emp_num_assur = payslip.employee_id.ssnid
            bds_emp_exist = self.env['cnss.bds'].search(
                [('n_num_assure', '=', ps_emp_num_assur)])
            if bds_emp_exist:
                for bds in bds_cnss:
                    bds_date = datetime.strptime(
                        f"15/{bds.l_mois}/{bds.l_annee}", f"%d/%m/%Y").date()
                    if payslip.employee_id.ssnid == bds.n_num_assure and bds_date >= payslip.date_from and bds_date <= payslip.date_to:
                        bds.l_type_enreg = "B02"
                        bds.n_num_affilie = "2703892"
                        bds.l_period = str(bds.l_annee+bds.l_mois)
                        bds.employee_ids = payslip.employee_id.id
                        bds.n_enfants = str(payslip.employee_id.children)
                        if payslip.employee_id.identification_id:
                            bds.l_num_cin = str(
                                payslip.employee_id.identification_id)
                        else:
                            bds.l_num_cin = str('')
                        # line_af = self.env['hr.payslip.line'].search(
                        #     [('slip_id', '=', payslip.id), ('code', '=', 'AF')])
                        # amount_af = 0
                        # if line_af:
                        #     amount_af = line_af.total
                        #     bds.n_af_a_payer = amount_af
                        bds.n_af_a_payer = 0
                        bds.n_af_a_deduire = 0
                        bds.n_af_net_a_payer = 0
                        bds.n_af_a_reverser = 0

                        for l in payslip.worked_days_line_ids:
                            if l.code == 'WORK100':
                                if l.number_of_days <= 26:
                                    bds.n_jour_declares = int(l.number_of_days)
                                else:
                                    bds.n_jour_declares = 26

                        line_sb = self.env['hr.payslip.line'].search(
                            [('slip_id', '=', payslip.id), ('code', '=', 'SBI')])
                        

                        amount_sbg = 0
                        if line_sb:
                            if bds.n_jour_declares < 1:
                                bds.n_salaire_reel = 0
                                bds.n_salaire_plaf = 0
                            else:
                                amount_sbg = line_sb.total
                                bds.n_salaire_reel = int(amount_sbg * 100)

                                if bds.n_salaire_reel > 600000:
                                    bds.n_salaire_plaf = 600000
                                else:
                                    bds.n_salaire_plaf = bds.n_salaire_reel
                                    
                        bds.n_situation = ""
                        bds.n_ctr = bds.n_salaire_reel+bds.n_salaire_plaf+bds.n_jour_declares+int(bds.n_num_assure)
                        bds.l_status = "TRAITE"
            else:

                # line_af = self.env['hr.payslip.line'].search(
                #     [('slip_id', '=', payslip.id), ('code', '=', 'AF')])
                # amount_af = 0
                # if line_af:
                #     amount_af = line_af.total

                line_sb = self.env['hr.payslip.line'].search(
                    [('slip_id', '=', payslip.id), ('code', '=', 'SBI')])

                jour_declares = 0
                for l in payslip.worked_days_line_ids:
                    if l.code == 'WORK100':
                        if l.number_of_days <= 26:
                            jour_declares = int(l.number_of_days)
                        else:
                            jour_declares = 26

                salaire_reel = 0
                salaire_plaf = 0

                if line_sb:
                    if jour_declares < 1:
                        salaire_reel = 0
                        salaire_plaf = 0
                    else:
                        salaire_reel = int(line_sb.total * 100)
                        
                        #bds.n_salaire_reel = salaire_reel
                        if salaire_reel > 600000:
                            salaire_plaf = 600000
                        else:
                            salaire_plaf = salaire_reel

                ctr = salaire_reel+salaire_plaf+jour_declares+int(payslip.employee_id.ssnid)
                line_dbs = self.env['cnss.bds']
                new_line_dbs = line_dbs.create({'l_type_enreg': 'B04', 'n_num_affilie': '2703892', 'l_annee': payslip.date_from.year, 'l_mois': payslip.date_from.month, 'n_num_assure': payslip.employee_id.ssnid,
                                                'employee_ids': payslip.employee_id.id, 'l_num_cin': str(payslip.employee_id.identification_id), 'n_enfants': str(payslip.employee_id.children), 'n_af_a_payer': '0', 'n_af_a_deduire': '0', 'n_af_net_a_payer': '0', 'n_af_a_reverser': '0',
                                                'n_jour_declares': jour_declares, 'n_salaire_reel': salaire_reel, 'n_salaire_plaf': salaire_plaf, 'n_situation': '', 'n_ctr': ctr, 'l_status': 'TRAITE'})
                new_line_dbs

        bds_not_exist = self.env['cnss.bds'].search(
            [('l_status', '=', 'NEW')])
        if bds_not_exist:
            l_bds_cnss = self.env['cnss.bds'].search(
                [('l_status', '=', 'NEW')])
            for bds in l_bds_cnss:
                bds_date = datetime.strptime(
                    f"15/{bds.l_mois}/{bds.l_annee}", f"%d/%m/%Y").date()
                for payslip in self.slip_ids:
                    if bds.n_num_assure != payslip.employee_id.ssnid and bds_date >= payslip.date_from and bds_date <= payslip.date_to:

                        emps = self.env['hr.employee'].search(
                            [('ssnid', '=', bds.n_num_assure)])

                        if emps:
                            bds.employee_ids = emps.id
                        bds.n_situation = "SO"
                        bds.l_type_enreg = "B02"
                        bds.n_af_a_payer = 0
                        bds.n_af_a_deduire = 0
                        bds.n_af_net_a_payer = 0
                        bds.n_af_a_reverser = 0
                        bds.n_jour_declares = 0
                        bds.n_salaire_reel = 0
                        bds.n_salaire_plaf = 0
                        bds.n_ctr = bds.n_salaire_reel+bds.n_salaire_plaf + \
                            bds.n_jour_declares+int(bds.n_num_assure)+1
                        bds.l_status = "TRAITE"

    date_sent_cnss = fields.Date(string='Date émission CNSS')

    def GenerateXML(self):
        data = ET.Element('doc')
       # first element
        element1 = ET.SubElement(data, 'nature_fichier_communique')

        s_elem1 = ET.SubElement(element1, 'L_type_enreg')
        s_elem2 = ET.SubElement(element1, 'N_identif_transfert')
        s_elem3 = ET.SubElement(element1, 'L_cat')
        s_elem4 = ET.SubElement(element1, 'L_filler')
        s_elem1.text = "B00"
        s_elem2.text = "A confirmer"
        s_elem3.text = "B0"
        s_elem4.text = " "
       # second element
        element2 = ET.SubElement(data, 'Entete_globale_declaration')

        s_elem1 = ET.SubElement(element2, 'L_type_enreg')
        s_elem2 = ET.SubElement(element2, 'Num_affilie')
        s_elem3 = ET.SubElement(element2, 'Periode')
        s_elem4 = ET.SubElement(element2, 'Raison_sociale')
        s_elem5 = ET.SubElement(element2, 'L_activite')
        s_elem6 = ET.SubElement(element2, 'L_Adresse')
        s_elem7 = ET.SubElement(element2, 'Ville')
        s_elem8 = ET.SubElement(element2, 'Code_postale')
        s_elem9 = ET.SubElement(element2, 'Code_agence')
        s_elem10 = ET.SubElement(element2, 'Date_emission')
        s_elem11 = ET.SubElement(element2, 'Date_exig')
        # date start
        myDateStart = self.date_start
        myMonthStart = myDateStart.strftime("%m")
        mYearStart = myDateStart.strftime("%Y")
        # date end + 10days
        myDateEnd = self.date_end + timedelta(days=10)
        mYearEnd = myDateEnd.strftime("%Y")
        myMonthEnd = myDateEnd.strftime("%m")
        myDayEnd = myDateEnd.strftime("%d")
        s_elem1.text = "B01"
        s_elem2.text = "a traite"
        s_elem3.text = mYearStart + "/" + myMonthStart
        s_elem4.text = self.env.user.company_id.name
        s_elem5.text = "a traite"
        s_elem6.text = self.env.user.company_id.street
        s_elem7.text = self.env.user.company_id.city
        s_elem8.text = self.env.user.company_id.zip
        s_elem9.text = "a traite"
        s_elem10.text = "??"
        s_elem11.text = mYearEnd + "/" + myMonthEnd + "/" + myDayEnd
       # third element
        element3 = ET.SubElement(data, 'Detail_declaration_sal_sur_preetabli')

        glob_csnn_sim = 0
        old_emp_payslip = self.env["hr.payslip"].search([])

        for payslip in old_emp_payslip:
            element3_vis = ET.SubElement(element3, 'Employer')
            s_elem1 = ET.SubElement(element3_vis, 'L_type_enreg')
            s_elem2 = ET.SubElement(element3_vis, 'Num_affilie')
            s_elem3 = ET.SubElement(element3_vis, 'Periode')
            s_elem4 = ET.SubElement(element3_vis, 'Num_assure')
            s_elem5 = ET.SubElement(element3_vis, 'Nom_prenom')
            s_elem6 = ET.SubElement(element3_vis, 'N_enfants')
            s_elem7 = ET.SubElement(element3_vis, 'N_af_a_payer')
            s_elem8 = ET.SubElement(element3_vis, 'N_af_a_deduire')
            s_elem9 = ET.SubElement(element3_vis, 'N_af_net_a_payer')
            s_elem10 = ET.SubElement(element3_vis, 'N_af_a_reverser')
            s_elem11 = ET.SubElement(element3_vis, 'N_jours_declare')
            s_elem12 = ET.SubElement(element3_vis, 'N_salaire_reel')
            s_elem13 = ET.SubElement(element3_vis, 'N_salaire_plaf')
            s_elem14 = ET.SubElement(element3_vis, 'L_situation')
            s_elem15 = ET.SubElement(element3_vis, 'S_ctr')
            s_elem16 = ET.SubElement(element3_vis, 'L_filler')

            s_elem1.text = "B02"
            s_elem2.text = "a traite"
            s_elem3.text = mYearStart + "/" + myMonthStart
            s_elem4.text = str(payslip.employee_id.ssnid)
            s_elem5.text = payslip.employee_id.name
            s_elem6.text = str(payslip.employee_id.children)
            s_elem7.text = "test"
            s_elem8.text = "test"
            s_elem9.text = "test"
            s_elem10.text = "test"
            s_elem11.text = "test"
            s_elem12.text = "test"
            s_elem13.text = "test"
            s_elem14.text = "test"
            s_elem15.text = "test"
            s_elem16.text = ""
      # fourth element
        element4 = ET.SubElement(
            data, 'Recapitulatif_declaration_sal_sur_preetabli')
        s_elem1 = ET.SubElement(element4, 'L_type_enreg')
        s_elem2 = ET.SubElement(element4, 'Num_affilie')
        s_elem3 = ET.SubElement(element4, 'Periode')
        s_elem4 = ET.SubElement(element4, 'Nbr_salaires')
        s_elem5 = ET.SubElement(element4, 'T_enfants')
        s_elem6 = ET.SubElement(element4, 'T_af_a_payer')
        s_elem7 = ET.SubElement(element4, 'T_af_a_deduire')
        s_elem8 = ET.SubElement(element4, 'T_af_net_a_payer')
        s_elem9 = ET.SubElement(element4, 'T_num_imma')
        s_elem10 = ET.SubElement(element4, 'T_af_a_renverser')
        s_elem11 = ET.SubElement(element4, 'T_jours_declares')
        s_elem12 = ET.SubElement(element4, 'T_salaire_reel')
        s_elem13 = ET.SubElement(element4, 'T_salaire_plaf')
        s_elem14 = ET.SubElement(element4, 'T_ctr')
        s_elem15 = ET.SubElement(element4, 'Filler')

        s_elem1.text = "B03"
        s_elem2.text = "test"
        s_elem3.text = mYearStart + "/" + myMonthStart
        s_elem4.text = "test"
        s_elem5.text = "test"
        s_elem6.text = "test"
        s_elem7.text = "test"
        s_elem8.text = "test"
        s_elem9.text = "test"
        s_elem10.text = "test"
        s_elem11.text = "test"
        s_elem12.text = "test"
        s_elem13.text = "test"
        s_elem14.text = "test"
        s_elem15.text = ""
       # fifth element
        element5 = ET.SubElement(data, 'Detail_declaration_sal_entrants')
        s_elem1 = ET.SubElement(element5, 'L_type_enreg')
        s_elem2 = ET.SubElement(element5, 'Num_affilie')
        s_elem3 = ET.SubElement(element5, 'Periode')
        s_elem4 = ET.SubElement(element5, 'Num_assure')
        s_elem5 = ET.SubElement(element5, 'Nom_prenom')
        s_elem6 = ET.SubElement(element5, 'Num_cin')
        s_elem7 = ET.SubElement(element5, 'nbr_jours')
        s_elem8 = ET.SubElement(element5, 'Sal_reel')
        s_elem9 = ET.SubElement(element5, 'Sal_plaf')
        s_elem10 = ET.SubElement(element5, 'Ctr')
        s_elem11 = ET.SubElement(element5, 'Filler')

        s_elem1.text = "B04"
        s_elem2.text = "test"
        s_elem3.text = mYearStart + "/" + myMonthStart
        s_elem4.text = "test"
        s_elem5.text = "test"
        s_elem6.text = "test"
        s_elem7.text = "test"
        s_elem8.text = "test"
        s_elem9.text = "test"
        s_elem10.text = "test"
        s_elem11.text = ""
       # sixth element
        element6 = ET.SubElement(data, 'Recap_declaration_sal_entrants')
        s_elem1 = ET.SubElement(element6, 'L_type_enreg')
        s_elem2 = ET.SubElement(element6, 'Num_affilie')
        s_elem3 = ET.SubElement(element6, 'Periode')
        s_elem4 = ET.SubElement(element6, 'Nbr_salaires')
        s_elem5 = ET.SubElement(element6, 'T_num_imma')
        s_elem6 = ET.SubElement(element6, 'T_jours_declares')
        s_elem7 = ET.SubElement(element6, 'T_salaire_reel')
        s_elem8 = ET.SubElement(element6, 'T_salaire_plaf')
        s_elem9 = ET.SubElement(element6, 'T_ctr')
        s_elem10 = ET.SubElement(element6, 'Filler')

        s_elem1.text = "B05"
        s_elem2.text = "test"
        s_elem3.text = mYearStart + "/" + myMonthStart
        s_elem4.text = "test"
        s_elem5.text = "test"
        s_elem6.text = "test"
        s_elem7.text = "test"
        s_elem8.text = "test"
        s_elem9.text = "test"
        s_elem10.text = ""
       # seventh element
        element7 = ET.SubElement(data, 'Recap_global_declaration_sal')
        s_elem1 = ET.SubElement(element7, 'L_type_enreg')
        s_elem2 = ET.SubElement(element7, 'Num_affilie')
        s_elem3 = ET.SubElement(element7, 'Periode')
        s_elem4 = ET.SubElement(element7, 'Nbr_salaires')
        s_elem5 = ET.SubElement(element7, 'T_num_imma')
        s_elem6 = ET.SubElement(element7, 'T_jours_declares')
        s_elem7 = ET.SubElement(element7, 'T_salaire_reel')
        s_elem8 = ET.SubElement(element7, 'T_salaire_plaf')
        s_elem9 = ET.SubElement(element7, 'T_ctr')
        s_elem10 = ET.SubElement(element7, 'Filler')

        s_elem1.text = "B06"
        s_elem2.text = "test"
        s_elem3.text = mYearStart + "/" + myMonthStart
        s_elem4.text = "test"
        s_elem5.text = "test"
        s_elem6.text = "test"
        s_elem7.text = "test"
        s_elem8.text = "test"
        s_elem9.text = "test"
        s_elem10.text = ""

        b_xml = ET.tostring(data)
        encoded = base64.b64encode(b_xml)
        attach = self.env['ir.attachment'].create(
            {'name': 'cnss.xml', 'type': 'binary', 'datas': encoded})
        download_url = '/web/content/' + str(attach.id) + '?download=true'

        return {
            'type': 'ir.actions.act_url',
            'url': str(download_url),
            'target': 'new'
        }

    def get_cumul_by_rubrique(self):
        struct_iga = self.env['hr.payroll.structure'].search(
            [('code', '=', 'payroll_igaser')])
        rules = struct_iga.rule_ids
        # rules = self.env['hr.payroll.structure'].search([('appears_on_payslip','=',True), ('', 'in', struct_iga.ids)])
        codes = [{'code': rule.code, 'libelle': rule.name}
                 for rule in rules if rule.appears_on_payslip == True]
        list_cum_by_rub = []
        for code_d in codes:
            code = code_d['code']
            code_libelle = code_d['libelle']
            dict_cum_by_code = {}
            lines = self.env['hr.payslip.line'].search(
                [('slip_id', 'in', self.slip_ids.ids), ('amount', '>', 0), ('code', '=', code)])
            sum_base_amount = sum(line.base_amount for line in lines)
            sum_total = sum(line.amount for line in lines)
            dict_cum_by_code['code'] = code
            dict_cum_by_code['libelle'] = code_libelle
            dict_cum_by_code['sum_base_amount'] = round(sum_base_amount)
            dict_cum_by_code['sum_total'] = round(sum_total)
            dict_cum_by_code['count_lines'] = len(lines)
            list_cum_by_rub.append(dict_cum_by_code)
        return list_cum_by_rub

    def GenerateTXT(self):
        dict_type_1 = {
            'L_Type_Enreg': 3,
            'N_Identif_Transfert': 14,
            'L_Cat': 2,
            'L_filler': 241
        }

        dict_type_2 = {
            'L_Type_Enreg': 3,
            'N_Num_Affilie ': 7,
            'L_Periode': 6,
            'L_Raison_Sociale': 40,
            'L_Activite': 40,
            'L_Adresse': 120,
            'L_Ville': 20,
            'C_Code_Postal': 6,
            'C_Code_Agence': 2,
            'D_Date_Emission': 8,
            'D_Date_Exig': 8
        }

        dict_type_3 = {
            'L_Type_Enreg': 3,
            'N_Num_Affilie ': 7,
            'L_Periode': 6,
            'N_Num_Assure': 9,
            'L_Nom_Prenom': 60,
            'N_Enfants': 2,
            'N_AF_A_Payer': 6,
            'N_AF_A_Deduire': 6,
            'N_AF_Net_A_Payer': 6,
            'L_filler': 155
        }

        dict_type_4 = {
            'L_Type_Enreg': 3,
            'N_Num_Affilie ': 7,
            'L_Periode': 6,
            'N_Nbr_Salaries': 6,
            'N_T_Enfants': 6,
            'N_T_AF_A_Payer': 12,
            'N_T_AF_A_Deduire': 12,
            'N_T_AF_Net_A_Payer': 12,
            'N_T_Num_Imma': 15,
            'L_filler': 181
        }

        identif_Transfert = '27038922203018'
        num_imma = '000081351100199'
        agence = '13'
        myDateStart = self.date_start
        myMonthStart = myDateStart.strftime("%m")
        mYearStart = myDateStart.strftime("%Y")
        # date end + 10days
        myDateEnd = self.date_end + timedelta(days=10)
        mYearEnd = self.date_end.strftime("%Y")
        myMonthEnd = self.date_end.strftime("%m")
        myDayEnd = myDateEnd.strftime("%d")
        date_sent_cnss = self.date_sent_cnss.strftime(
            "%Y%m%d") if self.date_sent_cnss else ''
        date_exig = myDateEnd.strftime("%Y%m%d")

        with open("./cnss_tst.txt", "w") as file:
            # first element(A00)
            line0 = 'A00' + str(identif_Transfert) + 'A0' + \
                ' '*dict_type_1['L_filler'] + '\n'
            file.write(line0)
            # second element(A01)
            line1 = 'A01' + str(identif_Transfert[0:7]) + str(mYearStart) + str(myMonthStart) + str(self.env.user.company_id.name) + ' '*(dict_type_2['L_Raison_Sociale']-len(self.env.user.company_id.name)) + ' '*dict_type_2['L_Activite'] + str(self.env.user.company_id.street) + ' '*(dict_type_2['L_Adresse']-len(self.env.user.company_id.street)) + str(
                self.env.user.company_id.city) + ' '*(dict_type_2['L_Ville']-len(self.env.user.company_id.city)) + str(self.env.user.company_id.zip) + ' '*(dict_type_2['C_Code_Postal']-len(self.env.user.company_id.zip)) + str(agence) + str(date_sent_cnss) + ' '*(dict_type_2['D_Date_Emission']-len(date_sent_cnss)) + str(date_exig) + '\n'
            file.write(line1)
            # third element(A02)
            nbr_salaries = 0
            total_childrens = 0
            total_amount_af = 0
            total_amount_ded = 0
            total_net_pay = 0
            for payslip in self.slip_ids:
                line_af = self.env['hr.payslip.line'].search(
                    [('slip_id', '=', payslip.id), ('code', '=', 'AF')])
                amount_af = 0
                if line_af:
                    amount_af = line_af.total
                amount_ded = 0
                net_apy = amount_af-amount_ded
                children = str(payslip.employee_id.children)
                amount_af_str = str(int(round(amount_af, 2)*100))[0:6]
                amount_ded_str = str(int(round(amount_ded, 2)*100))[0:6]
                net_apy_str = str(int(round(net_apy, 2)*100))[0:6]
                if len(children) < 2:
                    children = ' ' + children
                if payslip.employee_id.ssnid and payslip.employee_id.ssnid != 'en cours':
                    line2 = 'A02' + str(identif_Transfert[0:7]) + str(mYearStart) + str(myMonthStart) + str(payslip.employee_id.ssnid) + ' '*(dict_type_3['N_Num_Assure']-len(payslip.employee_id.ssnid)) + payslip.employee_id.name + ' '*(dict_type_3['L_Nom_Prenom']-len(payslip.employee_id.name)) + str(
                        children) + ' '*(dict_type_3['N_AF_A_Payer']-len(amount_af_str)) + amount_af_str + ' '*(dict_type_3['N_AF_A_Deduire']-len(amount_ded_str)) + amount_ded_str + ' '*(dict_type_3['N_AF_Net_A_Payer']-len(net_apy_str)) + net_apy_str + ' '*dict_type_3['L_filler'] + '\n'
                    nbr_salaries += 1
                    total_childrens += payslip.employee_id.children
                    total_amount_af += amount_af
                    total_amount_ded += amount_ded
                    total_net_pay += net_apy
                    file.write(line2)
            # third element(A02)
            total_amount_af_str = str(int(round(total_amount_af, 2)*100))[0:6]
            total_amount_ded_str = str(
                int(round(total_amount_ded, 2)*100))[0:6]
            total_net_pay_str = str(int(round(total_net_pay, 2)*100))[0:6]
            # third element(A03)
            line3 = 'A03' + str(identif_Transfert[0:7]) + str(mYearStart) + str(myMonthStart) + '0'*(dict_type_4['N_Nbr_Salaries']-len(str(nbr_salaries))) + str(nbr_salaries) + '0'*(dict_type_4['N_T_Enfants']-len(str(total_childrens))) + str(total_childrens) + ' '*(dict_type_4['N_T_AF_A_Payer']-len(
                total_amount_af_str)) + total_amount_af_str + ' '*(dict_type_4['N_T_AF_A_Deduire']-len(total_amount_ded_str)) + total_amount_ded_str + ' '*(dict_type_4['N_T_AF_Net_A_Payer']-len(total_net_pay_str)) + total_net_pay_str + str(num_imma) + ' '*dict_type_4['L_filler'] + '\n'
            file.write(line3)
            file.close()

            data = open("./cnss_tst.txt", "rb").read()
            encoded = base64.b64encode(data)
            file_name = 'AFFEBDS_' + \
                str(date_sent_cnss) + '_' + str(mYearStart) + \
                str(myMonthStart) + '.txt'
            attach = self.env['ir.attachment'].create(
                {'name': file_name, 'type': 'binary', 'datas': encoded})
            download_url = '/web/content/' + str(attach.id) + '?download=true'

            return {
                'type': 'ir.actions.act_url',
                'url': str(download_url),
                'target': 'new'
            }

    # liste unique des affaires
    def get_list_sites(self):
        list_aff_ids = [slip.contract_id.site_id.id for slip in self.slip_ids]
        list_aff_ids = set(list_aff_ids) - set([False])
        list_obj_aff = self.env['building.site'].browse(list_aff_ids)
        list_obj_aff = sorted(
            list_obj_aff, key=lambda aff: aff.name, reverse=False)
        return list_obj_aff

    def get_payslips(self, site_id):
        contracts = self.env['hr.contract'].search([('site_id', '=', site_id)])
        payslips = self.env['hr.payslip'].search(
            [('contract_id', 'in', contracts.ids), ('id', 'in', self.slip_ids.ids)])
        return payslips

    def done_payslip_run(self):
        self.slip_ids.action_payslip_done()
        journal_id = self.env["account.journal"].search([("name", "=", "Paie")])

        name = f"Lots de paie {self.name}"
        move_dict = {
            'narration': name,
            'ref': self.name,
            'journal_id': journal_id.id,
            'date': self.date_start,
            'move_type_id': self.env["account.move.type"].search([("name", "=", "Autre")], limit=1).id
        }

        grouped_lines = {}
        for slip in self.slip_ids:
            debit_sum = 0.0
            credit_sum = 0.0
            date = slip.date or slip.date_to
            currency = slip.company_id.currency_id

            categ = []

            # for l in slip.details_by_salary_rule_category:
            #     if not l.salary_rule_id.account_debit and l.salary_rule_id.account_credit:
            #         categ.append(l.salary_rule_id.category_id)

            # raise Exception(categ)

            if not any(line.salary_rule_id.account_debit and line.salary_rule_id.account_credit for line in slip.details_by_salary_rule_category):
                raise Exception(slip.id)
                raise UserError(_('Missing Debit Or Credit Account in Salary Rule'))

            for line in slip.details_by_salary_rule_category:
                amount = currency.round(slip.credit_note and -line.total or line.total)
                if currency.is_zero(amount) and not line.name.startswith('ARRONDIS'):
                    continue

                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id
                partenaire_id = line.salary_rule_id.partner_id.id

                rule_id = line.salary_rule_id.id  # Keep salary_rule_id for proper grouping

                # Grouping by (account_id, salary_rule_id)
                if debit_account_id:
                    key = (debit_account_id, rule_id, slip.credit_note)
                    if key not in grouped_lines:
                        grouped_lines[key] = {
                            'name': line.name,
                            # 'partner_id': line._get_partner_id(credit_account=False),
                            'partner_id': partenaire_id,
                            'account_id': debit_account_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': 0.0,
                            'credit': 0.0,
                            'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        }
                    debit = abs(max(amount, 0.0))
                    credit = abs(min(amount, 0.0))
                
                    grouped_lines[key]['debit'] = currency.round(grouped_lines[key]['debit'] + debit)
                    grouped_lines[key]['credit'] = currency.round(grouped_lines[key]['credit'] + credit)
                    debit_sum += debit - credit

                if credit_account_id:
                    key = (credit_account_id, rule_id, slip.credit_note)
                    if key not in grouped_lines:
                        grouped_lines[key] = {
                            'name': line.name,
                            # 'partner_id': line._get_partner_id(credit_account=True),
                            'partner_id': partenaire_id,
                            'account_id': credit_account_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': 0.0,
                            'credit': 0.0,
                            'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        }
                    debit = abs(min(amount, 0.0))
                    credit = abs(max(amount, 0.0))

                    grouped_lines[key]['debit'] = currency.round(grouped_lines[key]['debit'] + debit)
                    grouped_lines[key]['credit'] = currency.round(grouped_lines[key]['credit'] + credit)
                    credit_sum += credit - debit

        # Handle imbalance (ARRONDIS correction)
        amount_diff = abs(debit_sum - credit_sum)
        if currency.compare_amounts(credit_sum, debit_sum) == -1:
            if amount_diff > 0.1:
                pass
                # raise UserError(_('Il y a un déséquilibre dans ce bulletin de %s, merci de vérifier!') % amount_diff)
            for key, data in grouped_lines.items():
                if data['name'] == 'ARRONDIS EN MOINS':
                    data['credit'] += abs(amount_diff)

        elif currency.compare_amounts(debit_sum, credit_sum) == -1:
            if amount_diff > 0.1:
                pass
                # raise UserError(_('Il y a un déséquilibre dans ce bulletin de %s, merci de vérifier!') % amount_diff)
            for key, data in grouped_lines.items():
                if data['name'] == 'ARRONDIS EN PLUS':
                    data['debit'] += abs(amount_diff)

        # Create aggregated journal entry lines
        new_line_ids = [(0, 0, data) for data in grouped_lines.values() if not currency.is_zero(data['credit']) or not currency.is_zero(data['debit'])]

        if not new_line_ids:
            raise UserError(_('Vous ne pouvez pas comptabiliser une pièce vide pour le bulletin de paie, merci de vérifier!'))

        total_debit = sum(entry[2]['debit'] for entry in new_line_ids)
        total_credit = sum(entry[2]['credit'] for entry in new_line_ids)
        total_diff = currency.round(total_credit - total_debit)

        if total_diff != 0:
            rule_plus = self.env["hr.salary.rule"].search([("name", "=", "ARRONDIS EN PLUS")], limit=1)
            rule_less = self.env["hr.salary.rule"].search([("name", "=", "ARRONDIS EN MOINS")], limit=1)
            adjustment = abs(total_diff)
            
            rule_target, field, opposite_field = (
                (rule_less, 'credit', 'debit') if total_diff < 0 else (rule_plus, 'debit', 'credit')
            )
            
            for line in new_line_ids:
                if line[2]["name"] == rule_target.name:
                    line[2][field] += adjustment
                    break
                elif line[2]["name"] == (rule_plus.name if total_diff < 0 else rule_less.name):
                    line[2][opposite_field] -= adjustment
                    break
            else:
                new_line_ids.append((0, 0, {
                    "account_id": rule_target.account_credit.id if total_diff < 0 else rule_target.account_debit.id,
                    "name": rule_target.name,
                    "credit": adjustment if total_diff < 0 else 0,
                    "debit": 0 if total_diff < 0 else adjustment
                }))

        move_dict['line_ids'] = new_line_ids
        move = self.env['account.move'].create(move_dict)
        move.sudo().action_post()
        self.write({'state': 'done', 'move_id': move.id})

    def compute_all_sheet(self):
        i = 0
        for slip in self.slip_ids.filtered(lambda x: not x.credit_note):
            if i == 20:
                return True
            slip.compute_sheet()
            slip.credit_note = True
            i += 1
        return True