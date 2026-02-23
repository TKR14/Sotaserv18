# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
import datetime
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

class building_document(models.TransientModel):
    
    _name = "building.document"
    _description = "Import document"

    attachment_type_id = fields.Many2one('ir.attachment.type', 'Type du Document')
    file = fields.Binary("Fichier à importer",filters='*.*')
    name = fields.Char('Nom du document', size=256, readonly=False)
    start_date = fields.Date(string='Date début des travaux', required=False, readonly=False, index=True, copy=False, default=lambda *a: time.strftime('%Y-%m-%d'))
    stopping_date = fields.Date(string='Date d\'arret des travaux', required=False, readonly=False, index=True, copy=False, default=lambda *a: time.strftime('%Y-%m-%d'))
    restart_date = fields.Date(string='Date de reprise des travaux', required=False, readonly=False, index=True, copy=False, default=lambda *a: time.strftime('%Y-%m-%d'))
    provisional_receipt_date = fields.Date(string='Date de réception provisoire', required=False, readonly=False, index=True, copy=False, default=lambda *a: time.strftime('%Y-%m-%d'))
    ultimately_reception_date = fields.Date(string='Date de reception définitif', required=False, readonly=False, index=True, copy=False, default=lambda *a: time.strftime('%Y-%m-%d'))
    state  = fields.Selection([('open','Ouvert'),('stopping','En arrêt'),('restart','Ouvert'),('provisional_receipt','En réception provisoire'),('ultimately_reception','En réception définitive')], string="status",default='open')
    duration = fields.Float('Durée du projet en jours')
    # with_advance = fields.Boolean('Affaire avec Acompte ?',default=False)
    prc_cd = fields.Float('% CD')
    type_gr  = fields.Selection([('none','Pas de retenue de garantie'),('g_gr','Retenue Globale au début du projet'),('att_gr','Retenue de garantie par décompte'),('inv_gr','Retenue de garantie sur facturation')], string="Type RG",default='none')
    prc_gr = fields.Float('% RG')
    
    @api.model
    def default_get(self, fields):
        if self._context is None: self._context = {}
        res = super(building_document, self).default_get(fields)
        site_id = self._context.get('active_id', [])
        site = self.env['building.site'].browse(site_id)
        res.update(duration=site.duration)
        return res

    @api.onchange('attachment_type_id')
    def onchange_attachment_type_id(self):
        if self.attachment_type_id :
            if self.attachment_type_id.code == 'osdt' :
                self.state = 'open'
            if self.attachment_type_id.code == 'osat' :
                self.state = 'stopping'
            if self.attachment_type_id.code == 'osrt' :
                self.state = 'restart'
            if self.attachment_type_id.code == 'pp' :
                self.state = 'provisional_receipt'            
            if self.attachment_type_id.code == 'pd' :
                self.state = 'ultimately_reception'

    def create_document(self):
        return self.sudo()._create_document()

    def _create_document(self):
        attach_obj = self.env['ir.attachment']
        site_obj = self.env['building.site']
        site_id = self._context.get('active_id',False)
        site = site_obj.browse(site_id)
        if site.state == 'created' :
            if self.attachment_type_id.code != 'osdt' :
                raise UserError(_('Un document de service début des travaux est obligatoire pour l\'ouvrerture de l\'Affaire.'))
            orders = self.env['building.order'].search([('site_id', '=', site.id), ('amendment', '=', False)])
            if not orders :
                raise UserError(_('Affaire sans BP! Merci de verfier.'))
            
            end = self.start_date + relativedelta(days=self.duration)
            end = end.strftime("%Y-%m-%d")

            if self.prc_cd > 0:
                order = orders[0]
                record_account_caution = {
                    'type_caution': 'definitif_caution',
                    'type_caution_str': 'cp',
                    'site_id': site.id,
                    'deposit': order.amount_untaxed * self.prc_cd/100,
                    'caution_provisional_recovery_date': end,
                    'is_readonly': True
                }
                self.env['account.caution'].create(record_account_caution)
            if self.type_gr == 'g_gr':
                order = orders[0]
                record_account_caution = {
                    'type_caution': 'rg_caution',
                    'type_caution_str': 'gr',
                    'site_id': site.id,
                    'deposit': order.amount_untaxed * self.prc_gr/100,
                    'caution_provisional_recovery_date': end,
                    'is_readonly': True
                }
                self.env['account.caution'].create(record_account_caution)

            site.action_open()
            site.write({'date_start':self.start_date,'duration':self.duration, 'prc_cd': self.prc_cd, 'type_gr': self.type_gr , 'prc_gr': self.prc_gr})

            po = self.env["building.order"].search([("site_id", "=", site.id)], limit=1)
            if po:
                po.write({"state": "approved"})
                
        elif site.state == 'open' :
            if self.attachment_type_id.code == 'osat' and self._context.get('button',False) == 'arreter':
                site.action_stopping()
                site.write({'stopping_date':self.stopping_date})
            elif self.attachment_type_id.code == 'pp' and self._context.get('button',False) == 'provisoire':
                site.action_provisional_receipt()
                site.write({'provisional_receipt_date':self.provisional_receipt_date})
            elif self._context.get('button',False) == 'provisoire' :
                raise UserError(_('Un PV provisoire est obligatoire pour la réception provisoire de l\'Affaire.'))
            elif self._context.get('button',False) == 'arreter':
                raise UserError(_('Un document de service d\'arret des travaux est obligatoire pour l\'arret de l\'Affaire.'))
        elif site.state == 'stopping' :
            if self.attachment_type_id.code != 'osrt':
                raise UserError(_('Un document de service de reprise des travaux est obligatoire pour la reprise de l\'Affaire.'))
            site.action_open()
            stopping_date = datetime.strptime(site.stopping_date, '%Y-%m-%d')
            restart_date = datetime.strptime(self.restart_date, '%Y-%m-%d')
            duration = (restart_date-stopping_date).days
            end_date = datetime.strptime(site.date_end, '%Y-%m-%d')
            fin = end_date+relativedelta(days=duration)
            fin = fin.strftime("%Y-%m-%d")
            site.write({'date_end':fin})

        elif site.state == 'provisional_receipt' :
            if self.attachment_type_id.code != 'pd' :
                raise UserError(_('Un PV définitive est obligatoire pour la réception définitive de l\'Affaire.'))
            site.action_ultimately_reception()
            site.write({'ultimately_reception_date':self.ultimately_reception_date})

        attachment_record = {
                               'name': self.name,
                               'datas': self.file,
                               'store_fname': self.name,
                               'res_model': self._context.get('active_model'),
                               'res_id': site_id  ,
                               'attachment_type_id':self.attachment_type_id.id,
                               # 'partner_id':site.partner_id.id                 
                            }
        attach_obj.create(attachment_record)        
        return True