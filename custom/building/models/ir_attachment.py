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
from datetime import datetime
from dateutil.relativedelta import relativedelta


class IrAttachmentType(models.Model):
    _name = "ir.attachment.type"
    
    name = fields.Char('Type Document', size=256, required=False, readonly=False)
    code = fields.Char('Code Document', size=256, required=False, readonly=True)
    document_type = fields.Selection([('osdt', 'Ordre de Service début des Travaux'),
                             ('osrt', 'Ordre de Service reprise des Travaux'),
                             ('osat', 'Ordre de service d\'arret des Travaux'),
                             ('pp', 'PV Provisoire'),
                             ('pd', 'PV Définitif'),
                             ('other', 'Autre')], string='Type du document', required=True, default='other')

    @api.onchange('document_type')
    def onchange_document_type(self):
        if self.document_type :
            self.name = self.document_type.upper()
            self.code = self.document_type
        if self.document_type == 'other' :
            self.name = ''
            self.code = ''
    
    _sql_constraints = [('code_uniq', 'unique(code)','Le code doit etre unique!')]


class IrAttachment(models.Model):
    
    _inherit = "ir.attachment"
    
    attachment_type_id = fields.Many2one('ir.attachment.type', 'Type du document', required=True, default = None)

    def unlink(self):
        # Restrict deletion of attachments for completed receipts.
        for attachment in self:
            if attachment.res_model == 'stock.picking':
                stock_picking = self.env[attachment.res_model].browse(attachment.res_id)
                if stock_picking.state == 'done':
                    raise UserError("Vous ne pouvez pas supprimer une pièce jointe pour une réception effectuée.")
            elif attachment.res_model == 'account.move':
                account_move = self.env[attachment.res_model].browse(attachment.res_id)
                if account_move.state != 'draft':
                    raise UserError("Vous ne pouvez pas supprimer une pièce jointe.")
        return super(IrAttachment, self).unlink()