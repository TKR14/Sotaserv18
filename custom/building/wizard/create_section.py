from odoo import fields, models, api
from odoo.exceptions import UserError


class CreateSection(models.TransientModel):
  _name = "create.section.wizard"

  @api.onchange('category_name')
  def _onchange_category_name(self):
    used_categories = self.env['building.purchase.need.small.equipment'].search([
      ('need_id', '=', self.env.context.get('active_id'))
    ]).mapped('category_id')

    categories = self.env['product.category'].search([
      ('category_type', '=', 'small_equipment'),
      ('id', 'not in', used_categories.ids)
    ])

    return {'domain': {'category_name': [('id', 'in', categories.ids)]}}

  def _exclude_fuel(self):
    template = self.env["building.purchase.need"].search([("is_template", "=", True)])
    sections = len(template.fuel_ids.filtered(lambda l: l.display_type == "line_section"))
    return sections == 2

  def _categories_selection(self):
    selection = [
      ('building.purchase.need.ressource.humain', 'Ressources Humaines'),
      ('building.purchase.need.line', 'Fournitures'),
      ('building.purchase.need.service.provision', 'Prestation de service'),
      ('building.purchase.need.mini.equipment', 'Outillages'),
      ('building.purchase.need.equipment', 'Matériels'),
      ('building.purchase.need.small.equipment', 'Petit Matériels'),
    ]
    if not self._exclude_fuel():
      selection.append(('building.purchase.need.fuel', 'Carburant'))
    return selection

  categories = fields.Selection(_categories_selection, string='Onglet', required=True, default='building.purchase.need.ressource.humain')
  section_name = fields.Char(string='Nom de la section')
  category_name = fields.Many2one('product.category', string='Nom de la catégorie')
  sequence_number = fields.Integer(string='Numéro de la séquence', required=True)

  def create_section(self):
    get = self.read()[0]
    categories_identification_number_index = {
      'building.purchase.need.ressource.humain': 1,
      'building.purchase.need.line': 2,
      'building.purchase.need.service.provision': 3,
      'building.purchase.need.mini.equipment': 4,
      'building.purchase.need.equipment': 5,
      'building.purchase.need.small.equipment': 6,
      'building.purchase.need.fuel': 7
    }

    section_exists_with_same_name = self.env[get['categories']].search([('name', '=', get['section_name']), ('need_id', '=', self.env.context.get('active_id')), ('display_type', '=', 'line_section')])

    check_sequence_number_greater_than_zero = get['sequence_number'] > 0

    section_sequence_number_duplication = self.env[get['categories']].search([('sequence_number', '=', get['sequence_number']), ('need_id', '=', self.env.context.get('active_id')), ('display_type', '=', 'line_section')])

    if section_exists_with_same_name:
      raise UserError("Une section avec le même nom existe déjà")
    
    if not check_sequence_number_greater_than_zero:
      raise UserError("Le numéro de séquence doit être supérieur à 0")
    
    if section_sequence_number_duplication:
      raise UserError("Une section avec le même numéro de séquence existe déjà")

    data = {
      'name': get['section_name'] if get['categories'] != 'building.purchase.need.small.equipment' else get['category_name'][1],
      'need_id': self.env.context.get('active_id'),
      'display_type': 'line_section',
      'sequence_number': get['sequence_number'],
      'line_number': 0,
      'identification_number': f"{categories_identification_number_index[get['categories']]}.{get['sequence_number']}",
      }
    
    if get['categories'] == 'building.purchase.need.small.equipment':
      data['category_id'] = get['category_name'][0]

    self.env[get['categories']].create(data)


class CreateNeedSection(models.TransientModel):
  _name = "create.need.section.wizard"