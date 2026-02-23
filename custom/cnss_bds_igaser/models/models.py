# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class cnss_bds_igaser(models.Model):
#     _name = 'cnss_bds_igaser.cnss_bds_igaser'
#     _description = 'cnss_bds_igaser.cnss_bds_igaser'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
