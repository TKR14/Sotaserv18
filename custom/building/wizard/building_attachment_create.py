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
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
import time

class building_attachment_create(models.TransientModel):
    
    _name = 'building.attachment.create'
    
    # def _get_domain(self):
    #     domain = []
    #     site_id = self._context.get('active_id', [])
    #     orders = self.env['building.order'].search([('state','=','gained'), ('site_id', '=', site_id)])
    #     domain = [('id', 'in' , orders.ids)]
    #     return domain

    name = fields.Char('Nom', size=256, readonly=False)
    location_src_id = fields.Many2one('stock.location', 'Depot Source', required=True)
    location_dest_id = fields.Many2one('stock.location', 'Depot Destination', required=True, domain=[('usage','=','customer')])
    site_id = fields.Many2one('building.site', 'Affaire')
    order_id = fields.Many2one('building.order', 'BP', compute="_compute_order_id", store=True)
    subcontracting_id = fields.Many2one('building.subcontracting', 'Contrat sous-traitance')
    attachment_line_ids = fields.One2many('building.attachment.create.line', 'line_id', 'Décomptes')
    last_attachment = fields.Boolean('Attachement Définitif')
    is_readonly_last_attachment = fields.Boolean(default=False)
    is_invisible_last_attachment = fields.Boolean(default=False)
    start_date = fields.Date('Date de Début', required=True, readonly=False, index=True, copy=False)
    end_date = fields.Date('Date de Fin', required=True, readonly=False, index=True, copy=False)
    date = fields.Date('Date de Création', required=False, readonly=False,index=True, copy=False, default=lambda *a: time.strftime('%Y-%m-%d'))
    partner_id = fields.Many2one('res.partner', 'Fournisseur', domain=[('supplier_rank','>',0)])
    # type_marche  = fields.Selection([('forfait','Au Forfait'), ('metre','Au métré')], string="Type de marché", default='metre')
    type_marche = fields.Selection(related='site_id.type_marche', string="Type de marché", readonly=True, store=True)
    show_opening_attachment = fields.Boolean("Afficher Attachement d'Ouverture", default = False, store = False)
    opening_attachment = fields.Selection([("yes", "Oui"), ("no", "Non")], string="Attachement d'Ouverture", default = False)
    warning = fields.Boolean("Alerter", default = True)
    number = fields.Char(string="Numéro")

    @api.onchange('opening_attachment')
    def _onchange_opening_attachment(self):
        if self.opening_attachment == 'yes':
            self.start_date = self.site_id.date_start
            self.end_date = date(2025, 11, 30)
        else:
            self.start_date = date.today()
            self.end_date = date.today()

    # @api.model
    # def default_get(self, fields):
    #     if self._context is None: self._context = {}
    #     res = super(building_attachment_create, self).default_get(fields)
    #     site_id = self._context.get('active_id', [])
    #     site = self.env['building.site'].browse(site_id)
    #     destination_id = self.env['stock.location'].search([('usage' ,'=' ,'customer')], limit=1)
    #     res.update(location_src_id = site.location_id.id, location_dest_id = destination_id.id, site_id = site_id)
    #     return res

    @api.onchange('attachment_line_ids')
    def onchange_attachment_line_ids(self):
        for rec in self:
            if all((line.cumulative_quantity + line.previous_quantity) == line.price_quantity for line in rec.attachment_line_ids):
                rec.last_attachment = True
                rec.is_readonly_last_attachment = True
            else:
                rec.last_attachment = False
                rec.is_readonly_last_attachment = False

    @api.onchange('opening_attachment')
    def _onchamge_opening_attachment(self):
        for rec in self:
            if rec.opening_attachment == "yes":
                rec.is_invisible_last_attachment = True
            else:
                rec.is_invisible_last_attachment = False
        
    @api.onchange("site_id")
    def onchange_no_site_id(self):
        if not self.site_id:
            definitive_attachments = self.env["building.attachment"].search([
                ("state", "=", "done"),
                ("opening_attachment", "=", False),
                ("definitive_ok", "=", True)
            ])

            opening_attachment = self.env["building.attachment"].search([
                ("open_attachment_state", "!=", "validated_accounting"),
                ("opening_attachment", "=", True),
            ])
            opening_sites = opening_attachment.mapped("site_id")

            open_sites = self.env["building.site"].search([("state", "=", "open")])
            approved_open_site_ids = open_sites.filtered(
                lambda site: any(order.state == "approved" for order in site.order_ids)
            ).ids

            site_ids = list({attachment.site_id.id for attachment in definitive_attachments if attachment.site_id})

            done_attachments = self.env['building.attachment'].search([('state', '!=', 'done'), ('opening_attachment', '=', False)]).mapped('site_id')

            profile_ids = self.env["building.profile.assignment"].search([
                ("user_id", "=", self.env.user.id)
            ])
            user_site_ids = [profile.site_id.id for profile in profile_ids if profile.site_id]

            return {
                "domain": {
                    "site_id": [
                        ("id", "not in", done_attachments.ids),
                        ("id", "not in", site_ids),
                        ("id", "not in", opening_sites.ids),
                        ("id", "in", approved_open_site_ids),
                        ("id", "in", user_site_ids),
                    ]
                }
            }

    @api.depends('site_id')
    def _compute_order_id(self):
        for rec in self:
            approved_orders = rec.site_id.order_ids.filtered(lambda o: o.state == 'approved')
            rec.order_id = approved_orders[:1].id if approved_orders else False

    @api.onchange("site_id")
    def onchange_site_id(self):
        if self.site_id:
            already_open = self.env["building.attachment"].search_count([("site_id", "=", self.site_id.id)])
            if not already_open:
                self.show_opening_attachment = True
            else:
                self.opening_attachment = "no"

            self.location_src_id = self.site_id.warehouse_id.lot_stock_id.id
            dest_loc = self.env['stock.location'].search([('usage', '=', 'customer')])[0]
            self.location_dest_id = dest_loc.id

    @api.onchange('order_id')
    def onchange_order_id(self):
        attachment_lines = []
        if self.order_id:
            order = self.order_id
            attachment = self.env['building.attachment'].search([('type_attachment' ,'=' ,'sale'), ('site_id' ,'=' ,self.site_id.id), ('order_id' ,'=' , order.id)], order='id desc', limit=1)
            if attachment :
                for line in order.order_line.sorted(key=lambda l: l.sequence):
                    if not line.display_type:
                        attachment_line = self.env['building.attachment.line'].search([('attachment_id' ,'=' ,attachment.id), ('line_dqe_id' ,'=' ,line.id)], order='id desc', limit=1)
                        if attachment_line :
                            attachment_line_record = {
                                'product_id': line.product_id.id if line.product_id else False,
                                'product_uom_id': line.product_uom.id,
                                'order_line_id':line.id,
                                'quantity' : 0,
                                'cumulative_quantity' : 0,
                                'current_quantity' : 0,
                                'previous_quantity' :  attachment_line.cumulative_quantity,
                                # 'chapter':line.price_number,
                                'name':line.name,
                                'sequence': line.sequence,
                            }
                            attachment_lines.append((0, 0, attachment_line_record))
                        else :
                            attachment_line = self.env['building.attachment.line'].search([('line_dqe_id','=',line.id)], order='id desc', limit=1)
                            attachment_line_record = {
                                'product_id': line.product_id.id if line.product_id else False,
                                'product_uom_id': line.product_uom.id,
                                'order_line_id':line.id,
                                'quantity' : 0,
                                'cumulative_quantity' : 0,
                                'current_quantity' : 0,
                                'previous_quantity' :  attachment_line.cumulative_quantity,
                                # 'chapter':line.price_number,
                                'name':line.name,
                                'sequence': line.sequence,
                            }
                            attachment_lines.append((0, 0, attachment_line_record))
                    else:
                        attachment_lines.append((0, 0, {'name': line.name, 'display_type':line.display_type, 'sequence': line.sequence}))
            else :
                for line in order.order_line.sorted(key=lambda l: l.sequence):
                    if not line.display_type:
                        attachment_line_record = {
                            'product_id': line.product_id.id if line.product_id else False,
                            'product_uom_id': line.product_uom.id,
                            'order_line_id':line.id,
                            'quantity' : 0,
                            'cumulative_quantity' : 0,
                            'current_quantity' : 0,
                            'previous_quantity' :  0,
                            # 'chapter':line.price_number,
                            'name':line.name,
                            'sequence': line.sequence,
                        }
                        attachment_lines.append((0, 0, attachment_line_record))
                    else:
                        attachment_lines.append((0, 0, {'name': line.name, 'display_type':line.display_type, 'sequence': line.sequence}))
            self.attachment_line_ids = attachment_lines
            self.site_id = order.site_id.id

    @api.onchange('subcontracting_id')
    def onchange_subcontracting_id(self):
        attachment_lines = []
        if self.subcontracting_id:
            order = self.subcontracting_id
            attachment = self.env['building.attachment'].search([('type_attachment', '=', 'purchase'), ('site_id', '=', order.site_id.id), ('subcontracting_id', '=', self.subcontracting_id.id)], order='id desc', limit=1)
            if attachment :
                for line in order.order_line:
                    attachment_line = self.env['building.attachment.line'].search([('attachment_id', '=', attachment.id), ('line_subcontracting_id', '=', line.id)], order='id desc', limit=1)
                    if attachment_line :
                        attachment_line_record = {
                            'product_id': line.product_id.id if line.product_id else False,
                            'product_uom_id': line.product_uom.id,
                            'subcontracting_line_id':line.id,
                            'quantity' : 0,
                            'cumulative_quantity' : attachment_line.cumulative_quantity,
                            'current_quantity' : 0,
                            'previous_quantity' :  attachment_line.cumulative_quantity,
                            'chapter':line.chapter,
                            'name':line.name,
                        }
                        attachment_lines.append((0, 0, attachment_line))
                    else :
                        attachment_line = self.env['building.attachment.line'].search([('line_subcontracting_id', '=', line.id)], order='id desc', limit=1)
                        attachment_line_record = {
                            'product_id': line.product_id.id if line.product_id else False,
                            'product_uom_id': line.product_uom.id,
                            'subcontracting_line_id':line.id,
                            'quantity' : 0,
                            'cumulative_quantity' : attachment_line.cumulative_quantity,
                            'current_quantity' : 0,
                            'previous_quantity' :  attachment_line.cumulative_quantity,
                            'chapter':line.name,
                            'name':line.name,
                        }
                        attachment_lines.append(attachment_line_record)
            else :
                for line in order.order_line:
                    # if not line.display_type:
                    attachment_line = {
                        'product_id': line.product_id.id if line.product_id else False,
                        'product_uom_id': line.product_uom.id,
                        'subcontracting_line_id':line.id,
                        'quantity' : line.quantity,
                        'cumulative_quantity' : 0,
                        'current_quantity' : 0,
                        'previous_quantity' :  0,
                        'chapter':line.chapter,
                        'name':line.name,
                    }
                    attachment_lines.append((0, 0, attachment_line))
            self.attachment_line_ids = attachment_lines
            self.site_id = order.site_id.id
    
    @api.onchange('partner_id', 'site_id')
    def onchange_partner_id(self):
        if self.partner_id:
            subcontractings = self.env['building.subcontracting'].search([('partner_id','=', self.partner_id.id),('state','=','approved'),('site_id','=', self.site_id.id)])
            domain = {'subcontracting_id':  [('id', 'in', subcontractings.ids)]}
            return {'domain': domain}
        return {'domain': {'subcontracting_id':  [('id', 'in', [])]}}

    # def warning_switch(self):
    #     self.warning = not self.warning
    #     return {
    #         'name': 'Création des Attachements Client',
    #         'view_mode': 'form',
    #         'view_id': False,
    #         'res_model': self._name,
    #         'domain': [],
    #         'context': dict(self._context, active_ids=self.ids),
    #         'type': 'ir.actions.act_window',
    #         'target': 'new',
    #         'res_id': self.id,
    #     }

    @api.onchange("site_id", "opening_attachment")
    def onchange_site_id_number(self):
        count = self.env['building.attachment'].search_count([
            ('site_id', '=', self.site_id.id),
        ]) + 1

        if self.opening_attachment == "yes":
            if self.site_id.last_attachment_number:
                last_number = int(self.site_id.last_attachment_number)
                number = f"{self.site_id.number or ''}-{str(last_number).zfill(4)}"
            else:
                number = f"{self.site_id.number or ''}-{str(count).zfill(4)}"
        else:
            if self.site_id.last_attachment_number:
                last_number = int(self.site_id.last_attachment_number)
                number = f"{self.site_id.number or ''}-{str(last_number + count).zfill(4)}"
            else:
                number = f"{self.site_id.number or ''}-{str(count).zfill(4)}"

        self.number = number

    def create_attachment(self):
        type_attachment = self._context.get('type_attachment', False)
        # site_id = self._context.get('active_id', False)
        # site = self.env['building.site'].browse(site_id)
        # ds = self.start_date
        # de = self.end_date
        # delay = (de - ds).days

        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError(_("La date de début d'attachement doit être postérieure à la date de fin d'attachement."))
            
            last_entry = self.env['building.attachment'].search([('site_id', '=', record.site_id.id)], order='id desc', limit=1)
            if last_entry and last_entry.end_date:
                if record.start_date <= last_entry.end_date:
                    last_date_formatted = last_entry.end_date.strftime('%d-%m-%Y')
                    raise ValidationError(_(
                        "La date de début d'attachement doit être postérieure à la date du dernier attachement ({last_date})."
                    ).format(last_date=last_date_formatted))

            building_order = self.env['building.order'].search([('site_id', '=', record.site_id.id)], order='id desc', limit=1)
            if building_order and building_order.create_date:
                if record.start_date < building_order.create_date.date():
                    raise ValidationError(_("La date de début d'attachement doit être postérieure à la date du BDP."))

        attachment_lines = []
        record_attachment = {
            'name': self.name,
            'number': self.number,
            'site_id': self.site_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'date': self.date,
            'state': 'draft',
            'type_attachment': type_attachment,
            'definitive_ok': self.last_attachment,
            'is_readonly_last_attachment': self.is_readonly_last_attachment,
            'delay_attachment': self.site_id.duration,
            'location_src_id': self.location_src_id.id,
            'location_dest_id': self.location_dest_id.id,
            'type_marche': self.site_id.type_marche,
        }
        if self.opening_attachment == "yes":
            record_attachment["opening_attachment"] = True

        if self.last_attachment:
            record_attachment['definitive_ok'] = True
            if self.last_attachment :
                self.site_id.write({'last_attachment':True})

        if type_attachment == 'sale':
            record_attachment['partner_id'] = self.site_id.partner_id.id
            record_attachment['customer_id'] = self.site_id.partner_id.id
            record_attachment['order_id'] = self.order_id.id
        if type_attachment == 'purchase':
            record_attachment['partner_id'] = self.partner_id.id
            record_attachment['supplier_id'] = self.partner_id.id
            record_attachment['subcontracting_id'] = self.subcontracting_id.id
            # if self.last_attachment :
            #     self.subcontracting_id.write({'definitive_ok':True})

        # attachment_id = self.env['building.attachment'].create(record_attachment)
        for line in self.attachment_line_ids :
            if not line.display_type:
                record_attachment_line = {
                    # 'attachment_id' :attachment_id.id,
                    'product_id' :line.product_id.id if line.product_id else False,
                    'product_uom_id' :line.order_line_id.product_uom.id,
                    'price_quantity' :line.price_quantity,
                    'qty' :line.order_line_id.quantity,
                    'cumulative_quantity':line.cumulative_quantity,
                    'current_quantity':line.current_quantity,
                    'previous_quantity':line.previous_quantity,
                    'name':line.name,
                    'tax_id': self.env['account.fiscal.position'].map_tax(line.order_line_id.tax_id),
                    # 'chapter': line.order_line_id.price_number,
                    'display_type': line.display_type,
                    'order_line_id': line.order_line_id.id,
                    'sequence': line.sequence
                }
                if type_attachment == 'sale' :
                    record_attachment_line['line_dqe_id'] = line.order_line_id.id
                    record_attachment_line['price_unit'] = line.order_line_id.price_unit
                    # record_attachment_line['chapter'] = line.chapter
                if type_attachment == 'purchase' :
                    record_attachment_line['line_subcontracting_id'] = line.subcontracting_line_id.id
                    record_attachment_line['price_unit'] = line.subcontracting_line_id.price_unit
                    # record_attachment_line['chapter'] = line.chapter
                # self.env['building.attachment.line'].create(record_attachment_line)
                attachment_lines.append((0, 0, record_attachment_line))
            else:
                record_attachment_line = {
                                            # 'attachment_id' :attachment_id.id,
                                            'name':line.name,
                                            'display_type': line.display_type,
                                            'price_unit': 0,
                                            'order_line_id': line.order_line_id.id,
                                            'sequence': line.sequence
                                        }
                attachment_lines.append((0, 0, record_attachment_line))
                # raise UserError(str(record_attachment_line))
                # self.env['building.attachment.line'].create(record_attachment_line)
        record_attachment['line_ids'] = attachment_lines
        self.env['building.attachment'].create(record_attachment)
        return True
                

class building_attachment_create_line(models.TransientModel):
    _name = 'building.attachment.create.line'

    line_id = fields.Many2one('building.attachment.create', 'Attachement')
    product_id = fields.Many2one('product.product', 'Product')
    product_uom_id = fields.Many2one('uom.uom', 'UDM')
    percentage_completion = fields.Float('% Avance', compute="_compute_percentage_completion")
    quantity = fields.Float('Quantity')
    cumulative_quantity = fields.Float('Qté cumulée')
    current_quantity = fields.Float('Qté courant')
    previous_quantity = fields.Float('Qté Préc')
    order_line_id = fields.Many2one('building.order.line', 'Details BP')
    price_quantity = fields.Float('Qté BDP', related="order_line_id.quantity")
    subcontracting_line_id = fields.Many2one('building.subcontracting.line', 'Details Contrat')
    # chapter = fields.Char('Code', size=2048, required=False, readonly=False)
    name = fields.Char('Produit', size=4096, required=False, readonly=False)
    display_type = fields.Selection([
        ('line_chapter', "Chapitre"),
        ('line_sub_chapter', "Sous Chapitre"),
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    sequence = fields.Integer(string='Sequence', default=10)
    is_readonly_cumulative_quantity = fields.Boolean('Readonly', default=False, compute="_compute_is_readonly_cumulative_quantity")

    def _compute_is_readonly_cumulative_quantity(self):
        for rec in self:
            rec.is_readonly_cumulative_quantity = rec.previous_quantity == rec.price_quantity

    @api.depends('cumulative_quantity', 'price_quantity')
    def _compute_percentage_completion(self):
        for rec in self:
            if rec.price_quantity:
                rec.percentage_completion = (rec.cumulative_quantity / rec.price_quantity) * 100
            else:
                rec.percentage_completion = 0

    @api.onchange('cumulative_quantity')
    def _onchange_cumulative_quantity(self):
        for rec in self:
            if rec.cumulative_quantity < rec.previous_quantity:
                raise ValidationError(f"La quantité cumulée saisie est inférieure à la quantité décomptes précédents.")

            if rec.cumulative_quantity > rec.order_line_id.quantity and rec.line_id.site_id.type_marche == "forfait":
                raise ValidationError(f"Produit: {rec.name}\nLa quantité cumulée saisie {rec.cumulative_quantity:.2f} dépasse celle définie sur le BP {rec.order_line_id.quantity:.2f}.")

    # @api.onchange('cumulative_quantity')
    # def onchange_line_cumulative_quantity(self):
    #     if self.line_id.warning:
    #         warning = False

    #         if self.cumulative_quantity < self.previous_quantity:
    #             warning = True
    #             warning_message = f"La quantité cumulée saisie est inférieure à la quantité décomptes précédents."

    #         if self.cumulative_quantity > self.order_line_id.quantity:
    #             if warning:
    #                 warning_message += f"\n\n"
    #             warning = True
    #             warning_message = f"Produit: {self.name}\nLa quantité cumulée saisie {self.cumulative_quantity:.2f} dépasse celle définie sur le BP {self.order_line_id.quantity:.2f}."

    #         if warning:
    #             return { 
    #                 'warning': {
    #                     'title': "Attention",
    #                     'message': _(warning_message),
    #                 }
    #             }

    @api.onchange('current_quantity', 'previous_quantity')
    def onchange_current_quantity(self):
        self.cumulative_quantity = self.current_quantity + self.previous_quantity

    @api.onchange('cumulative_quantity', 'previous_quantity')
    def onchange_cumulative_quantity(self):
        self.current_quantity = self.cumulative_quantity - self.previous_quantity