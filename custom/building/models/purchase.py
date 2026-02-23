from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_repr

import time
import json
from lxml import etree
import xlsxwriter
import base64
import os


MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')

class purchase_order(models.Model):
    
    _inherit = 'purchase.order'
    _description = "Achats"

    site_id =  fields.Many2one('building.site', string='Affaire')
    dqe_id =  fields.Many2one('building.order', string='BP')
    # purchase_workforce = fields.Boolean('Achat Main-d’œuvre')
    # purchase_material = fields.Boolean('Achat Fourniture')
    # purchase_equipment = fields.Boolean('Achat Matériel')
    # purchase_service = fields.Boolean('Achat de Service')
    purchase_type = fields.Selection([('material','Matérieaux'), ('conso','Consommables'), ('equipment','Matériels'), ('mini_equipment','Petit Matériels'), ('diesel','Gasoil'), ('service','Prestation de Service'), ('load','Autres Charges')], string="Type d'achat", default='')
    vehicle_id =  fields.Many2one('fleet.vehicle', string='STE')

    # def print_detail(self):
    #     return self.env.ref('purchase_plus.detail_action').report_action(self)

    def _compute_qty_reserved_by_purchase_request(self, site_id):
        requests = self.env['purchase.request'].search([('site_id', '=', site_id), ('state', '=', 'done')])
        dict_qty_reserved_by_product = {}
        for request in requests:
            for line in request.line_ids:
                if line.product_id.id not in dict_qty_reserved_by_product:
                    dict_qty_reserved_by_product[line.product_id.id] = 0
                dict_qty_reserved_by_product[line.product_id.id] += line.product_qty
        return dict_qty_reserved_by_product

    @api.model
    def create(self, vals):
        if ('site_id' in vals) and vals['site_id'] :
            site = order = self.env['building.site'].browse(vals['site_id'])
            order = self.env['building.order'].search([('site_id', '=' , vals['site_id']), ('amendment', '=' , False)], limit=1)
            if vals.get('site_id',  False) and vals.get('order_line', []) and site.is_with_purchase_need:
                for l in vals.get('order_line', []):
                    product = self.env['product.product'].search([('id', '=', l[2]['product_id'])])[0]
                    need_line = self.env['building.purchase.need.line'].search([('product_id', '=', l[2]['product_id']), ('site_id', '=', vals['site_id']), ('state', '=', 'approuved')])
                    if product.type == 'service':
                        need_line = self.env['building.purchase.need.service.provision'].search([('product_id', '=', l[2]['product_id']), ('site_id', '=', vals['site_id']), ('state', '=', 'approuved')])
                    if need_line:
                        need_line = need_line[0]
                        if product.type == 'service':
                            if l[2]['price_unit']*l[2]['product_qty']  > need_line.price_subtotal_remaining:
                                raise UserError(_('Attention!: Il y a un depassement du budget de l''article %s')%product.name)
                        else:
                            if l[2]['product_qty'] > need_line.quantity_remaining:
                                raise UserError(_('Attention!: Il y a un depassement de quantité pour l''article %s')%product.name)
                    else:
                        raise UserError(_('Attention!: Il y a pas un besoin defini pour l''article %s')%product.name)

        company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
        # Ensures default picking type and currency are taken from the right company.
        self_comp = self.with_company(company_id)
        if vals.get('name', 'New') == 'New':
            # seq_date = None
            # if 'date_order' in vals:
            #     seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            # vals['name'] = self_comp.env['ir.sequence'].next_by_code('purchase.order', sequence_date=seq_date) or '/'
            # Prevent assigning sequence on creation, save it for purchase state
            vals["name"] = self_comp.env["ir.sequence"].next_by_code("purchase.order.sequence.price.request")
        vals, partner_vals = self._write_partner_values(vals)
        res = super(purchase_order, self_comp).create(vals)
        if partner_vals:
            res.sudo().write(partner_vals)  # Because the purchase user doesn't have write on `res.partner`
        return res

    # def write(self, vals):
    #     print (vals)
    #     purchase = self
    #     if purchase.site_id and purchase.site_id.is_with_purchase_need:
    #         order = self.env['building.order'].search([('site_id', '=' , purchase.site_id.id), ('amendment', '=' , False)], limit=1)
    #         for line in purchase.order_line :
    #             need_line = self.env['building.purchase.need.line'].search([('product_id', '=', line.product_id.id), ('site_id', '=', purchase.site_id.id), ('state', '=', 'approuved')])
    #             print (line.id)
    #             print (line.product_id)
    #             if line.product_id.type == 'service':
    #                 need_line = self.env['building.purchase.need.service.provision'].search([('product_id', '=', line.product_id.id), ('site_id', '=', purchase.site_id.id), ('state', '=', 'approuved')])
    #             if need_line:
    #                 need_line = need_line[0]
    #                 if line.product_id.type == 'service':
    #                     print ("price_subtotal, need_line.price_subtotal_remaining",line.price_subtotal, need_line.price_subtotal_remaining)
    #                     if line.price_subtotal > need_line.price_subtotal_remaining:
    #                         raise UserError(_('Attention!: Il y a un depassement du budget de l''article %s')%line.product_id.name)
    #                 else:
    #                     if line.product_qty > need_line.quantity_remaining:
    #                         raise UserError(_('Attention!: Il y a un depassement de quantité pour l''article %s')%line.product_id.name)
    #             else:
    #                 raise UserError(_('Attention!: Il y a pas un besoin defini pour l''article %s')%line.product_id.name)
    #     res  = super(purchase_order, self).write(vals)        
    #     return res
    
    def write(self, vals):
        purchase = self
        if purchase.site_id and purchase.site_id.is_with_purchase_need and vals.get('order_line', []):
            order = self.env['building.order'].search([('site_id', '=' , purchase.site_id.id), ('amendment', '=' , False)], limit=1)
            for l in vals.get('order_line', []):
                if l[0] == 4 and l[2]:
                    order_line = self.env['purchase.order.line'].browse(l[1])
                    need_line = self.env['building.purchase.need.line'].search([('product_id', '=', order_line.product_id.id), ('site_id', '=', purchase.site_id.id), ('state', '=', 'approuved')])
                    if order_line.product_id.type == 'service':
                        need_line = self.env['building.purchase.need.service.provision'].search([('product_id', '=', order_line.product_id.id), ('site_id', '=', purchase.site_id.id), ('state', '=', 'approuved')])
                    if need_line:
                        need_line = need_line[0]
                        if order_line.product_id.type == 'service':
                            price_subtotal = order_line.price_subtotal
                            if 'price_unit' in l[2] and 'product_qty' not in l[2]:
                                price_subtotal = l[2]['price_unit']*order_line.product_qty
                            if 'price_unit' not in l[2] and 'product_qty' in l[2]:
                                price_subtotal = l[2]['product_qty']*order_line.price_unit
                            if 'price_unit' in l[2] and 'product_qty' in l[2]:
                                price_subtotal = l[2]['price_unit']*l[2]['product_qty']
                            if price_subtotal  > need_line.price_subtotal_remaining:
                                raise UserError(_('Attention!: Il y a un depassement du budget de l''article %s')%order_line.product_id.name)
                        else:
                            if 'product_qty' in l[2] and l[2]['product_qty'] > need_line.quantity_remaining:
                                raise UserError(_('Attention!: Il y a un depassement de quantité pour l''article %s')%order_line.product_id.name)
                    else:
                        raise UserError(_('Attention!: Il y a pas un besoin defini pour l''article %s')%order_line.product_id.name)
                if l[0] == 0 and l[2]:
                    product = self.env['product.product'].search([('id', '=', l[2]['product_id'])])[0]
                    need_line = self.env['building.purchase.need.line'].search([('product_id', '=', l[2]['product_id']), ('site_id', '=', purchase.site_id.id), ('state', '=', 'approuved')])
                    if product.type == 'service':
                        need_line = self.env['building.purchase.need.service.provision'].search([('product_id', '=', l[2]['product_id']), ('site_id', '=', purchase.site_id.id), ('state', '=', 'approuved')])
                    if need_line:
                        need_line = need_line[0]
                        if product.type == 'service':
                            if l[2]['price_unit']*l[2]['product_qty']  > need_line.price_subtotal_remaining:
                                raise UserError(_('Attention!: Il y a un depassement du budget de l''article %s')%product.name)
                        else:
                            if l[2]['product_qty'] > need_line.quantity_remaining:
                                raise UserError(_('Attention!: Il y a un depassement de quantité pour l''article %s')%product.name)
                    else:
                        raise UserError(_('Attention!: Il y a pas un besoin defini pour l''article %s')%product.name)
        res  = super(purchase_order, self).write(vals)        
        return res

    @api.onchange('site_id')
    def _onchange_site_id(self):
        if self.site_id:
            # self.partner_id = self.site_id.partner_id.id
            for line in self.order_line:
                line.product_description_variants = self.site_id.name

    def _prepare_picking(self):
        result = super(purchase_order, self)._prepare_picking()
        if self.site_id:
            result['site_id'] = self.site_id.id
        if self.site_id:
            result['vehicle_id'] = self.vehicle_id.id
        return result

    def _get_destination_location(self):
        res = super(purchase_order, self)._get_destination_location()
        if self.site_id:
            return self.site_id.warehouse_id.lot_stock_id.id
        return res

    def _prepare_invoice(self):
        invoice_vals = super(purchase_order, self)._prepare_invoice()
        if self.site_id:
            invoice_vals['site_id'] = self.site_id.id
        if self.vehicle_id:
            invoice_vals['vehicle_id'] = self.vehicle_id.id
        is_service_provision = False
        for line in self:
            if line.product_id.type == 'service':
                invoice_vals['invoice_service'] = True
                return invoice_vals
        return invoice_vals

class purchase_order_line(models.Model):

    _inherit = 'purchase.order.line'
    _description = "Lignes Achat"

    order_id = fields.Many2one('purchase.order', ondelete='cascade')

    price_line_id =  fields.Many2one('building.price.calculation.line', string='ligne etude')

    # def _prepare_stock_moves(self, picking):
    #     moves = super(purchase_order, self)._prepare_stock_moves(picking)
    #     if self.site_id:
    #         for mv_dict in moves:
    #             mv['site_id'] = self.site_id.id
    #     return moves

    # def _prepare_account_move_line(self, move=False):
    #     res = super(purchase_order_line, self)._prepare_account_move_line()
    #     if self.product_id.type == 'service':
    #         move.invoice_service = True
    #     return res

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        # Appeler la méthode de vérification des champs vides
        self.order_id._check_empty_fields()

    def show_detail(self):
        self.ensure_one()
        purchase_order = self.order_id
        if purchase_order.state_2 != "draft" or self.env.user.has_group('building_plus.group_opc'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Détails de la ligne de bon de commande',
                'view_mode': 'form',
                'res_model': 'purchase.order.line',
                'target': 'new',
                'context': {
                    'default_purchase_order_line_id': self.id,
                    'create': False,
                },
                "res_id": self.id,
                "views": [
                    (self.env.ref("purchase_plus.purchase_order_line_view_form_details_readonly").id, "form"),
                ],
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Détails de la ligne de bon de commande',
                'view_mode': 'form',
                'res_model': 'purchase.order.line',
                'target': 'new',
                'context': {
                    'default_purchase_order_line_id': self.id,
                    'create': False,
                },
                "res_id": self.id,
                "views": [
                    (self.env.ref("purchase_plus.purchase_order_line_view_form_details").id, "form"),
                ],
            }


class building_purchase_cheak(models.Model):

    _name = 'building.purchase.cheak'
    _description = "gestion des chéques"

    name =  fields.Char(string='Numéro de chéque')
    partner_id = fields.Many2one('res.partner', string='Fournisseur')
    invoice_id = fields.Many2one('account.invoice', string='Facture')
    site_id = fields.Many2one('building.site', string='Affaire')
    amount = fields.Float(string='Montant de la chéque')
    state = fields.Selection([('draft', 'Brouillon'),('sent', 'déposé'),('payed', 'Payé'),], 'Statut',default='draft')


    def action_sent(self):
        self.state = 'sent'

    def action_payed(self):
        self.state = 'payed'

class building_purchase_need(models.Model):
    _name = 'building.purchase.need'
    _description = "Besoins des affaires"

    is_besoin_updated = fields.Boolean(string="Besoin Updated", default=False)

    def update_fuel_tab(self):
        template = self.search([("is_template", "=", True)])
        template_fuel_ids = template.fuel_ids.filtered(lambda l: l.display_type != "line_section")
        needs = self.search([("is_template", "!=", True)])
        
        for need in needs:
            lines_values = [(6, 0, [])]
            for line in template_fuel_ids:
                line_vals = line.section_id.copy_data()[0]
                line_vals.update({
                    "need_id": need.id,
                    "sequence_number": False,
                    "line_number": False,
                    "section_id": False,
                    "identification_number": False,
                    "sequence_number_parent": 0,
                    "line_number_parent": 0,
                    "identification_number_parent": 0,
                    "template_line_id": line.section_id.id,
                })
                lines_values.append((0, 0, line_vals))

                line_vals = line.copy_data()[0]
                line_vals.update({
                    "need_id": need.id,
                    "sequence_number": False,
                    "line_number": False,
                    "section_id": False,
                    "identification_number": False,
                    "sequence_number_parent": 0,
                    "line_number_parent": 0,
                    "identification_number_parent": 0,
                    "template_line_id": line.id,
                })
                lines_values.append((0, 0, line_vals))
            need.update({"fuel_ids": lines_values})

    def update_equipment_tab(self):
        self.ensure_one()

        template = self.search([("is_template", "=", True)], limit=1)
        template_lines = template.equipment_ids.filtered(
            lambda l: l.display_type != "line_section"
        )

        lines_values = [(6, 0, [])]
        added_sections = set()

        for line in template_lines:
            section = line.section_id
            if section and section.id not in added_sections:
                section_vals = section.copy_data()[0]
                section_vals.update({
                    "need_id": self.id,
                    "sequence_number": False,
                    "line_number": False,
                    "section_id": False,
                    "identification_number": False,
                    "sequence_number_parent": 0,
                    "line_number_parent": 0,
                    "identification_number_parent": 0,
                    "template_line_id": section.id,
                })
                lines_values.append((0, 0, section_vals))
                added_sections.add(section.id)

            line_vals = line.copy_data()[0]
            line_vals.update({
                "need_id": self.id,
                "sequence_number": False,
                "line_number": False,
                "section_id": False,
                "identification_number": False,
                "sequence_number_parent": 0,
                "line_number_parent": 0,
                "identification_number_parent": 0,
                "template_line_id": line.id,
            })
            lines_values.append((0, 0, line_vals))

        self.write({"equipment_ids": lines_values})

    def update_small_equipment_tab(self):
        self.ensure_one()

        template = self.search([("is_template", "=", True)], limit=1)
        template_lines = template.small_equipment_ids.filtered(
            lambda l: l.display_type != "line_section"
        )

        lines_values = [(6, 0, [])]
        added_sections = set()

        for line in template_lines:
            section = line.section_id

            if section and section.id not in added_sections:
                section_vals = section.copy_data()[0]
                section_vals.update({
                    "need_id": self.id,
                    "sequence_number": False,
                    "line_number": False,
                    "section_id": False,
                    "identification_number": False,
                    "sequence_number_parent": 0,
                    "line_number_parent": 0,
                    "identification_number_parent": 0,
                    "template_line_id": section.id,
                })
                lines_values.append((0, 0, section_vals))
                added_sections.add(section.id)

            line_vals = line.copy_data()[0]
            line_vals.update({
                "need_id": self.id,
                "sequence_number": False,
                "line_number": False,
                "section_id": False,
                "identification_number": False,
                "sequence_number_parent": 0,
                "line_number_parent": 0,
                "identification_number_parent": 0,
                "template_line_id": line.id,
            })
            lines_values.append((0, 0, line_vals))

        self.write({"small_equipment_ids": lines_values})

    def action_update_besoin_lines(self):
        self.ensure_one()
        self.update_equipment_tab()
        self.update_small_equipment_tab()
        self.is_besoin_updated = True

    def export_excel(self):
        PATH = "/mnt/extra-addons/building_plus"
        path = PATH + f"/{self.site_id.code}.xlsx"
        workbook = xlsxwriter.Workbook(path)

        ressource_humain_ids = self.ressource_humain_ids
        line_ids = self.line_ids
        service_provision_ids = self.service_provision_ids
        mini_equipment_ids = self.mini_equipment_ids
        equipment_ids = self.equipment_ids
        small_equipment_ids = self.small_equipment_ids

        sheets = [
            (
                "Ressource Humaines",
                ressource_humain_ids.sorted(lambda l: (l.sequence_number_parent, l.line_number_parent)),
                {
                    "Catégorie": "type_resource",
                    "Profil": "profile_id",
                    "Poste": "job_id",
                    "Nombre": "quantity",
                    "Volume": "duree_j",
                    "UDM": "uom_id",
                    "Px. Unit.": "price_unit",
                    "Prix Total": "price_subtotal",
                }
            ),
            (
                "Fournitures",
                line_ids.sorted(lambda l: (l.sequence_number_parent, l.line_number_parent)),
                {
                    "Type Produit": "type_produit",
                    "Article": "product_id",
                    "Description": "name",
                    "Quantité": "quantity",
                    "UDM": "uom_id",
                    "Prix Unitaire": "price_unit",
                    "Prix Total": "price_subtotal",
                }
            ),
            (
                "Prestation de service",
                service_provision_ids.sorted(lambda l: (l.sequence_number_parent, l.line_number_parent)),
                {
                    "Article": "product_id",
                    "Description": "name",
                    "Quantité": "quantity",
                    "UDM": "uom_id",
                    "Prix Unitaire": "price_unit",
                    "Prix Total": "price_subtotal",
                }
            ),
            (
                "Outillages",
                mini_equipment_ids.sorted(lambda l: (l.sequence_number_parent, l.line_number_parent)),
                {
                    "Catégorie": "category_id",
                    "Outillage": "product_id",
                    "Description": "name",
                    "Quantité": "quantity",
                    "UDM": "uom_id",
                    "Prix Unitaire": "price_unit",
                    "Prix Total": "price_subtotal",
                }
            ),
            (
                "Matériels",
                equipment_ids.sorted(lambda l: (l.sequence_number_parent, l.line_number_parent)),
                {
                    "Matériel": "equipment_category_id",
                    "Description": "name",
                    "Quantité": "quantity",
                    "Durée": "duree_j",
                    "UDM": "uom_id",
                    "Prix Unitaire": "price_unit",
                    "Prix Total": "price_subtotal",
                }
            ),
            (
                "Petit Matériels",
                small_equipment_ids.sorted(lambda l: (l.sequence_number_parent, l.line_number_parent)),
                {
                    "Petit matériel": "equipment_id",
                    "Description": "name",
                    "Quantité": "quantity",
                    "Durée": "duree",
                    "UDM": "uom_id",
                    "Prix Unitaire": "price_unit",
                    "Prix Total": "price_subtotal",
                }
            ),
        ]

        header_format = workbook.add_format({
            "border": 1,
            "bg_color": "#D9D9D9",
            "border_color": "#666666",
            "bold": True,
        })
        normal_format = workbook.add_format({
            "border": 1,
            "border_color": "#666666",
        })
        section_format = workbook.add_format({
            "border": 1,
            "bg_color": "F2F2F2",
            "border_color": "#666666",
            "bold": True,
        })

        for title, lines, columns in sheets:
            sheet = workbook.add_worksheet(title)
            # HEADER
            for i, column in enumerate(columns.keys()):
                sheet.write(0, i, column, header_format)
            # LINES
            for i, line in enumerate(lines, 1):
                if not line.display_type:
                    for j, column in enumerate(columns.values()):
                        value = line[column]
                        field_metadata = line.fields_get([column]).get(column)
                        if field_metadata and field_metadata.get("type") == "selection":                            
                            value = dict(field_metadata["selection"]).get(value)
                        elif column.endswith("_id"):
                            value = line[column]["name"]
                        sheet.write(i, j, value or "", normal_format)
                else:
                    sheet.merge_range(i, 0, i, len(columns.values()) - 1, line.name, section_format)
            # sheet.autofit()
        workbook.close()

        data = open(path, "rb").read()
        encoded = base64.b64encode(data)
        file_name = self.site_id.code
        attachment = self.env["ir.attachment"].create({
            "name": file_name,
            "datas": encoded,
        })
        action = {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "new"
        }
        os.remove(path)
        return action

    def dev(self):
        def _new_line(line, need_id):
            origin_id = f"{line._name},{line.template_line_id.id}"
            template_line_id = self.env["building.purchase.need.diesel.consumption"].search([("origin_id", "=", origin_id)], limit=1).id            
            values = {
                "need_id": need_id,
                "name": line.name,
                "display_type": line.display_type,
                
                "origin": line._name,
                "origin_id": origin_id,
                "template_line_id": template_line_id,
            }
            if not line.display_type and line.equipment_id:
                equipment = line.equipment_id
                model, id = (equipment._name, equipment.id)
                values["equipment_id"] = f"{model},{id}"
                values["uom_id"] = line.uom_id.id
            return (0, 0, values)

        for record in self:
            new_lines = [_new_line(line, record.id) for line in record.equipment_ids]
            new_lines += [_new_line(line, record.id) for line in record.small_equipment_ids]
            new_lines.insert(0, (5, 0, 0))
            record.diesel_consumption_ids = new_lines

    def update_template_diesel_consumption_ids(self):
        """This method updates diesel_consumption_ids of the template from equipment_ids & small_equipment_ids"""
        if self.is_template:
            def _new_line(line):
                values = {
                    "origin": line._name,
                    "origin_id": f"{line._name},{line.id}",
                    "name": line.name,
                    "display_type": line.display_type,
                    "line_number": line.line_number,
                    "sequence_number": line.sequence_number,
                }
                if not line.display_type and line.equipment_id:
                    equipment = line.equipment_id
                    model, id = (equipment._name, equipment.id)
                    values["equipment_id"] = f"{model},{id}"
                    values["uom_id"] = line.uom_id.id
                return (0, 0, values)

            def already_in(_name):
                origins = self.diesel_consumption_ids.filtered(lambda line: line.origin_id._name == _name).mapped("origin_id")
                ids = [origin.id for origin in origins]
                return ids

            filter = lambda line: line.id not in already_in(line._name)
            new_lines = [_new_line(line) for line in self.equipment_ids.filtered(filter)]
            new_lines += [_new_line(line) for line in self.small_equipment_ids.filtered(filter)]

            self.diesel_consumption_ids = new_lines

    def fix_template_values(self):
        template_id = self.env["building.purchase.need"].search([("id", "=", 3)], limit=1)
        # raise Exception(template_id)

        for line in template_id.ressource_humain_ids:
            line.write({
                "duree_j": 0,
                "price_unit": 0
            })

        for line in template_id.line_ids:
            line.write({
                "quantity": 0,
                "price_unit": 0
            })

        for line in template_id.service_provision_ids:
            line.write({
                "quantity": 0,
                "price_unit": 0
            })

        for line in template_id.mini_equipment_ids:
            line.write({
                "quantity": 0,
                "duree_j": 0,
                "duree_h": 0,
                "price_unit": 0
            })

        for line in template_id.equipment_ids:
            line.write({
                "quantity": 0,
                "duree_j": 0,
                "price_unit": 0
            })

        for line in template_id.small_equipment_ids:
            line.write({
                "quantity": 0,
                "duree": 0,
                "price_unit": 0
            })

    def fix_compute_subtotal(self):
        for record in self:
            record.ressource_humain_ids._compute_price_subtotal()
            record.line_ids._compute_price_subtotal()
            record.service_provision_ids._compute_price_subtotal()
            record.mini_equipment_ids._compute_price_subtotal()
            record.equipment_ids._compute_price_subtotal()
            record.small_equipment_ids._compute_price_subtotal()
            record.diesel_consumption_ids._compute_price_subtotal()

    def get_template(self):
        template = self.env['building.purchase.need'].search([('is_template', '=', True)], limit=1)

        if not template:
            template = self.create({
                'is_template': True,
                'name': 'Template liste des besoins',
            })

        action_id = self.env.ref('building.building_purchase_need_template_action').read()[0]
        action_id['res_id'] = template.id

        return action_id

    def update_section_sequence_number(self):
        return {
            'name': _('Modfier une Section'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'update.section.sequence.number.wizard',
            'target': 'new',
            'context': self.env.context,
        }

    def create_section(self):
        return {
            'name': _('Ajouter une Section'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'create.section.wizard',
            'target': 'new',
            'context': self.env.context,
        }
    
    def create_line(self):
        if self._context.get("is_template"):
            return {
                'name': _('Ajouter une Ligne'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'create.line.wizard',
                'target': 'new',
                'context': self.env.context,
            }
        else:
            template = self.env['building.purchase.need'].search([('is_template', '=', True)], limit=1)
            categories_domain = 0

            category_mapping = ['ressource_humain', 'line', 'service_provision', 'mini_equipment', 'equipment', 'diesel_consumption', 'small_equipment']

            for category in category_mapping:
                check_need_category = template[f"{category}_ids"].filtered(
                    lambda line_template: line_template.is_activated and line_template.display_type != 'line_section'
                ) - getattr(self, f"{category}_ids").template_line_id

                if check_need_category:
                    categories_domain += 1

            if categories_domain >= 1:
                return {
                    'name': _('Ajouter une Ligne'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'create.need.line.wizard',
                    'target': 'new',
                    'context': self.env.context,
                }
            else:
                raise UserError(_('Il n\'y a pas de ligne à ajouter'))

    def fix_all(self):
        for record in self.env['building.purchase.need'].search([]):
            record._compute_amount()

    @api.depends('amount_business', 'line_ids.price_subtotal', 'site_installation_ids.price_subtotal', 
        'ressource_humain_ids.price_subtotal', 'equipment_ids.price_subtotal', 'mini_equipment_ids.price_subtotal', 
        'service_provision_ids.price_subtotal', 'diesel_consumption_ids.price_subtotal')
    def _compute_amount(self):
        for need in self:
            total_amount_site_install = sum((line.price_subtotal for line in need.site_installation_ids), 0.0)
            total_amount_equipment = sum((line.price_subtotal for line in need.equipment_ids), 0.0)
            total_amount_mini_equipment = sum((line.price_subtotal for line in need.mini_equipment_ids), 0.0) + sum((line.price_subtotal for line in need.equipment_ids), 0.0) + sum((line.price_subtotal for line in need.coffecha_ids), 0.0)
            total_amount_ressource = sum((line.price_subtotal for line in need.ressource_humain_ids if line.type_resource == 'supervisor'), 0.0)
            total_amount_executor_ressource = sum((line.price_subtotal for line in need.ressource_humain_ids if line.type_resource == 'executor'), 0.0)
            total_amount_diesel_consumption = sum((line.price_subtotal for line in need.diesel_consumption_ids), 0.0)
            total_amount_fuel = sum((line.price_subtotal for line in need.fuel_ids), 0.0)
            total_amount_service_provision = sum((line.price_subtotal for line in need.service_provision_ids), 0.0)
            total_amount_material = sum((line.price_subtotal for line in need.line_ids if line.type_produit == 'material'), 0.0)
            total_amount_consomable = sum((line.price_subtotal for line in need.line_ids if line.type_produit == 'conso'), 0.0)
            total_small_equipments = sum(line.price_subtotal for line in need.small_equipment_ids)

            need.total_amount_site_install = total_amount_site_install
            need.total_amount_equipment = total_amount_equipment
            need.total_amount_mini_equipment = total_amount_mini_equipment
            need.total_amount_ressource = total_amount_ressource
            need.total_amount_executor_ressource = total_amount_executor_ressource
            need.total_amount_diesel_consumption = total_amount_diesel_consumption
            need.total_amount_service_provision = total_amount_service_provision
            need.total_amount_material = total_amount_material
            need.total_amount_consomable = total_amount_consomable

            need.total_amount = total_small_equipments + total_amount_site_install + total_amount_equipment + total_amount_mini_equipment + total_amount_ressource + total_amount_executor_ressource + total_amount_fuel + total_amount_service_provision + total_amount_material + total_amount_consomable
            need.total_amount_margin = need.amount_business - need.total_amount


    @api.depends('equipment_ids')
    def _compute_categ_equipment(self):
        for need in self:
            categs = []
            if need.equipment_ids:
                for equip in need.equipment_ids:
                    if equip.equipment_category_id and equip.equipment_category_id.id not in categs:
                        categs.append(equip.equipment_category_id.id)
            need.categ_equipment_ids = categs

    def _get_default_is_template(self):
        if self._context.get("is_template") == True:
            return True
        else:
            return False
        
    def _get_deafult_name(self):
        if self._context.get("is_template") == True:
            return 'Template'
        
        else:
            return False
        
    name =  fields.Char(string='Numéro', default=_get_deafult_name)
    opp_id = fields.Many2one('crm.lead', string='Appel d''offre', related="site_id.opp_id")
    site_id = fields.Many2one('building.site', string='Affaire')
    site_ids_domain = fields.Many2many("building.site", compute="_compute_site_ids_domain")
    order_id = fields.Many2one('building.order', string='Bordereau des prix')
    state = fields.Selection([('draft', 'Brouillon'), ('validated', 'Validé'), ('approuved', 'Approuvé')], 'Statut', default='draft')
    categ_marche_id = fields.Many2one("building.categ.site", string="Categ Projet", related="site_id.categ_marche_id")
    is_template = fields.Boolean(default=_get_default_is_template)
    flow_ids = fields.One2many('building.purchase.need.flow', 'need_id', 'Flux', readonly=False, copy=True)
    site_installation_ids = fields.One2many('building.purchase.need.site.installation', 'need_id', 'site installation', readonly=False, copy=True)
    categ_equipment_ids = fields.Many2many('maintenance.vehicle.category', string='Categories matériels', compute='_compute_categ_equipment')
    coffecha_ids = fields.One2many('building.purchase.need.coffecha', 'need_id', 'Coffrage/Echaffaudage', readonly=False, copy=True)

    ressource_humain_ids = fields.One2many('building.purchase.need.ressource.humain', 'need_id', 'ressource humain', readonly=False, copy=True)
    line_ids = fields.One2many('building.purchase.need.line', 'need_id', 'Besoins', readonly=False, copy=True)
    service_provision_ids = fields.One2many('building.purchase.need.service.provision', 'need_id', 'service provision', readonly=False, copy=True)
    mini_equipment_ids = fields.One2many('building.purchase.need.mini.equipment', 'need_id', 'Lignes', readonly=False, copy=True)
    equipment_ids = fields.One2many('building.purchase.need.equipment', 'need_id', 'materiels', readonly=False, copy=True)
    small_equipment_ids = fields.One2many('building.purchase.need.small.equipment', 'need_id', 'Petit matériels')
    diesel_consumption_ids = fields.One2many('building.purchase.need.diesel.consumption', 'need_id', 'diesel consumption', readonly=False, copy=True)

    ro_ressource_humain_ids = fields.One2many("building.purchase.need.ressource.humain", string="Ressources Humaines", compute="_ro_line_ids")
    ro_line_ids = fields.One2many("building.purchase.need.line", string="Fournitures", compute="_ro_line_ids")
    ro_service_provision_ids = fields.One2many("building.purchase.need.service.provision", string="Prestation de service", compute="_ro_line_ids")
    ro_mini_equipment_ids = fields.One2many("building.purchase.need.mini.equipment", string="Outillages", compute="_ro_line_ids")
    ro_equipment_ids = fields.One2many("building.purchase.need.equipment", string="Matériels", compute="_ro_line_ids")
    ro_small_equipment_ids = fields.One2many("building.purchase.need.small.equipment", string="Petit Matériels", compute="_ro_line_ids")
    ro_diesel_consumption_ids = fields.One2many("building.purchase.need.diesel.consumption", string="Gasoil", compute="_ro_line_ids")

    total_ressource_humains = fields.Float("Sous-total", compute="_compute_total")
    total_lines = fields.Float("Sous-total", compute="_compute_total")
    total_service_provisions = fields.Float("Sous-total", compute="_compute_total")
    total_mini_equipments = fields.Float("Sous-total", compute="_compute_total")
    total_equipments = fields.Float("Sous-total", compute="_compute_total")
    total_small_equipments = fields.Float("Sous-total", compute="_compute_total")
    total_diesel_consumptions = fields.Float("Sous-total", compute="_compute_total")
        
    amount_business = fields.Float(string='BPHT', compute="_compute_amount_business")
    total_amount_site_install = fields.Float(string='Installation de chantier', readonly=False, store =True, compute='_compute_amount')
    total_amount_equipment = fields.Float(string='Matériels', readonly=False, store =True, compute='_compute_amount')
    total_amount_mini_equipment = fields.Float(string='Petit matériels', readonly=False, store =True, compute='_compute_amount')
    total_amount_ressource = fields.Float(string='Encadrement', readonly=False, store =True, compute='_compute_amount')
    total_amount_executor_ressource = fields.Float(string='Main-d’œuvre', readonly=False, store =True, compute='_compute_amount')
    total_amount_diesel_consumption = fields.Float(string='Gasoil', readonly=False, store =True, compute='_compute_amount')
    total_amount_service_provision = fields.Float(string='Prestation de service', readonly=False, store =True, compute='_compute_amount')
    total_amount_material = fields.Float(string='Matériaux', readonly=False, store =True, compute='_compute_amount')
    total_amount_consomable = fields.Float(string='Consommables', readonly=False, store =True, compute='_compute_amount')
    total_amount = fields.Float(string='Total Budget', readonly=False, store =True, compute='_compute_amount')
    total_amount_margin = fields.Float(string='Marge', readonly=False, store =True, compute='_compute_amount')

    ressource_humain_ids_job_ids = fields.Many2many("hr.job", compute="_compute_ressource_humain_ids_job_ids")
    line_ids_product_ids = fields.Many2many("product.product", compute="_compute_line_ids_product_ids")
    service_provision_ids_product_ids = fields.Many2many("product.product", compute="_compute_service_provision_ids_product_ids")
    mini_equipment_ids_product_ids = fields.Many2many("product.product", compute="_compute_mini_equipment_ids_product_ids")
    equipment_ids_equipment_ids = fields.Many2many("maintenance.vehicle.category", compute="_compute_equipment_ids_equipment_ids")

    fuel_ids = fields.One2many("building.purchase.need.fuel", "need_id", string="Carburant")
    ro_fuel_ids = fields.One2many("building.purchase.need.fuel", string="Carburant", compute="_ro_line_ids")
    total_fuels = fields.Float("Sous-total", compute="_compute_total")

    @api.depends("ressource_humain_ids")
    def _compute_ressource_humain_ids_job_ids(self):
        for bpn in self:
            bpn.ressource_humain_ids_job_ids = self.env["hr.job"].search([("id", "not in", bpn.ressource_humain_ids.mapped("job_id").ids)])

    @api.depends("line_ids")
    def _compute_line_ids_product_ids(self):
        for bpn in self:
            bpn.line_ids_product_ids = self.env["product.product"].search([("id", "not in", bpn.line_ids.mapped("product_id").ids), ("purchase_ok", "=", True)])
    
    @api.depends("service_provision_ids")
    def _compute_service_provision_ids_product_ids(self):
        for bpn in self:
            bpn.service_provision_ids_product_ids = self.env["product.product"].search([("id", "not in", bpn.service_provision_ids.mapped("product_id").ids), ("purchase_ok", "=", True), ("type", "=", "service")])

    @api.depends("mini_equipment_ids")
    def _compute_mini_equipment_ids_product_ids(self):
        for bpn in self:
            bpn.mini_equipment_ids_product_ids = self.env["product.product"].search([("id", "not in", bpn.mini_equipment_ids.mapped("product_id").ids)])

    @api.depends("equipment_ids")
    def _compute_equipment_ids_equipment_ids(self):
        for bpn in self:
            bpn.equipment_ids_equipment_ids = self.env["maintenance.vehicle.category"].search([("id", "not in", bpn.equipment_ids.mapped("equipment_category_id").ids)])

    @api.depends("state", "ressource_humain_ids", "line_ids", "service_provision_ids", "mini_equipment_ids", "equipment_ids", "small_equipment_ids", "diesel_consumption_ids")
    def _compute_total(self):
        for record in self:
            record.total_ressource_humains = sum(line.price_subtotal for line in record.ressource_humain_ids)
            record.total_lines = sum(line.price_subtotal for line in record.line_ids)
            record.total_service_provisions = sum(line.price_subtotal for line in record.service_provision_ids)
            record.total_mini_equipments = sum(line.price_subtotal for line in record.mini_equipment_ids)
            record.total_equipments = sum(line.price_subtotal for line in record.equipment_ids)
            record.total_small_equipments = sum(line.price_subtotal for line in record.small_equipment_ids)
            record.total_diesel_consumptions = sum(line.price_subtotal for line in record.diesel_consumption_ids)
            record.total_fuels = sum(line.price_subtotal for line in record.fuel_ids)

    @api.depends("state", "ressource_humain_ids", "line_ids", "service_provision_ids", "mini_equipment_ids", "equipment_ids", "small_equipment_ids", "diesel_consumption_ids")
    def _ro_line_ids(self):
        for record in self:
            filter = lambda line: line.quantity != 0 or line.display_type == "line_section"
            record.ro_ressource_humain_ids = record.state != "draft" and not record.is_template and record.ressource_humain_ids.filtered(filter) or record.ressource_humain_ids
            record.ro_line_ids = record.state != "draft" and not record.is_template and record.line_ids.filtered(filter) or record.line_ids
            record.ro_service_provision_ids = record.state != "draft" and not record.is_template and record.service_provision_ids.filtered(filter) or record.service_provision_ids
            record.ro_mini_equipment_ids = record.state != "draft" and not record.is_template and record.mini_equipment_ids.filtered(filter) or record.mini_equipment_ids
            record.ro_equipment_ids = record.state != "draft" and not record.is_template and record.equipment_ids.filtered(filter) or record.equipment_ids
            record.ro_small_equipment_ids = record.state != "draft" and not record.is_template and record.small_equipment_ids.filtered(filter) or record.small_equipment_ids
            record.ro_diesel_consumption_ids = record.state != "draft" and not record.is_template and record.diesel_consumption_ids.filtered(filter) or record.diesel_consumption_ids
            record.ro_fuel_ids = record.state != "draft" and not record.is_template and record.fuel_ids.filtered(filter) or record.fuel_ids

    @api.depends("site_id")
    def _compute_site_ids_domain(self):
        for site_need in self:
            building_purchase_needs = self.env['building.purchase.need'].search([])
            sites_with_purchase_needs = building_purchase_needs.mapped("site_id")
            domain = self.env["building.site"].search([]) - sites_with_purchase_needs

            site_need.site_ids_domain = domain

    @api.model
    def default_get(self, fields):
        res = super(building_purchase_need, self).default_get(fields)
        if not self._context.get("is_template") == True:
            template = self.env['building.purchase.need'].search([('is_template', '=', True)], limit=1)

            site_installation_ids_vals = []
            for site_install in template.site_installation_ids:
                site_install_vals = site_install.copy_data()[0]
                if site_install_vals['is_activated']:
                    site_install_vals['need_id'] = False
                    site_install_vals['sequence_number'] = False
                    site_install_vals['line_number'] = False
                    site_install_vals['section_id'] = False
                    site_install_vals['identification_number'] = False
                    site_install_vals['sequence_number_parent'] = 0
                    site_install_vals['line_number_parent'] = 0
                    site_install_vals['identification_number_parent'] = 0
                    site_install_vals['template_line_id'] = site_install["id"]
                    site_installation_ids_vals.append((0, 0, site_install_vals))
            res.update({
                'site_installation_ids': site_installation_ids_vals,
            })

            ressource_humain_ids_vals = []
            for ressource_humain in template.ressource_humain_ids:
                ressource_humain_vals = ressource_humain.copy_data()[0]
                if ressource_humain_vals['is_activated']:
                    ressource_humain_vals['need_id'] = False
                    ressource_humain_vals['sequence_number'] = False
                    ressource_humain_vals['line_number'] = False
                    ressource_humain_vals['section_id'] = False
                    ressource_humain_vals['identification_number'] = False
                    ressource_humain_vals['template_line_id'] = ressource_humain['id']
                    ressource_humain_ids_vals.append((0, 0, ressource_humain_vals))
            res.update({
                'ressource_humain_ids': ressource_humain_ids_vals,
            })

            line_ids_vals = []
            for line in template.line_ids:
                line_vals = line.copy_data()[0]
                if line_vals['is_activated']:
                    product_id = line_vals['product_id']
                    product = self.env['product.product'].browse(product_id)

                    if product:
                        line_vals['uom_id'] = product.uom_id.id
                        line_vals['price_unit'] = product.reference_price

                    line_vals['need_id'] = False
                    line_vals['sequence_number'] = False
                    line_vals['line_number'] = False
                    line_vals['section_id'] = False
                    line_vals['identification_number'] = False
                    line_vals['template_line_id'] = line['id']
                    line_ids_vals.append((0, 0, line_vals))
            res.update({
                'line_ids': line_ids_vals,
            })

            service_provision_ids_vals = []
            for service_provision in template.service_provision_ids:
                service_provision_vals = service_provision.copy_data()[0]
                if service_provision_vals['is_activated']:
                    product_id = service_provision_vals['product_id']
                    product = self.env['product.product'].browse(product_id)

                    if product:
                        service_provision_vals['uom_id'] = product.uom_id.id
                        service_provision_vals['price_unit'] = product.reference_price

                    service_provision_vals['need_id'] = False
                    service_provision_vals['sequence_number'] = False
                    service_provision_vals['line_number'] = False
                    service_provision_vals['section_id'] = False
                    service_provision_vals['identification_number'] = False
                    service_provision_vals['template_line_id'] = service_provision['id']
                    service_provision_ids_vals.append((0, 0, service_provision_vals))
            res.update({
                'service_provision_ids': service_provision_ids_vals,
            })

            mini_equipment_ids_vals = []
            for mini_equipment in template.mini_equipment_ids:
                mini_equipment_vals = mini_equipment.copy_data()[0]
                if mini_equipment_vals['is_activated']:
                    product = self.env["product.product"].browse(mini_equipment_vals["product_id"])

                    if product:
                        mini_equipment_vals["uom_id"] = product.uom_id.id
                        mini_equipment_vals["price_unit"] = product.reference_price

                    mini_equipment_vals['need_id'] = False
                    mini_equipment_vals['sequence_number'] = False
                    mini_equipment_vals['line_number'] = False
                    mini_equipment_vals['section_id'] = False
                    mini_equipment_vals['identification_number'] = False
                    mini_equipment_vals['template_line_id'] = mini_equipment['id']
                    mini_equipment_ids_vals.append((0, 0, mini_equipment_vals))
            res.update({
                'mini_equipment_ids': mini_equipment_ids_vals,
            })

            equipment_ids_vals = []
            for equipment in template.equipment_ids:
                equipment_vals = equipment.copy_data()[0]
                if equipment_vals['is_activated']:
                    equipment_id = equipment_vals['equipment_category_id']
                    equipment_category = self.env['maintenance.vehicle.category'].browse(equipment_id)

                    if equipment_category:
                        equipment_vals['uom_id'] = equipment_category.uom_id.id
                        equipment_vals['price_unit'] = equipment_category.cost

                    equipment_vals['need_id'] = False
                    equipment_vals['sequence_number'] = False
                    equipment_vals['line_number'] = False
                    equipment_vals['section_id'] = False
                    equipment_vals['identification_number'] = False
                    equipment_vals['template_line_id'] = equipment['id']
                    equipment_ids_vals.append((0, 0, equipment_vals))
            res.update({
                'equipment_ids': equipment_ids_vals,
            })

            diesel_consumption_ids_vals = []
            for diesel_consumption in template.diesel_consumption_ids:
                diesel_consumption_vals = diesel_consumption.copy_data()[0]                
                if diesel_consumption_vals['is_activated']:
                    diesel_consumption_vals['need_id'] = False
                    diesel_consumption_vals['sequence_number'] = False
                    diesel_consumption_vals['line_number'] = False
                    diesel_consumption_vals['section_id'] = False
                    diesel_consumption_vals['identification_number'] = False
                    diesel_consumption_vals['template_line_id'] = diesel_consumption['id']
                    diesel_consumption_ids_vals.append((0, 0, diesel_consumption_vals))
            res.update({
                'diesel_consumption_ids': diesel_consumption_ids_vals,
            })

            small_equipment_ids_vals = []
            for small_equipment in template.small_equipment_ids:
                small_equipment_vals = small_equipment.copy_data()[0]
                if small_equipment_vals['is_activated']:
                    equipment_id = small_equipment_vals['equipment_id']
                    equipment_category = self.env['product.product'].browse(equipment_id)

                    if equipment_category:
                        small_equipment_vals['uom_id'] = equipment_category.uom_id.id
                        small_equipment_vals['price_unit'] = equipment_category.standard_price

                    small_equipment_vals['need_id'] = False
                    small_equipment_vals['sequence_number'] = False
                    small_equipment_vals['line_number'] = False
                    small_equipment_vals['section_id'] = False
                    small_equipment_vals['identification_number'] = False
                    small_equipment_vals['template_line_id'] = small_equipment['id']
                    small_equipment_ids_vals.append((0, 0, small_equipment_vals))
            res.update({
                'small_equipment_ids': small_equipment_ids_vals,
            })

            fuel_ids_vals = []
            for fuel in template.fuel_ids:
                fuel_vals = fuel.copy_data()[0]
                if fuel_vals["is_activated"]:
                    product_id = fuel_vals["product_id"]
                    product = self.env["product.product"].browse(product_id)
                    if product:
                        fuel_vals["uom_id"] = product.uom_id.id
                        fuel_vals["price_unit"] = product.reference_price

                    fuel_vals["need_id"] = False
                    fuel_vals["sequence_number"] = False
                    fuel_vals["line_number"] = False
                    fuel_vals["section_id"] = False
                    fuel_vals["identification_number"] = False
                    fuel_vals["template_line_id"] = fuel["id"]
                    fuel_ids_vals.append((0, 0, fuel_vals))
            res.update({'fuel_ids': fuel_ids_vals})
        return res

    @api.model
    def create(self, vals):
        if self._context.get("is_template") == True:
            check_is_template_exists = self.search([('is_template', '=', True)], limit=1)
            if check_is_template_exists:
                raise UserError(_('Attention!: Il y a une template déja crée'))

        if vals.get('opp_id'):
            self.env['crm.lead'].browse(vals.get('opp_id')).write({'is_purchase_need_created': True})

        return super(building_purchase_need, self).create(vals)

    def write(self, vals):
        date_validation = fields.Datetime.now()

        ressource_humain_ids = vals.get("ro_ressource_humain_ids")
        if ressource_humain_ids:
            for rhi in ressource_humain_ids:
                if rhi[0] == 1 and rhi[2].get("duree_j"):
                    record = self.env["building.purchase.need.ressource.humain"].browse(rhi[1])
                    record_flow = {
                    'need_id': self.id,
                    'user_id': self.env.user.id,
                    'date':date_validation,
                    'note': f"{record.job_id.name}: Volume {float(record.duree_j)} > {float(rhi[2]['duree_j'])}"
                    }
                    self.env['building.purchase.need.flow'].create(record_flow)

        line_ids = vals.get("ro_line_ids")
        if line_ids:
            for li in line_ids:
                if li[0] == 1 and li[2].get("quantity"):
                    record = self.env["building.purchase.need.line"].browse(li[1])
                    record_flow = {
                    'need_id': self.id,
                    'user_id': self.env.user.id,
                    'date':date_validation,
                    'note': f"{record.product_id.name}: Quantité {float(record.quantity)} > {float(li[2]['quantity'])}"
                    }
                    self.env['building.purchase.need.flow'].create(record_flow)

        service_provision_ids = vals.get("ro_service_provision_ids")
        if service_provision_ids:
            for spi in service_provision_ids:
                if spi[0] == 1 and spi[2].get("quantity"):
                    record = self.env["building.purchase.need.service.provision"].browse(spi[1])
                    record_flow = {
                    'need_id': self.id,
                    'user_id': self.env.user.id,
                    'date':date_validation,
                    'note': f"{record.product_id.name}: Quantité {float(record.quantity)} > {float(spi[2]['quantity'])}"
                    }
                    self.env['building.purchase.need.flow'].create(record_flow)

        mini_equipment_ids = vals.get("ro_mini_equipment_ids")
        if mini_equipment_ids:
            for mei in mini_equipment_ids:
                if mei[0] == 1 and mei[2].get("quantity"):
                    record = self.env["building.purchase.need.mini.equipment"].browse(mei[1])
                    record_flow = {
                    'need_id': self.id,
                    'user_id': self.env.user.id,
                    'date':date_validation,
                    'note': f"{record.product_id.name}: Quantité {float(record.quantity)} > {float(mei[2]['quantity'])}"
                    }
                    self.env['building.purchase.need.flow'].create(record_flow)

        equipment_ids = vals.get("ro_equipment_ids")
        if equipment_ids:
            for ei in equipment_ids:
                if ei[0] == 1 and ei[2].get("quantity"):
                    record = self.env["building.purchase.need.equipment"].browse(ei[1])
                    record_flow = {
                    'need_id': self.id,
                    'user_id': self.env.user.id,
                    'date':date_validation,
                    'note': f"{record.equipment_category_id.name}: Quantité {float(record.quantity)} > {float(ei[2]['quantity'])}"
                    }
                    self.env['building.purchase.need.flow'].create(record_flow)
                    
        small_equipment_ids = vals.get("small_equipment_ids")
        # raise Exception(small_equipment_ids)
        if small_equipment_ids:
            for sei in small_equipment_ids:
                if sei[0] == 1 and sei[2].get("quantity"):
                    record = self.env["building.purchase.need.small.equipment"].browse(sei[1])
                    record_flow = {
                    'need_id': self.id,
                    'user_id': self.env.user.id,
                    'date':date_validation,
                    'note': f"{record.equipment_id.name}: Quantité {float(record.quantity)} > {float(sei[2]['quantity'])}"
                    }
                    self.env['building.purchase.need.flow'].create(record_flow)

        res = super(building_purchase_need, self).write(vals)

        if vals.get('opp_id'):
            if self.opp_id:
                self.opp_id.write({'is_purchase_need_created': False})
            self.env['crm.lead'].browse(vals.get('opp_id')).write({'is_purchase_need_created': True})

        return res
    
    def unlink(self):
        for need in self:
            if need.site_id and need.site_id.state != 'created':
                raise UserError(_("Vous ne pouvez pas supprimer une liste de besoins d'une affaire en cours."))
            else:
                if need.opp_id:
                    need.opp_id.write({'is_purchase_need_created': False})
        return super(building_purchase_need, self).unlink()

    @api.depends('site_id')
    def _compute_amount_business(self):
        for record in self:
            record.amount_business = 0
            if record.site_id:
                record.categ_marche_id = record.site_id.categ_marche_id.id
                order = record.env['building.order'].search(
                    [('site_id', '=', record.site_id.id)], order='id desc', limit=1
                )
                if order:
                    record.amount_business = order.amount_untaxed

    def refresh_purchase_needs(self):
        for need in self.env["building.purchase.need"].search([]):
            order = self.env['building.order'].search([('site_id', '=', need.site_id.id)], order='id desc', limit=1)
            if order:
                need.amount_business = order.amount_untaxed

    # @api.onchange('categ_marche_id')
    # def onchange_categ_marche(self):
    #     if self.categ_marche_id:
    #         need = self.search([('categ_marche_id' , '=' , self.categ_marche_id.id)], order='id desc', limit=1)
    #         if need :
    #             self.site_installation_ids = need.site_installation_ids
    #             self.ressource_humain_ids = need.ressource_humain_ids
    #             self.line_ids = need.line_ids
    #             self.service_provision_ids = need.service_provision_ids
    #             self.mini_equipment_ids = need.mini_equipment_ids
    #             self.equipment_ids = need.equipment_ids
    #             self.equipment_ids = need.equipment_ids
    #             self.diesel_consumption_ids = need.diesel_consumption_ids

    def action_validated(self):
        date_validation = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        for need in self:
            sequ = self.env['ir.sequence'].get('building.purchase.need') or '/'
            need.state = 'validated'
            need.name = sequ
            record_flow = {
                'need_id': need.id,
                'user_id': self.env.user.id,
                'date':date_validation,
                'note': 'Validation par ' + self.env.user.name
            }
            self.env['building.purchase.need.flow'].create(record_flow)

    def action_approuved(self):
        date_approuved = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        for need in self:
            need.state = 'approuved'
            record_flow = {
                'need_id': need.id,
                'user_id': self.env.user.id,
                'date':date_approuved,
                'note': 'Approbation par ' + self.env.user.name
            }
            self.env['building.purchase.need.flow'].create(record_flow)

    def action_open(self):
        date_draft = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        for need in self:
            need.state = "draft"
            record_flow = {
                "need_id": need.id,
                "user_id": self.env.user.id,
                "date": date_draft,
                "note": f"Remettre par {self.env.user.name} au brouillon pour modifcation"
            }
            self.env['building.purchase.need.flow'].create(record_flow)

    def action_visualize_graph(self):
        list_need_report = []
        for need in self:
            self.env['building.purchase.need.report'].search([('need_id', '=', need.id), ('site_id', '=', need.site_id.id), ('opp_id', '=', need.opp_id.id)]).unlink()
            record_load_site_install = {
                'opp_id': need.opp_id.id,
                'need_id': need.id,
                'site_id' : need.site_id.id,
                'r0': 'site_install',
                'amount' : need.total_amount_site_install,
                'prc_amount_per_load': (need.total_amount_site_install/need.total_amount)*100,
                'prc_seuil' : 100
            }
            need_report = self.env['building.purchase.need.report'].create(record_load_site_install)
            list_need_report.append(need_report.id)
            record_load_ressource = {
                'opp_id': need.opp_id.id,
                'need_id': need.id,
                'site_id' : need.site_id.id,
                'r0': 'supervisor_ressource',
                'amount' : need.total_amount_ressource,
                'prc_amount_per_load': (need.total_amount_ressource/need.total_amount)*100,
                'prc_seuil' : 100
            }
            need_report = self.env['building.purchase.need.report'].create(record_load_ressource)
            list_need_report.append(need_report.id)
            
            limit_control = self.env['building.limit.control.site'].search([('categ_site_id', '=', need.site_id.categ_marche_id.id), ('rubrique', '=', 'product')])
            prc_limit_control = 0
            if limit_control:
                prc_limit_control = limit_control.prc_limit
            record_load_material = {
                'opp_id': need.opp_id.id,
                'need_id': need.id,
                'site_id' : need.site_id.id,
                'r0': 'product',
                'amount' : need.total_amount_material,
                'prc_amount_per_load': (need.total_amount_material/need.total_amount)*100,
                'prc_seuil' : prc_limit_control
            }
            need_report = self.env['building.purchase.need.report'].create(record_load_material)
            list_need_report.append(need_report.id)
            
            limit_control = self.env['building.limit.control.site'].search([('categ_site_id', '=', need.site_id.categ_marche_id.id), ('rubrique', '=', 'equipment')])
            prc_limit_control = 0
            if limit_control:
                prc_limit_control = limit_control.prc_limit
            record_load_equipment = {
                'opp_id': need.opp_id.id,
                'need_id': need.id,
                'site_id' : need.site_id.id,
                'r0': 'equipment',
                'amount' : need.total_amount_equipment,
                'prc_amount_per_load': (need.total_amount_equipment/need.total_amount)*100,
                'prc_seuil' : prc_limit_control
            }
            need_report = self.env['building.purchase.need.report'].create(record_load_equipment)
            list_need_report.append(need_report.id)
            
            limit_control = self.env['building.limit.control.site'].search([('categ_site_id', '=', need.site_id.categ_marche_id.id), ('rubrique', '=', 'diesel')])
            prc_limit_control = 0
            if limit_control:
                prc_limit_control = limit_control.prc_limit
            record_load_diesel_consumption  = {
                'opp_id': need.opp_id.id,
                'need_id': need.id,
                'site_id' : need.site_id.id,
                'r0': 'diesel',
                'amount' : need.total_amount_diesel_consumption,
                'prc_amount_per_load': (need.total_amount_diesel_consumption/need.total_amount)*100,
                'prc_seuil' : prc_limit_control
            }
            need_report = self.env['building.purchase.need.report'].create(record_load_diesel_consumption)
            list_need_report.append(need_report.id)
            record_load_mini_equipment = {
                'opp_id': need.opp_id.id,
                'need_id': need.id,
                'site_id' : need.site_id.id,
                'r0': 'mini_equipment',
                'amount' : need.total_amount_mini_equipment,
                'prc_amount_per_load': (need.total_amount_mini_equipment/need.total_amount)*100,
                'prc_seuil' : 100
            }
            need_report = self.env['building.purchase.need.report'].create(record_load_mini_equipment)
            list_need_report.append(need_report.id)
            
            limit_control = self.env['building.limit.control.site'].search([('categ_site_id', '=', need.site_id.categ_marche_id.id), ('rubrique', '=', 'conso')])
            prc_limit_control = 0
            if limit_control:
                prc_limit_control = limit_control.prc_limit
            record_load_consomable = {
                'opp_id': need.opp_id.id,
                'need_id': need.id,
                'site_id' : need.site_id.id,
                'r0': 'consu',
                'amount' : need.total_amount_consomable,
                'prc_amount_per_load': (need.total_amount_consomable/need.total_amount)*100,
                'prc_seuil' : prc_limit_control
            }
            need_report = self.env['building.purchase.need.report'].create(record_load_consomable)
            list_need_report.append(need_report.id)
            
            limit_control = self.env['building.limit.control.site'].search([('categ_site_id', '=', need.site_id.categ_marche_id.id), ('rubrique', '=', 'rh')])
            prc_limit_control = 0
            if limit_control:
                prc_limit_control = limit_control.prc_limit
            record_load_executor_ressource = {
                'opp_id': need.opp_id.id,
                'need_id': need.id,
                'site_id' : need.site_id.id,
                'r0': 'executor_ressource',
                'amount' : need.total_amount_executor_ressource,
                'prc_amount_per_load': (need.total_amount_executor_ressource/need.total_amount)*100,
                'prc_seuil' : prc_limit_control
            }
            need_report = self.env['building.purchase.need.report'].create(record_load_executor_ressource)
            list_need_report.append(need_report.id)
            
            limit_control = self.env['building.limit.control.site'].search([('categ_site_id', '=', need.site_id.categ_marche_id.id), ('rubrique', '=', 'prov_serv')])
            prc_limit_control = 0
            if limit_control:
                prc_limit_control = limit_control.prc_limit
            record_load_service_provision = {
                'opp_id': need.opp_id.id,
                'need_id': need.id,
                'site_id' : need.site_id.id,
                'r0': 'service_provision',
                'amount' : need.total_amount_service_provision,
                'prc_amount_per_load': (need.total_amount_service_provision/need.total_amount)*100,
                'prc_seuil' : prc_limit_control
            }
            need_report = self.env['building.purchase.need.report'].create(record_load_service_provision)
            list_need_report.append(need_report.id)

        domain = [('id', 'in', list_need_report)]
        search_view_id = self.env.ref('building.building_purchase_need_report_filter').id
        return {
            'name': _('Besoins par rubrique'),
            'domain': domain,
            'res_model': 'building.purchase.need.report',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,graph',
            'search_view_id': search_view_id,
            'limit': 80
        }

    def get_lines(self):
        correspondance = {
            1: ("ressource.humain", "ressource_humain", "Ressources Humaines"),
            2: ("line", "line", "Fournitures"),
            3: ("service.provision", "service_provision", "Prestation de service"),
            4: ("mini.equipment", "mini_equipment", "Outillages"),
            5: ("equipment", "equipment", "Matériels"),
            6: ("small.equipment", "small_equipment", "Petit Matériels"),
            7: ("fuel", "fuel", "Carburant"),
        }

        model, view, name = correspondance[self.env.context.get("number")]
        model = f"building.purchase.need.{model}"
        tree_view_id = self.env.ref(f"building.building_purchase_need_{view}_view_tree_get_lines").id
        search_view_id = self.env.ref(f"building.building_purchase_need_{view}_view_search").id

        return {
            "name": name,
            "res_model": model,
            "type": "ir.actions.act_window",
            "view_mode": "tree",
            "search_view_id": (search_view_id, "search"),
            "views": [
                (tree_view_id, "tree"),
            ],
            "domain": [("need_id", "=", self.id), ("display_type", "!=", "line_section")],
            "context": {
                "create": False,
                "delete": False,
                "edit": self.state == "draft",
            }
        }


class building_purchase_need_site_installation(models.Model):

    _name = 'building.purchase.need.site.installation'
    _description = "Site Installation"
    _order = "sequence_number,line_number"

    @api.depends('quantity', 'duree', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.quantity = line.quantity if line.quantity else 0
            line.duree = line.duree if line.duree else 0
            line.price_unit = line.price_unit if line.price_unit else 0
            line.price_subtotal = line.quantity*line.duree*line.price_unit

    def _compute_ordered_remaining_quantity(self):
        for line in self:
            qty_ordered = self.env['building.assignment.line'].search_count([('site_id', '=', line.site_id.id), ('state', '=', 'open'), ('categ_maintenance_id', '=', line.equipment_id.id)])
            line.quantity_ordered = qty_ordered
            line.quantity_remaining = line.quantity - qty_ordered
            requested_lines = self.env['maintenance.request.resource.material.line'].search([('site_id', '=', line.site_id.id), ('state', '!=', 'draft'), ('categ_id', '=', line.equipment_id.id)])
            quantity_requested = 0
            if requested_lines:
                quantity_requested = sum(line.qty for line in requested_lines)
            line.quantity_requested = quantity_requested
            
    @api.depends('sequence')
    def _compute_sequence(self):
        for line in self:
            line.sequence_realted = line.sequence

    @api.onchange('line_number')
    def _onchange_line(self):
        if self._context.get("is_template") == True:
            template = self.env['building.purchase.need'].search([('is_template', '=', True)], limit=1)
            check_line_number_duplication = self.env['building.purchase.need.site.installation'].search([('line_number', '=', self.line_number), ('section_id', '=', self.section_id.id), ('need_id', '=', template.id)])

            if check_line_number_duplication:
                raise UserError(_('Attention!: Il y a une ligne avec le même numéro'))

            self.identification_number = f"{self.section_id.identification_number}.{self.line_number}"

    need_id = fields.Many2one('building.purchase.need', string='Affaire', ondelete="cascade")
    equipment_id = fields.Many2one('maintenance.vehicle.category', string='Matériel')
    num_line =  fields.Char(string='N°') 
    name =  fields.Char(string='Description') 
    uom_id = fields.Many2one('uom.uom', string='UDM')
    quantity =  fields.Float(string='Quantité')
    quantity_ordered =  fields.Float(string='Quantité Affectée', compute='_compute_ordered_remaining_quantity')
    quantity_remaining =  fields.Float(string='Quantité Restante', compute='_compute_ordered_remaining_quantity')
    quantity_requested =  fields.Float(string='Quantité Demandée', compute='_compute_ordered_remaining_quantity')
    duree =  fields.Float(string='Durée(Mois)', default=1)
    duree_j =  fields.Float(string='Durée(Jours)', default=1)
    price_unit =  fields.Float(string='Prix HT')
    price_subtotal =  fields.Float(string='Prix Total', readonly=False, store=True, compute='_compute_price_subtotal')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    note =  fields.Char(string='Observations')
    sequence = fields.Integer(string='Sequence', default=1)
    sequence_num = fields.Integer(string='Sequence', default=1)
    sequence_realted = fields.Integer(string='Séquence', compute='_compute_sequence', store=True)
    site_id = fields.Many2one('building.site', string='Affaire',related='need_id.site_id', store=True, readonly=True)
    state = fields.Selection(string='Statut', related='need_id.state', store=True, readonly=True)

    sequence_number = fields.Integer(string="Numéro de séquence")
    line_number = fields.Integer(string="Numéro de ligne")
    identification_number = fields.Char(string="Identifiant")
    sequence_number_parent = fields.Integer(string="Numéro de séquence parent", related='template_line_id.sequence_number', default=0)
    line_number_parent = fields.Integer(string="Numéro de ligne parent", related='template_line_id.line_number', default=0)
    identification_number_parent = fields.Char(string="Identifiant parent", readonly=True, related='template_line_id.identification_number', default=0)
    section_ids = fields.One2many('building.purchase.need.site.installation', 'section_id', string='Sous-sections')
    section_id = fields.Many2one('building.purchase.need.site.installation', string='Section parente', ondelete='restrict')
    template_line_id = fields.Many2one('building.purchase.need.site.installation', string='Ligne template', ondelete='restrict')
    is_activated = fields.Boolean(string="Act.", default=True)
    
    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        if self.equipment_id:
            # self.name = self.equipment_id.name
            self.uom_id = self.equipment_id.uom_id.id
            self.price_unit = self.equipment_id.cost

class building_purchase_need_rh(models.Model):
    _name = 'building.purchase.need.ressource.humain'
    _description = "Ressources Humaines"
    _order = "sequence_number,line_number"


    is_from_template = fields.Boolean(string="Provenant du template", compute='_compute_is_from_template')

    def _compute_is_from_template(self):
        for line in self:
            if line.need_id.is_template:
                line.is_from_template = self.search_count([('template_line_id', '=', line.id)]) > 0
            else:
                line.is_from_template = False

    @api.depends('quantity', 'duree_j', 'duree_h', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            # if line.type_resource == 'executor':
            #     line.price_subtotal = line.quantity*line.duree_j*line.duree_h*line.price_unit
            # if line.type_resource == 'supervisor':
            #     line.price_subtotal = line.quantity*line.duree_j*line.price_unit
            line.quantity = line.quantity if line.quantity else 0
            line.duree_j = line.duree_j if line.duree_j else 0
            line.price_unit = line.price_unit if line.price_unit else 0
            line.price_subtotal = line.duree_j*line.price_unit

    def _compute_ordered_remaining_quantity(self):
        for line in self:
            qty_ordered = self.env['building.assignment.line'].search_count([('site_id', '=', line.site_id.id), ('state', '=', 'open'), ('job_id', '=', line.job_id.id)])
            line.quantity_ordered = qty_ordered
            line.quantity_remaining = line.quantity - qty_ordered

    def _compute_ordered_remaining_quantity(self):
        for line in self:
            qty_ordered = self.env['building.assignment.line'].search_count([('site_id', '=', line.site_id.id), ('state', '=', 'open'), ('job_id', '=', line.job_id.id)])
            line.quantity_ordered = qty_ordered
            line.quantity_remaining = line.quantity - qty_ordered
            requested_lines = self.env['maintenance.request.resource.material.line'].search([('site_id', '=', line.site_id.id), ('state', '!=', 'draft'), ('job_id', '=', line.job_id.id)])
            quantity_requested = 0
            if requested_lines:
                quantity_requested = sum(line.qty for line in requested_lines)
            line.quantity_requested = quantity_requested

    @api.depends('sequence')
    def _compute_sequence(self):
        for line in self:
            line.sequence_realted = line.sequence

    @api.onchange('line_number')
    def _onchange_line(self):
        if self._context.get("is_template") == True:
            template = self.env['building.purchase.need'].search([('is_template', '=', True)], limit=1)
            check_line_number_duplication = self.env['building.purchase.need.ressource.humain'].search([('line_number', '=', self.line_number), ('section_id', '=', self.section_id.id), ('need_id', '=', template.id)])

            if check_line_number_duplication:
                raise UserError(_('Attention!: Il y a une ligne avec le même numéro'))
            
            self.identification_number = f"{self.section_id.identification_number}.{self.line_number}"

    def name_get(self):
        result = []
        for line in self:
            name = line.name
            if line.job_id:
                name = line.job_id.name
            result.append((line.id, name if name else "Faux"))
        return result

    def _compute_quantity_available(self):
        for line in self:
            assigned_lines_count = self.env["hr.assignment.line"].search_count([
                ("request_line_id.site_id", "=", line.site_id.id),
                ("job_id", "=", line.job_id.id),
                ("state", "in", ["planned", "open"])
            ])
            line.quantity_available = line.quantity - assigned_lines_count

    def _compute_duration_available(self):
        for line in self:
            requested_lines = self.env["hr.assignment.request.line"].search([("site_id", "=", line.site_id.id), ("job_id", "=", line.job_id.id)])
            duration_requested = sum(requested_lines.filtered(lambda l: l.state != "done").mapped("duration_requested"))
            duration_assigned = sum(requested_lines.filtered(lambda l: l.state == "done").mapped("duration_assigned"))
            duration_rejected = sum(requested_lines.filtered(lambda l: l.state == "rejected" and l.request_id.state == "done").mapped("duration_requested"))
            line.duration_available = line.duree_j - duration_requested - duration_assigned + duration_rejected

    def _compute_volume(self):
        for line in self:
            assignment_lines = self.env["hr.assignment.line"].search([
                ("job_id", "=", line.job_id.id),
                ("assignment_id.site_id", "=", line.site_id.id),
                ("type", "=", "daily"),
            ])
            line.volume_clocked = sum(assignment_lines.mapped("volume_clocked"))
            line.volume_available = line.duree_j - line.volume_clocked

    need_id = fields.Many2one('building.purchase.need', string='Affaire', ondelete="cascade")
    job_id = fields.Many2one('hr.job', string='Ressource humain', ondelete="restrict")
    name =  fields.Char(string='Description') 
    uom_id = fields.Many2one('uom.uom', string='UDM', default=lambda self: self.env['uom.uom'].search([('name', '=', 'Heures')]), ondelete="restrict")
    quantity =  fields.Float(string='Nombre de personnes')
    quantity_ordered =  fields.Float(string='Quantité Affectée', compute='_compute_ordered_remaining_quantity')
    quantity_remaining =  fields.Float(string='Quantité Restante', compute='_compute_ordered_remaining_quantity')
    quantity_requested =  fields.Float(string='Quantité Demandée', compute='_compute_ordered_remaining_quantity')
    duree =  fields.Float(string='Durée(Mois)')
    duree_j =  fields.Float(string='Durée')
    duree_h =  fields.Float(string='Heures de travail/J', default=8)
    price_unit =  fields.Float(string='Prix HT')
    price_subtotal =  fields.Float(string='Prix Total', readonly=False, store=True, compute='_compute_price_subtotal')
    type_resource = fields.Selection([
        ('supervisor', "Encadrement"),
        ('executor', "Main-d’œuvre")], default='')
    profile_id = fields.Many2one('hr.job.profile', string='Profil', ondelete="restrict")
    profile_id_integer = fields.Integer(string='Profil', related='profile_id.id')

    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    sequence = fields.Integer(string='Sequence', default=1)
    sequence_num = fields.Integer(string='Sequence', default=1)
    sequence_realted = fields.Integer(string='Séquence', compute='_compute_sequence', store=True, readonly=True)
    site_id = fields.Many2one('building.site', string='Affaire',related='need_id.site_id', store=True, readonly=True)
    state = fields.Selection(string='Statut',related='need_id.state', store=True, readonly=True)

    sequence_number = fields.Integer(string="Numéro de séquence")
    line_number = fields.Integer(string="Numéro de ligne")
    identification_number = fields.Char(string="Identifiant")
    sequence_number_parent = fields.Integer(string="Numéro de séquence parent", related='template_line_id.sequence_number', default=0)
    line_number_parent = fields.Integer(string="Numéro de ligne parent", related='template_line_id.line_number', default=0)
    identification_number_parent = fields.Char(string="Identifiant parent", readonly=True, related='template_line_id.identification_number', default=0)
    section_ids = fields.One2many('building.purchase.need.ressource.humain', 'section_id', string='Sous-sections')
    section_id = fields.Many2one('building.purchase.need.ressource.humain', string='Section parente', ondelete='restrict')
    template_line_id = fields.Many2one('building.purchase.need.ressource.humain', string='Ligne template', ondelete='restrict')
    is_activated = fields.Boolean(string="Act.", default=True)

    quantity_available = fields.Float("Quantité disponible", compute="_compute_quantity_available")
    duration_available = fields.Float("Durée disponible", compute="_compute_duration_available")
    volume_available = fields.Float("Volume disponible", compute="_compute_volume")
    volume_clocked = fields.Float("Volume disponible", compute="_compute_volume")
    # con = fields.Float("")

    @api.onchange('job_id')
    def _onchange_product_id(self):
        if self.job_id:
            # self.name = self.job_id.name
            self.uom_id = self.job_id.uom_id.id
            self.price_unit = self.job_id.cost

    def write(self, vals):
        res = super(building_purchase_need_rh, self).write(vals)

        
        

class building_purchase_need_line(models.Model):
    _name = 'building.purchase.need.line'
    _description = "Lignes des besoins"
    _order = "sequence_number,line_number"

    is_from_template = fields.Boolean(string="Provenant du template", compute='_compute_is_from_template')

    def _compute_is_from_template(self):
        for line in self:
            if line.need_id.is_template:
                line.is_from_template = self.search_count([('template_line_id', '=', line.id)]) > 0
            else:
                line.is_from_template = False
   
    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.quantity = line.quantity if line.quantity else 0
            line.price_unit = line.price_unit if line.price_unit else 0
            line.price_subtotal = line.quantity * line.price_unit

    @api.depends('type_produit')
    def _compute_type_product_selected(self):
        type_product_selected = ''
        for line in self:
            if line.type_produit:
                if line.type_produit == 'material':
                    line.type_produit_selected = 'product'
                if line.type_produit == 'conso':
                    line.type_produit_selected = 'consu'

    def _compute_ordered_remaining_quantity(self):
        for line in self:
            qty_ordered = 0
            orders = self.env['purchase.order'].search([('site_id', '=', line.site_id.id), ('state', '=', 'purchase')])
            order_lines = self.env['purchase.order.line'].search([('order_id', 'in', orders.ids), ('product_id', '=', line.product_id.id)])
            for o_line in order_lines:
                qty_ordered = qty_ordered + o_line.product_qty
            line.quantity_ordered = qty_ordered
            line.quantity_remaining = line.quantity - qty_ordered
    
    def _compute_receved_quantity(self):
        for line in self:
            moves = self.env['stock.picking'].search([('site_id', '=', line.site_id.id), ('location_dest_id', '=', line.site_id.location_id.id), ('state', '=', 'done')])
            quantity_receved = 0
            for move in moves:
                for mline in move.move_line_ids_without_package:
                    if mline.product_id.id == line.product_id.id:
                        quantity_receved = quantity_receved + mline.qty_done
            line.quantity_receved = quantity_receved
            line.quantity_to_receve = line.quantity - quantity_receved
    
    def _compute_available_quantity(self):
        for line in self:
            requested = self.env["purchase.request.line"].search([("site_id", "=", line.site_id.id), ("product_id", "=", line.product_id.id), ("state", "!=", "canceled")])
            line.available_quantity = line.quantity - sum(requested.mapped("product_qty"))

    @api.depends('sequence')
    def _compute_sequence(self):
        for line in self:
            line.sequence_realted = line.sequence

    @api.onchange('line_number')
    def _onchange_line(self):
        if self._context.get("is_template") == True:
            template = self.env['building.purchase.need'].search([('is_template', '=', True)], limit=1)
            check_line_number_duplication = self.env['building.purchase.need.line'].search([('line_number', '=', self.line_number), ('section_id', '=', self.section_id.id), ('need_id', '=', template.id)])

            if check_line_number_duplication:
                raise UserError(_('Attention!: Il y a une ligne avec le même numéro'))
            
            self.identification_number = f"{self.section_id.identification_number}.{self.line_number}"

    def name_get(self):
        result = []
        for line in self:
            name = line.name
            if line.product_id:
                name = line.product_id.name
            result.append((line.id, name if name else "Faux"))
        return result

    need_id = fields.Many2one('building.purchase.need', string='Affaire', ondelete="cascade")
    product_id = fields.Many2one('product.product', string='Article', domain=[('purchase_ok', '=', True)], ondelete="restrict")
    name =  fields.Char(string='Description') 
    uom_id = fields.Many2one('uom.uom', string='UDM', ondelete="restrict")
    quantity =  fields.Float(string='Quantité')
    quantity_ordered =  fields.Float(string='Quantité Commandée', compute='_compute_ordered_remaining_quantity')
    quantity_remaining =  fields.Float(string='Quantité Restante', compute='_compute_ordered_remaining_quantity')
    quantity_receved = fields.Float(string='Quantité Receptionée', compute='_compute_receved_quantity')
    quantity_to_receve = fields.Float(string='Quantité A Receptionée', compute='_compute_receved_quantity')
    price_unit =  fields.Float(string='Prix HT')
    price_subtotal =  fields.Float(string='Prix Total', readonly=False, store=True, compute='_compute_price_subtotal')
    type_produit = fields.Selection([
        ('material', "Fourniture"),
        ('conso', "Consommable")], default='')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    sequence = fields.Integer(string='Sequence', default=1)
    sequence_num = fields.Integer(string='Sequence', default=1)
    sequence_realted = fields.Integer(string='Séquence', compute='_compute_sequence', store=True, readonly=True)
    site_id = fields.Many2one('building.site', string='Affaire',related='need_id.site_id', store=True, readonly=False)
    state = fields.Selection(string='Statut',related='need_id.state', store=True, readonly=False)
    type_produit_selected =  fields.Char(string='Type de produit', readonly=False, store=True, compute='_compute_type_product_selected')

    sequence_number = fields.Integer(string="Numéro de séquence")
    line_number = fields.Integer(string="Numéro de ligne")
    identification_number = fields.Char(string="Identifiant")
    sequence_number_parent = fields.Integer(string="Numéro de séquence parent", related='template_line_id.sequence_number', default=0)
    line_number_parent = fields.Integer(string="Numéro de ligne parent", related='template_line_id.line_number', default=0)
    identification_number_parent = fields.Char(string="Identifiant parent", readonly=True, related='template_line_id.identification_number', default=0)
    section_ids = fields.One2many('building.purchase.need.line', 'section_id', string='Sous-sections')
    section_id = fields.Many2one('building.purchase.need.line', string='Section parente', ondelete='restrict')
    template_line_id = fields.Many2one('building.purchase.need.line', string='Ligne template', ondelete='restrict')
    is_activated = fields.Boolean(string="Act.", default=True)

    available_quantity = fields.Float("Quantité disponible", compute="_compute_available_quantity")
    # con = fields.Float("")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            # self.name = self.product_id.name
            self.uom_id = self.product_id.uom_id.id
            self.price_unit = self.product_id.reference_price

class building_purchase_need_equipment(models.Model):

    _name = 'building.purchase.need.equipment'
    _description = "equipment"
    _order = "sequence_number,line_number"

    is_from_template = fields.Boolean(string="Provenant du template", compute='_compute_is_from_template')

    def _compute_is_from_template(self):
        for line in self:
            if line.need_id.is_template:
                line.is_from_template = self.search_count([('template_line_id', '=', line.id)]) > 0
            else:
                line.is_from_template = False
   
    @api.depends('quantity', 'duree_j', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.quantity = line.quantity if line.quantity else 0
            line.duree_j = line.duree_j if line.duree_j else 0
            line.price_unit = line.price_unit if line.price_unit else 0
            line.price_subtotal = line.quantity*line.duree_j*line.price_unit

    def _compute_ordered_remaining_quantity(self):
        for line in self:
            qty_ordered = self.env['building.assignment.line'].search_count([('site_id', '=', line.site_id.id), ('state', '=', 'open'), ('categ_fleet_id', '=', line.equipment_category_id.id)])
            line.quantity_ordered = qty_ordered
            line.quantity_remaining = line.quantity - qty_ordered
            requested_lines = self.env['maintenance.request.resource.material.line'].search([('site_id', '=', line.site_id.id), ('state', '!=', 'draft'), ('categ_vec_id', '=', line.equipment_category_id.id)])
            quantity_requested = 0
            if requested_lines:
                quantity_requested = sum(line.qty for line in requested_lines)
            line.quantity_requested = quantity_requested

    @api.depends('sequence')
    def _compute_sequence(self):
        for line in self:
            line.sequence_realted = line.sequence

    @api.onchange('line_number')
    def _onchange_line(self):
        if self._context.get("is_template") == True:
            template = self.env['building.purchase.need'].search([('is_template', '=', True)], limit=1)
            check_line_number_duplication = self.env['building.purchase.need.equipment'].search([('line_number', '=', self.line_number), ('section_id', '=', self.section_id.id), ('need_id', '=', template.id)])

            if check_line_number_duplication:
                raise UserError(_('Attention!: Il y a une ligne avec le même numéro'))
            
            self.identification_number = f"{self.section_id.identification_number}.{self.line_number}"

    need_id = fields.Many2one('building.purchase.need', string='Affaire', ondelete="cascade")
    site_id = fields.Many2one('building.site', string='Affaire',related='need_id.site_id', store=True, readonly=True)
    equipment_category_id = fields.Many2one('maintenance.vehicle.category', string='Matériel', ondelete="restrict")
    name =  fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', string='UDM', ondelete="restrict")
    quantity =  fields.Float(string='Quantité')
    quantity_ordered =  fields.Float(string='Quantité Affectée', compute='_compute_ordered_remaining_quantity')
    quantity_remaining =  fields.Float(string='Quantité Restante', compute='_compute_ordered_remaining_quantity')
    quantity_requested =  fields.Float(string='Quantité Demandée', compute='_compute_ordered_remaining_quantity')
    duree =  fields.Float(string='Durée(Mois)')
    duree_j =  fields.Float(string='Durée')
    duree_h =  fields.Float(string='Heures de travail/J', default=9)
    price_unit =  fields.Float(string='Prix HT', digits=(15,5))
    price_subtotal =  fields.Float(string='Prix Total', readonly=False, store=True, compute='_compute_price_subtotal', digits=(15,5))
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    sequence = fields.Integer(string='Sequence', default=1)
    sequence_num = fields.Integer(string='Sequence', default=1)
    sequence_realted = fields.Integer(string='Séquence', compute='_compute_sequence', store=True, readonly=True)
    site_id = fields.Many2one('building.site', string='Affaire',related='need_id.site_id', store=True, readonly=True)
    state = fields.Selection(string='Statut',related='need_id.state', store=True, readonly=True)

    sequence_number = fields.Integer(string="Numéro de séquence")
    line_number = fields.Integer(string="Numéro de ligne")
    identification_number = fields.Char(string="Identifiant")
    sequence_number_parent = fields.Integer(string="Numéro de séquence parent", related='template_line_id.sequence_number', default=0)
    line_number_parent = fields.Integer(string="Numéro de ligne parent", related='template_line_id.line_number', default=0)
    identification_number_parent = fields.Char(string="Identifiant parent", readonly=True, related='template_line_id.identification_number', default=0)
    section_ids = fields.One2many('building.purchase.need.equipment', 'section_id', string='Sous-sections')
    section_id = fields.Many2one('building.purchase.need.equipment', string='Section parente', ondelete='restrict')
    template_line_id = fields.Many2one('building.purchase.need.equipment', string='Ligne template', ondelete='restrict')
    is_activated = fields.Boolean(string="Act.", default=True)
    available_quantity = fields.Float("Qté disponible", compute="_compute_available_quantity")

    def _compute_available_quantity(self):
        for line in self:
            requested = self.env["fleet.request.line"].search([
                ("site_id", "=", line.site_id.id),
                ("equipment_id", "=", line.equipment_id.id),
                ("state", "!=", "canceled")
            ])
            line.available_quantity = line.quantity - sum(requested.mapped("quantity"))

    @api.onchange('equipment_category_id')
    def _onchange_equipment_category_id(self):
        if self.equipment_category_id:
            self.name = self.equipment_category_id.name
            self.uom_id = self.equipment_category_id.uom_h_id.id
            self.price_unit = self.equipment_category_id.cost_h

    def write(self, values):
        result = super(building_purchase_need_equipment, self).write(values)
        if self.need_id.is_template:
            need = self.need_id
            diesel_consumption_id = need.diesel_consumption_ids.filtered(lambda line: line.origin_id == self)
            if "equipment_category_id" in values:
                if values.get("equipment_category_id"):
                    diesel_consumption_id.equipment_id = f"{self.equipment_category_id._name},{values.get('equipment_category_id')}"
                else:
                    diesel_consumption_id.equipment_category_id = False
                del values["equipment_category_id"]
            if "uom_id" in values:
                diesel_consumption_id.uom_id = values.get("uom_id")
                del values["uom_id"]
            if "duree_j" in values: del values["duree_j"]
            diesel_consumption_id.write(values)
        return result
    
    def unlink(self):
        for rec in self:
            diesel_line = rec.env["building.purchase.need.diesel.consumption"].search([
                ("need_id", "=", rec.need_id.id),
                ("origin_id", "=", f"{rec._name},{rec.template_line_id.id}")
            ])
            diesel_line.unlink()

        return super().unlink()


class building_purchase_need_small_equipment(models.Model):
    _name = 'building.purchase.need.small.equipment'
    _description = "Lignes des petit matériels"
    _order = "sequence_number,line_number"


    is_from_template = fields.Boolean(string="Provenant du template", compute='_compute_is_from_template')

    def _compute_is_from_template(self):
        for line in self:
            if line.need_id.is_template:
                line.is_from_template = self.search_count([('template_line_id', '=', line.id)]) > 0
            else:
                line.is_from_template = False
   
    @api.depends('quantity', 'duree', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.quantity = line.quantity if line.quantity else 0
            line.price_unit = line.price_unit if line.price_unit else 0
            line.duree = line.duree if line.duree else 0
            line.price_subtotal = line.quantity * line.duree * line.price_unit

    @api.onchange('line_number')
    def _onchange_line(self):
        if self._context.get("is_template") == True:
            template = self.env['building.purchase.need'].search([('is_template', '=', True)], limit=1)
            check_line_number_duplication = self.env['building.purchase.need.small.equipment'].search([('line_number', '=', self.line_number), ('section_id', '=', self.section_id.id), ('need_id', '=', template.id)])

            if check_line_number_duplication:
                raise UserError(_('Attention!: Il y a une ligne avec le même numéro'))
            
            self.identification_number = f"{self.section_id.identification_number}.{self.line_number}"

    def name_get(self):
        result = []
        for line in self:
            name = line.name
            if line.equipment_id:
                name = line.equipment_id.name
            result.append((line.id, name if name else "Faux"))
        return result

    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    need_id = fields.Many2one('building.purchase.need', string='Affaire', ondelete="cascade")
    site_id = fields.Many2one('building.site', string='Affaire',related='need_id.site_id', store=True, readonly=True)
    equipment_id = fields.Many2one('product.product', string='Petit matériel', ondelete="restrict")
    name =  fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', string='UDM', ondelete="restrict")
    duree =  fields.Float(string='Durée')
    quantity =  fields.Float(string='Quantité')
    price_unit =  fields.Float(string='Prix HT')
    price_subtotal =  fields.Float(string='Prix Total', readonly=False, store=True, compute='_compute_price_subtotal')
    category_id = fields.Many2one('product.category', string='Catégorie', ondelete="restrict")
    equipment_ids = fields.Many2many('product.product', string='Petit matériel', compute='_compute_equipment_ids')

    sequence_number = fields.Integer(string="Numéro de séquence")
    line_number = fields.Integer(string="Numéro de ligne")
    identification_number = fields.Char(string="Identifiant")
    sequence_number_parent = fields.Integer(string="Numéro de séquence parent", related='template_line_id.sequence_number', default=0)
    line_number_parent = fields.Integer(string="Numéro de ligne parent", related='template_line_id.line_number', default=0)
    identification_number_parent = fields.Char(string="Identifiant parent", readonly=True, related='template_line_id.identification_number', default=0)
    section_ids = fields.One2many('building.purchase.need.small.equipment', 'section_id', string='Sous-sections')
    section_id = fields.Many2one('building.purchase.need.small.equipment', string='Section parente', ondelete='restrict')
    template_line_id = fields.Many2one('building.purchase.need.small.equipment', string='Ligne template', ondelete='restrict')
    is_activated = fields.Boolean(string="Act.", default=True)

    def _compute_equipment_ids(self):
        for line in self:
            products = self.env['product.product'].search([
                ('categ_id', '=', line.section_id.category_id.id),
                ('categ_id.category_type', '=', 'small_equipment')
            ])

            used_products = self.env['building.purchase.need.small.equipment'].search([
                ('equipment_id', 'in', products.ids),
                ('need_id', '=', line.need_id.id),
            ]).mapped('equipment_id')

            line.equipment_ids = products - self.env['product.product'].browse(used_products.ids)

    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        if self.equipment_id:
            self.name = self.equipment_id.name
            self.uom_id = self.equipment_id.uom_id.id
            self.price_unit = self.equipment_id.standard_price

    def write(self, values):
        result = super(building_purchase_need_small_equipment, self).write(values)
        if self.need_id.is_template:
            need = self.need_id
            diesel_consumption_id = need.diesel_consumption_ids.filtered(lambda line: line.origin_id == self)
            if "equipment_id" in values:
                if values.get("equipment_id"):
                    diesel_consumption_id.equipment_id = f"{self.equipment_id._name},{values.get('equipment_id')}"
                else:
                    diesel_consumption_id.equipment_id = False
                del values["equipment_id"]
            if "uom_id" in values:
                diesel_consumption_id.uom_id = values.get("uom_id")
                del values["uom_id"]
            if "duree" in values: del values["duree"]
            diesel_consumption_id.write(values)
        return result
    
    def unlink(self):
        diesel_line = self.env["building.purchase.need.diesel.consumption"].search([("need_id", "=", self.need_id.id), ("origin_id", "=", f"{self._name},{self.template_line_id.id}")])
        diesel_line.unlink()
        return super(building_purchase_need_small_equipment, self).unlink()

                                   
class building_purchase_need_mini_equipment(models.Model):
    _name = 'building.purchase.need.mini.equipment'
    _description = "equipment"
    _order = "sequence_number,line_number"


    is_from_template = fields.Boolean(string="Provenant du template", compute='_compute_is_from_template')

    def _compute_is_from_template(self):
        for line in self:
            if line.need_id.is_template:
                line.is_from_template = self.search_count([('template_line_id', '=', line.id)]) > 0
            else:
                line.is_from_template = False
   

    @api.depends('quantity', 'duree_h', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.quantity = line.quantity if line.quantity else 0
            line.duree_j = line.duree_j if line.duree_j else 0
            line.duree_h = line.duree_h if line.duree_h else 0
            line.price_unit = line.price_unit if line.price_unit else 0
            line.price_subtotal = line.quantity*line.duree_j*line.duree_h*line.price_unit

    def _compute_ordered_remaining_quantity(self):
        for line in self:
            # qty_ordered = self.env['building.assignment.line'].search_count([('site_id', '=', line.site_id.id), ('state', '=', 'open'), ('categ_maintenance_id', '=', line.equipment_id.id)])
            # line.quantity_ordered = qty_ordered
            # line.quantity_remaining = line.quantity - qty_ordered
            # requested_lines = self.env['maintenance.request.resource.material.line'].search([('site_id', '=', line.site_id.id), ('state', '!=', 'draft'), ('categ_id', '=', line.equipment_id.id)])
            # quantity_requested = 0
            # if requested_lines:
            #     quantity_requested = sum(line.qty for line in requested_lines)
            # line.quantity_requested = quantity_requested

            line.quantity_ordered = 0
            line.quantity_remaining = 0
            line.quantity_requested = 0

    @api.depends('sequence')
    def _compute_sequence(self):
        for line in self:
            line.sequence_realted = line.sequence

    @api.onchange('line_number')
    def _onchange_line(self):
        if self._context.get("is_template") == True:
            template = self.env['building.purchase.need'].search([('is_template', '=', True)], limit=1)
            check_line_number_duplication = self.env['building.purchase.need.mini.equipment'].search([('line_number', '=', self.line_number), ('section_id', '=', self.section_id.id), ('need_id', '=', template.id)])

            if check_line_number_duplication:
                raise UserError(_('Attention!: Il y a une ligne avec le même numéro'))
            
            self.identification_number = f"{self.section_id.identification_number}.{self.line_number}"
    
    def _compute_available_quantity(self):
        for line in self:
            requested = self.env["purchase.request.line"].search([("site_id", "=", line.site_id.id), ("product_id", "=", line.product_id.id), ("state", "!=", "canceled")])
            line.available_quantity = line.quantity - sum(requested.mapped("product_qty"))

    need_id = fields.Many2one('building.purchase.need', string='Affaire', ondelete="cascade")
    category_id = fields.Many2one("product.category", string="Catégorie")
    product_id = fields.Many2one("product.product", string="Outillage")
    name =  fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', string='UDM', ondelete="restrict")
    quantity =  fields.Float(string='Quantité')
    quantity_ordered =  fields.Float(string='Quantité Affectée', compute='_compute_ordered_remaining_quantity')
    quantity_remaining =  fields.Float(string='Quantité Restante', compute='_compute_ordered_remaining_quantity')
    quantity_requested =  fields.Float(string='Quantité Demandée', compute='_compute_ordered_remaining_quantity')
    duree =  fields.Float(string='Durée(Mois)')
    duree_j =  fields.Float(string='Durée(Jours)', default=1)
    duree_h =  fields.Float(string='Heures de travail/J', default=1)
    price_unit =  fields.Float(string='Prix HT')
    price_subtotal =  fields.Float(string='Prix Total', readonly=False, store=True, compute='_compute_price_subtotal')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    description = fields.Char(string='Description')
    sequence = fields.Integer(string='Sequence', default=1)
    sequence_num = fields.Integer(string='Sequence', default=1)
    sequence_realted = fields.Integer(string='Séquence', compute='_compute_sequence', store=True, readonly=True)
    site_id = fields.Many2one('building.site', string='Affaire',related='need_id.site_id', store=True, readonly=True)
    state = fields.Selection(string='Statut',related='need_id.state', store=True, readonly=True)

    sequence_number = fields.Integer(string="Numéro de séquence")
    line_number = fields.Integer(string="Numéro de ligne")
    identification_number = fields.Char(string="Identifiant")
    sequence_number_parent = fields.Integer(string="Numéro de séquence parent", related='template_line_id.sequence_number', default=0)
    line_number_parent = fields.Integer(string="Numéro de ligne parent", related='template_line_id.line_number', default=0)
    identification_number_parent = fields.Char(string="Identifiant parent", readonly=True, related='template_line_id.identification_number', default=0)
    section_ids = fields.One2many('building.purchase.need.mini.equipment', 'section_id', string='Sous-sections')
    section_id = fields.Many2one('building.purchase.need.mini.equipment', string='Section parente', ondelete='restrict')
    template_line_id = fields.Many2one('building.purchase.need.mini.equipment', string='Ligne template', ondelete='restrict')
    is_activated = fields.Boolean(string="Act.", default=True)

    available_quantity = fields.Float("Quantité disponible", compute="_compute_available_quantity")
    # con = fields.Float("")


class building_purchase_need_service_provision(models.Model):

    _name = 'building.purchase.need.service.provision'
    _description = "service provision"
    _order = "sequence_number,line_number"


    is_from_template = fields.Boolean(string="Provenant du template", compute='_compute_is_from_template')

    def _compute_is_from_template(self):
        for line in self:
            if line.need_id.is_template:
                line.is_from_template = self.search_count([('template_line_id', '=', line.id)]) > 0
            else:
                line.is_from_template = False
   
    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.quantity = line.quantity if line.quantity else 0
            line.price_unit = line.price_unit if line.price_unit else 0
            line.price_subtotal = line.quantity*line.price_unit

    def _compute_ordered_remaining_price_subtotal(self):
        for line in self:
            price_subtotal_ordered = 0
            orders = self.env['purchase.order'].search([('site_id', '=', line.site_id.id), ('state', '=', 'purchase')])
            order_lines = self.env['purchase.order.line'].search([('order_id', 'in', orders.ids), ('product_id', '=', line.product_id.id)])
            for o_line in order_lines:
                price_subtotal_ordered = price_subtotal_ordered + o_line.price_subtotal
            line.price_subtotal_ordered = price_subtotal_ordered
            line.price_subtotal_remaining = line.price_subtotal - price_subtotal_ordered

    @api.depends('sequence')
    def _compute_sequence(self):
        for line in self:
            line.sequence_realted = line.sequence

    @api.onchange('line_number')
    def _onchange_line(self):
        if self._context.get("is_template") == True:
            template = self.env['building.purchase.need'].search([('is_template', '=', True)], limit=1)
            check_line_number_duplication = self.env['building.purchase.need.service.provision'].search([('line_number', '=', self.line_number), ('section_id', '=', self.section_id.id), ('need_id', '=', template.id)])

            if check_line_number_duplication:
                raise UserError(_('Attention!: Il y a une ligne avec le même numéro'))
            
            self.identification_number = f"{self.section_id.identification_number}.{self.line_number}"

    def name_get(self):
        result = []
        for line in self:
            name = line.name
            if line.product_id:
                name = line.product_id.name
            result.append((line.id, name if name else "Faux"))
        return result
    
    def _compute_available_quantity(self):
        for line in self:
            requested = self.env["purchase.request.line"].search([("site_id", "=", line.site_id.id), ("product_id", "=", line.product_id.id), ("state", "!=", "canceled")])
            line.available_quantity = line.quantity - sum(requested.mapped("product_qty"))

    need_id = fields.Many2one('building.purchase.need', string='Affaire', ondelete="cascade")
    product_id = fields.Many2one('product.product', string='Article', domain=[('type', '=', 'service'), ('purchase_ok', '=', True)], ondelete="restrict")
    name =  fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', string='UDM', ondelete="restrict")
    quantity =  fields.Float(string='Quantité')
    price_unit =  fields.Float(string='Prix HT')
    price_subtotal =  fields.Float(string='Total HT', readonly=False, store=True, compute='_compute_price_subtotal')
    price_subtotal_ordered =  fields.Float(string='HT Consomé', compute='_compute_ordered_remaining_price_subtotal')
    price_subtotal_remaining =  fields.Float(string='HT Restant', compute='_compute_ordered_remaining_price_subtotal')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    sequence = fields.Integer(string='Sequence', default=1)
    sequence_num = fields.Integer(string='Sequence', default=1)
    sequence_realted = fields.Integer(string='Séquence', compute='_compute_sequence', store=True, readonly=True)
    site_id = fields.Many2one('building.site', string='Affaire',related='need_id.site_id', store=True, readonly=True)
    state = fields.Selection(string='Statut',related='need_id.state', store=True, readonly=True)

    sequence_number = fields.Integer(string="Numéro de séquence")
    line_number = fields.Integer(string="Numéro de ligne")
    identification_number = fields.Char(string="Identifiant")
    sequence_number_parent = fields.Integer(string="Numéro de séquence parent", related='template_line_id.sequence_number', default=0)
    line_number_parent = fields.Integer(string="Numéro de ligne parent", related='template_line_id.line_number', default=0)
    identification_number_parent = fields.Char(string="Identifiant parent", readonly=True, related='template_line_id.identification_number', default=0)
    section_ids = fields.One2many('building.purchase.need.service.provision', 'section_id', string='Sous-sections')
    section_id = fields.Many2one('building.purchase.need.service.provision', string='Section parente', ondelete='restrict')
    template_line_id = fields.Many2one('building.purchase.need.service.provision', string='Ligne template', ondelete='restrict')
    is_activated = fields.Boolean(string="Act.", default=True)

    available_quantity = fields.Float("Quantité disponible", compute="_compute_available_quantity")
    # con = fields.Float("")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            # self.name = self.product_id.name
            self.uom_id = self.product_id.uom_id.id
            self.price_unit = self.product_id.reference_price

class building_purchase_need_diesel_consumption(models.Model):
    _name = 'building.purchase.need.diesel.consumption'
    _description = "Gasoil"
    _order = "origin,sequence_number,line_number"

    @api.onchange('line_number')
    def _onchange_line(self):
        if self._context.get("is_template") == True:
            template = self.env['building.purchase.need'].search([('is_template', '=', True)], limit=1)
            check_line_number_duplication = self.env['building.purchase.need.diesel.consumption'].search([('line_number', '=', self.line_number), ('section_id', '=', self.section_id.id), ('need_id', '=', template.id)])

            if check_line_number_duplication:
                raise UserError(_('Attention!: Il y a une ligne avec le même numéro'))
            
            self.identification_number = f"{self.section_id.identification_number}.{self.line_number}"

    need_id = fields.Many2one("building.purchase.need", string="Affaire", ondelete="cascade")
    site_id = fields.Many2one("building.site", string="Affaire", related="need_id.site_id")
    state = fields.Selection("Statut", related="need_id.state")

    origin = fields.Selection(string="Origine", selection=[
        ("building.purchase.need.equipment", "Matériels"),
        ("building.purchase.need.small.equipment", "Petits Matériels"),
    ])
    origin_id = fields.Reference(string="Origine", selection=[
        ("building.purchase.need.equipment", "Matériels"),
        ("building.purchase.need.small.equipment", "Petits Matériels"),
    ])
    equipment_id = fields.Reference(string="Resource", selection=[
        ("maintenance.vehicle.category", "Matériel"),
        ("fleet.vehicle", "Petit Matériel"),
    ])
    name =  fields.Char(string="Description")
    quantity = fields.Float("Quantité", compute="_compute_from_origin")
    duration = fields.Float("Durée", compute="_compute_from_origin")

    def _compute_from_origin(self):
        for record in self:
            record.quantity = record.quantity
            record.duration = record.duration
            if not record.need_id.is_template:
                origin_line = self.env[record.origin].search([("need_id", "=", record.need_id.id), ("template_line_id", "=", record.origin_id.id)], limit=1)
                quantity, duration = (origin_line.quantity, origin_line[record.origin == "building.purchase.need.equipment" and "duree_j" or "duree"])
                record.quantity = quantity
                record.duration = duration

    uom_id = fields.Many2one("uom.uom", string="UDM", ondelete="restrict")
    consumption = fields.Float(string="Consommation(L/J)")
    price_unit =  fields.Float(string="PU")
    price_subtotal =  fields.Float(string="Total")

    display_type = fields.Selection(default=False, selection=[
        ("line_section", "Section"),
        ("line_note", "Note")
    ])
    sequence_number = fields.Integer(string="Numéro de séquence")
    line_number = fields.Integer(string="Numéro de ligne")
    identification_number = fields.Char(string="Identifiant")
    sequence_number_parent = fields.Integer("Numéro de séquence parent", related="template_line_id.sequence_number", default=0)
    line_number_parent = fields.Integer("Numéro de ligne parent", related="template_line_id.line_number", default=0)
    identification_number_parent = fields.Char("Identifiant parent", readonly=True, related="template_line_id.identification_number", default=0)
    section_ids = fields.One2many("building.purchase.need.diesel.consumption", "section_id", string="Sous-sections")
    section_id = fields.Many2one("building.purchase.need.diesel.consumption", string="Section parente", ondelete="restrict")
    template_line_id = fields.Many2one("building.purchase.need.diesel.consumption", string="Ligne template", ondelete="restrict")
    is_activated = fields.Boolean(string="Act.", default=True)

    is_from_template = fields.Boolean(string="Provenant du template", compute='_compute_is_from_template')

    def _compute_is_from_template(self):
        for line in self:
            if line.need_id.is_template:
                line.is_from_template = self.search_count([('template_line_id', '=', line.id)]) > 0
            else:
                line.is_from_template = False


class building_purchase_need_coff_echa(models.Model):

    _name = 'building.purchase.need.coffecha'
    _description = "Lignes des besoins"
    _order = "sequence_number,line_number"

    @api.depends('quantity', 'duree', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.quantity = line.quantity if line.quantity else 0
            line.duree = line.duree if line.duree else 0
            line.price_unit = line.price_unit if line.price_unit else 0
            line.price_subtotal = line.quantity*line.duree*line.price_unit

    def _compute_ordered_remaining_quantity(self):
        for line in self:
            # internal_type = elf.env['stock.picking.type'].search([('sequence_code', '=', 'INT')])
            # moves = self.env['stock.picking'].search([('site_id', '=', line.site_id.id), ('state', '=', 'done'), ('picking_type_id', '=', internal_type.id), ('location_dest_id', '=', line.site_id.location_id.id)])
            moves = self.env['stock.picking'].search([('site_id', '=', line.site_id.id), ('location_dest_id', '=', line.site_id.location_id.id)])
            qty_ordered = 0
            for move in moves:
                for mline in move.move_line_ids_without_package:
                    if mline.product_id.categ_id.is_coffrage:
                        qty_ordered = qty_ordered + mline.qty_done
            line.quantity_ordered = qty_ordered
            line.quantity_remaining = line.quantity - qty_ordered
            requested_lines = self.env['maintenance.request.resource.material.line'].search([('site_id', '=', line.site_id.id), ('state', '!=', 'draft'), ('product_id', '=', line.product_id.id)])
            quantity_requested = 0
            if requested_lines:
                quantity_requested = sum(line.qty for line in requested_lines)
            line.quantity_requested = quantity_requested

    @api.depends('sequence')
    def _compute_sequence(self):
        for line in self:
            line.sequence_realted = line.sequence

    @api.onchange('line_number')
    def _onchange_line(self):
        if self._context.get("is_template") == True:
            template = self.env['building.purchase.need'].search([('is_template', '=', True)], limit=1)
            check_line_number_duplication = self.env['building.purchase.need.coffecha'].search([('line_number', '=', self.line_number), ('section_id', '=', self.section_id.id), ('need_id', '=', template.id)])

            if check_line_number_duplication:
                raise UserError(_('Attention!: Il y a une ligne avec le même numéro'))
            
            self.identification_number = f"{self.section_id.identification_number}.{self.line_number}"

    need_id = fields.Many2one('building.purchase.need', string='Affaire', ondelete="cascade")
    product_id = fields.Many2one('product.product', string='Article', domain=[('is_coffrage', '=', True)])
    name =  fields.Char(string='Description') 
    uom_id = fields.Many2one('uom.uom', string='UDM')
    duree =  fields.Float(string='Durée(mois)')
    quantity =  fields.Float(string='Quantité')
    quantity_ordered =  fields.Float(string='Quantité Affectée', compute='_compute_ordered_remaining_quantity')
    quantity_remaining =  fields.Float(string='Quantité Restante', compute='_compute_ordered_remaining_quantity')
    quantity_requested =  fields.Float(string='Quantité Demandée', compute='_compute_ordered_remaining_quantity')
    price_unit =  fields.Float(string='Prix HT')
    price_subtotal =  fields.Float(string='Prix Total', readonly=False, store=True, compute='_compute_price_subtotal')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    sequence = fields.Integer(string='Sequence', default=1)
    sequence_num = fields.Integer(string='Sequence', default=1)
    sequence_realted = fields.Integer(string='Séquence', compute='_compute_sequence', store=True, readonly=True)
    site_id = fields.Many2one('building.site', string='Affaire',related='need_id.site_id', store=True, readonly=True)
    state = fields.Selection(string='Statut',related='need_id.state', store=True, readonly=True)

    sequence_number = fields.Integer(string="Numéro de séquence")
    line_number = fields.Integer(string="Numéro de ligne")
    identification_number = fields.Char(string="Identifiant")
    sequence_number_parent = fields.Integer(string="Numéro de séquence parent", related='template_line_id.sequence_number', default=0)
    line_number_parent = fields.Integer(string="Numéro de ligne parent", related='template_line_id.line_number', default=0)
    identification_number_parent = fields.Char(string="Identifiant parent", readonly=True, related='template_line_id.identification_number', default=0)
    section_ids = fields.One2many('building.purchase.need.coffecha', 'section_id', string='Sous-sections')
    section_id = fields.Many2one('building.purchase.need.coffecha', string='Section parente', ondelete='restrict')
    template_line_id = fields.Many2one('building.purchase.need.coffecha', string='Ligne template', ondelete='restrict')
    is_activated = fields.Boolean(string="Act.", default=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            # self.name = self.product_id.name
            self.uom_id = self.product_id.uom_id.id
            self.price_unit = self.product_id.reference_price

class building_purchase_need_flow(models.Model):

    _name = 'building.purchase.need.flow'
    _description = "Flux des besoins"
    _order = "date desc"

    need_id = fields.Many2one('building.purchase.need', string='Affaire')
    user_id = fields.Many2one('res.users', string='Utilisateur')
    date = fields.Datetime('Date')
    note =  fields.Char(string='Commentaire')


class BuildingPurchaseNeedFuel(models.Model):
    _name = "building.purchase.need.fuel"
    _description = "Carburant"
    _order = "sequence_number,line_number"
    
    def _compute_available_quantity(self):
        for line in self:
            requested = self.env["purchase.request.line"].search([("site_id", "=", line.site_id.id), ("product_id", "=", line.product_id.id), ("state", "!=", "canceled")])
            line.available_quantity = line.quantity - sum(requested.mapped("product_qty"))

    def name_get(self):
        return [(line.id, line.product_id.name or (line.display_type == "line_section" and line.name) or "Faux") for line in self]

    need_id = fields.Many2one("building.purchase.need", string="Affaire", ondelete="cascade")
    site_id = fields.Many2one("building.site", string="Affaire", related="need_id.site_id")
    state = fields.Selection("Statut", related="need_id.state")

    name =  fields.Char(string="Description")

    category_id = fields.Many2one("product.category", string="Catégorie", domain="[('is_fuel', '=', True)]")
    product_id = fields.Many2one("product.product", string="Article")
    product_ids = fields.Many2many("product.product", string="Domain Article")

    quantity = fields.Float("Quantité")
    available_quantity = fields.Float("Quantité disponible", compute="_compute_available_quantity")
    duration = fields.Float("Durée") # Not used in views
    uom_id = fields.Many2one("uom.uom", string="UDM")
    consumption = fields.Float("Consommation") # Not used in views

    price_unit =  fields.Float("PU")
    price_subtotal = fields.Float(string="Total", compute="_compute_total")

    display_type = fields.Selection(default=False, selection=[
        ("line_section", "Section"),
        ("line_note", "Note")
    ])
    sequence_number = fields.Integer(string="Numéro de séquence")
    line_number = fields.Integer(string="Numéro de ligne")
    identification_number = fields.Char(string="Identifiant")
    sequence_number_parent = fields.Integer("Numéro de séquence parent", related="template_line_id.sequence_number", default=0)
    line_number_parent = fields.Integer("Numéro de ligne parent", related="template_line_id.line_number", default=0)
    identification_number_parent = fields.Char("Identifiant parent", readonly=True, related="template_line_id.identification_number", default=0)
    section_ids = fields.One2many("building.purchase.need.fuel", "section_id", string="Sous-sections")
    section_id = fields.Many2one("building.purchase.need.fuel", string="Section parente", ondelete="restrict")
    template_line_id = fields.Many2one("building.purchase.need.fuel", string="Ligne template", ondelete="restrict")
    is_activated = fields.Boolean(string="Act.", default=True)
    is_from_template = fields.Boolean(string="Provenant du template", compute='_compute_is_from_template')

    @api.depends("duration", "price_unit", "quantity")
    def _compute_total(self):
        for line in self:
            line.price_subtotal = line.price_unit * line.quantity

    @api.onchange("category_id")
    def _onchange_category_id(self):
        self.product_ids = self.env["product.product"].search([("categ_id", "=", self.category_id.id), ("id", "not in", self.need_id.fuel_ids.mapped("product_id").ids)])

    def _compute_is_from_template(self):
        for line in self:
            if line.need_id.is_template:
                line.is_from_template = self.search_count([('template_line_id', '=', line.id)]) > 0
            else:
                line.is_from_template = False