from odoo import fields, models, api
from odoo.exceptions import UserError


class UpdateSectionSectionNumber(models.TransientModel):
  _name = "update.section.sequence.number.wizard"

  @api.onchange('building_purchase_need_site_installation')
  def _onchange_building_purchase_need_site_installation(self):
    return {"domain": {"building_purchase_need_site_installation": [('need_id', '=', self.env.context.get('active_id')), ('display_type', '=', 'line_section')]}}
  
  @api.onchange('building_purchase_need_ressource_humain')
  def _onchange_building_purchase_need_ressource_humain(self):
    return {"domain": {"building_purchase_need_ressource_humain": [('need_id', '=', self.env.context.get('active_id')), ('display_type', '=', 'line_section')]}}
  
  @api.onchange('building_purchase_need_line')
  def _onchange_building_purchase_need_line(self):
    return {"domain": {"building_purchase_need_line": [('need_id', '=', self.env.context.get('active_id')), ('display_type', '=', 'line_section')]}}
  
  @api.onchange('building_purchase_need_service_provision')
  def _onchange_building_purchase_need_service_provision(self):
    return {"domain": {"building_purchase_need_service_provision": [('need_id', '=', self.env.context.get('active_id')), ('display_type', '=', 'line_section')]}}
  
  @api.onchange('building_purchase_need_mini_equipment')
  def _onchange_building_purchase_need_mini_equipment(self):
    return {"domain": {"building_purchase_need_mini_equipment": [('need_id', '=', self.env.context.get('active_id')), ('display_type', '=', 'line_section')]}}
  
  @api.onchange('building_purchase_need_equipment')
  def _onchange_building_purchase_need_equipment(self):
    return {"domain": {"building_purchase_need_equipment": [('need_id', '=', self.env.context.get('active_id')), ('display_type', '=', 'line_section')]}}
  
  @api.onchange('building_purchase_need_diesel_consumption')
  def _onchange_building_purchase_need_diesel_consumption(self):
    return {"domain": {"building_purchase_need_diesel_consumption": [('need_id', '=', self.env.context.get('active_id')), ('display_type', '=', 'line_section')]}}
  
  @api.onchange('building_purchase_need_small_equipment')
  def _onchange_building_purchase_need_small_equipment(self):
    return {"domain": {"building_purchase_need_small_equipment": [('need_id', '=', self.env.context.get('active_id')), ('display_type', '=', 'line_section')]}}


  categories = fields.Selection([
    # ('building.purchase.need.site.installation', 'Installation de chantier'),
    ('building.purchase.need.ressource.humain', 'Ressources Humaines'),
    ('building.purchase.need.line', 'Fournitures'),
    ('building.purchase.need.service.provision', 'Prestation de service'),
    ('building.purchase.need.mini.equipment', 'Outillages'),
    ('building.purchase.need.equipment', 'Matériels'),
    ('building.purchase.need.small.equipment', 'Petit Matériels'),
    ('building.purchase.need.diesel.consumption', 'Gasoil')], string='Onglet', required=True, default='building.purchase.need.ressource.humain')
  
  building_purchase_need_site_installation = fields.Many2one('building.purchase.need.site.installation', string='Section Installation de chantier')
  building_purchase_need_ressource_humain = fields.Many2one('building.purchase.need.ressource.humain', string='Section Ressources Humaines')
  building_purchase_need_line= fields.Many2one('building.purchase.need.line', string='Section Fournitures')
  building_purchase_need_service_provision = fields.Many2one('building.purchase.need.service.provision', string='Section Prestation de service')
  building_purchase_need_mini_equipment = fields.Many2one('building.purchase.need.mini.equipment', string='Section Outillages')
  building_purchase_need_equipment= fields.Many2one('building.purchase.need.equipment', string='Section Matériels')
  building_purchase_need_diesel_consumption = fields.Many2one('building.purchase.need.diesel.consumption', string='Section Gasoil')
  building_purchase_need_small_equipment = fields.Many2one('building.purchase.need.small.equipment', string='Section Petit Matériels')

  old_section_sequence_number = fields.Integer(string='Ancien numéro de séquence', required=True)
  new_section_sequence_number = fields.Integer(string='Nouveau numéro de séquence', required=True)

  @api.onchange('building_purchase_need_site_installation', 'building_purchase_need_ressource_humain', 'building_purchase_need_line', 'building_purchase_need_service_provision', 'building_purchase_need_mini_equipment', 'building_purchase_need_equipment', 'building_purchase_need_diesel_consumption', 'building_purchase_need_small_equipment')
  def _set_old_section_sequence_number(self):
    self.old_section_sequence_number = self[self.categories.replace('.', '_')].sequence_number or 0

  def update_section_sequence_number(self):
    categories_identification_number_index = {
    'building.purchase.need.ressource.humain': 1,
    'building.purchase.need.line': 2,
    'building.purchase.need.service.provision': 3,
    'building.purchase.need.mini.equipment': 4,
    'building.purchase.need.equipment': 5,
    'building.purchase.need.small.equipment': 6,
    'building.purchase.need.diesel.consumption': 7
    }

    check_new_section_sequence_number_greater_than_zero = self.new_section_sequence_number > 0

    if not check_new_section_sequence_number_greater_than_zero:
      raise UserError("Le nouveau numéro de séquence doit être supérieur à 0")

    check_new_section_sequence_number_duplication = self.env[self.categories].search([('sequence_number', '=', self.new_section_sequence_number), ('need_id', '=', self.env.context.get('active_id')), ('display_type', '=', 'line_section')])

    if check_new_section_sequence_number_duplication:
      raise UserError("Une section avec le même numéro de séquence existe déjà")
    
    section = self[self.categories.replace('.', '_')]
    section.sequence_number = self.new_section_sequence_number
    section.identification_number = f"{categories_identification_number_index[self.categories]}.{self.new_section_sequence_number}"

    for line in section.section_ids:
      line.sequence_number = self.new_section_sequence_number
      line.identification_number = f"{categories_identification_number_index[self.categories]}.{self.new_section_sequence_number}.{line.line_number}"
      