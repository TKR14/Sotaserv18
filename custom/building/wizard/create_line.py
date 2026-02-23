from odoo import fields, models, api
from odoo.exceptions import UserError

class CreateLine(models.TransientModel):
  _name = "create.line.wizard"

  @api.onchange("building_purchase_need_site_installation")
  def _onchange_building_purchase_need_site_installation(self):
    return {"domain": {"building_purchase_need_site_installation": [("need_id", "=", self.env.context.get("active_id")), ("display_type", "=", "line_section")]}}
  
  @api.onchange("building_purchase_need_ressource_humain")
  def _onchange_building_purchase_need_ressource_humain(self):
    return {"domain": {"building_purchase_need_ressource_humain": [("need_id", "=", self.env.context.get("active_id")), ("display_type", "=", "line_section")]}}
  
  @api.onchange("building_purchase_need_line")
  def _onchange_building_purchase_need_line(self):
    return {"domain": {"building_purchase_need_line": [("need_id", "=", self.env.context.get("active_id")), ("display_type", "=", "line_section")]}}
  
  @api.onchange("building_purchase_need_service_provision")
  def _onchange_building_purchase_need_service_provision(self):
    return {"domain": {"building_purchase_need_service_provision": [("need_id", "=", self.env.context.get("active_id")), ("display_type", "=", "line_section")]}}
  
  @api.onchange("building_purchase_need_mini_equipment")
  def _onchange_building_purchase_need_mini_equipment(self):
    return {"domain": {"building_purchase_need_mini_equipment": [("need_id", "=", self.env.context.get("active_id")), ("display_type", "=", "line_section")]}}
  
  @api.onchange("building_purchase_need_equipment")
  def _onchange_building_purchase_need_equipment(self):
    return {"domain": {"building_purchase_need_equipment": [("need_id", "=", self.env.context.get("active_id")), ("display_type", "=", "line_section")]}}
  
  @api.onchange("building_purchase_need_fuel")
  def _onchange_building_purchase_need_fuel(self):
    template = self.env["building.purchase.need"].search([("is_template", "=", True)])
    sections = template.fuel_ids.filtered(lambda l: l.display_type != "line_section").mapped("section_id").ids
    return {"domain": {"building_purchase_need_fuel": [("id", "not in", sections), ("need_id", "=", self.env.context.get("active_id")), ("display_type", "=", "line_section")]}}
  
  @api.onchange("building_purchase_need_small_equipment")
  def _onchange_building_purchase_need_small_equipment(self):
    return {"domain": {"building_purchase_need_small_equipment": [("need_id", "=", self.env.context.get("active_id")), ("display_type", "=", "line_section")]}}

  def _exclude_fuel(self):
    template = self.env["building.purchase.need"].search([("is_template", "=", True)])
    lines = len(template.fuel_ids.filtered(lambda l: l.display_type != "line_section"))
    return lines == 2

  def _categories_selection(self):
    selection = [
      ("building.purchase.need.ressource.humain", "Ressources Humaines"),
      ("building.purchase.need.line", "Fournitures"),
      ("building.purchase.need.service.provision", "Prestation de service"),
      ("building.purchase.need.mini.equipment", "Outillages"),
      ("building.purchase.need.equipment", "Matériels"),
      ('building.purchase.need.small.equipment', 'Petit Matériels'),
    ]
    if not self._exclude_fuel():
      selection.append(("building.purchase.need.fuel", "Carburant"))
    return selection

  categories = fields.Selection(_categories_selection, string="Onglet", required=True, default="building.purchase.need.ressource.humain")
  
  building_purchase_need_site_installation = fields.Many2one("building.purchase.need.site.installation", string="Section Installation de chantier")
  building_purchase_need_ressource_humain = fields.Many2one("building.purchase.need.ressource.humain", string="Section Ressources Humaines")
  building_purchase_need_line= fields.Many2one("building.purchase.need.line", string="Section Fournitures")
  building_purchase_need_service_provision = fields.Many2one("building.purchase.need.service.provision", string="Section Prestation de service")
  building_purchase_need_mini_equipment = fields.Many2one("building.purchase.need.mini.equipment", string="Section Outillages")
  building_purchase_need_small_equipment = fields.Many2one("building.purchase.need.small.equipment", string="Section Petit Matériels")
  building_purchase_need_equipment= fields.Many2one("building.purchase.need.equipment", string="Section Matériels")
  building_purchase_need_fuel = fields.Many2one("building.purchase.need.fuel", string="Section Carburant")

  line_number = fields.Integer(string="Numéro de la ligne", required=True)

  def create_line(self):
    get = self.read()[0]

    check_line_number_greater_than_zero = get["line_number"] > 0

    if not check_line_number_greater_than_zero:
      raise UserError("Le numéro de la ligne doit être supérieur à 0")
    
    check_line_number_duplication = self.env[get["categories"]].search([("line_number", "=", get["line_number"]), ("need_id", "=", self.env.context.get("active_id")), ("section_id", "=", self[get["categories"].replace(".", "_")].id)])

    if check_line_number_duplication:
      raise UserError("Une ligne avec le même numéro existe déjà")
    
    data = {
      "need_id": self.env.context.get("active_id"),
      "sequence_number": self[get["categories"].replace(".", "_")].sequence_number,
      "line_number": get["line_number"],
      "section_id": self[get["categories"].replace(".", "_")].id,
      "identification_number": f"{self[get['categories'].replace('.', '_')].identification_number}.{get['line_number']}",
      "is_activated": False
    }
    self.env[get["categories"]].create(data)


class CreateNeedLine(models.TransientModel):
  _name = "create.need.line.wizard"

  @api.model
  def _get_categories_selection_values(self):
    current_purchase_need = self.env["building.purchase.need"].browse(self.env.context.get("active_id"))
    template = self.env["building.purchase.need"].search([("is_template", "=", True)], limit=1)

    category_mapping = {
        "ressource.humain": "Ressources Humaines",
        "line": "Fournitures",
        "service.provision": "Prestation de service",
        "mini.equipment": "Outillages",
        "equipment": "Matériels",
        "small.equipment": "Petit Matériels",
        "fuel": "Carburant",
    }

    categories_domain = [
        (category, label)
        for category, label in category_mapping.items()
        # if template[f"{category.replace('.', '_')}_ids"].filtered(
        #     lambda line_template: line_template.is_activated and line_template.display_type != "line_section"
        # ) - getattr(current_purchase_need, f"{category.replace('.', '_')}_ids").template_line_id
    ]

    return categories_domain

  
  categories = fields.Selection(_get_categories_selection_values, string="Onglet", required=True)
  site_installation = fields.Many2one("building.purchase.need.site.installation", string="Installation de chantier")
  ressource_humain = fields.Many2one("building.purchase.need.ressource.humain", string="Ressources Humaines")
  line = fields.Many2one("building.purchase.need.line", string="Fournitures")
  service_provision = fields.Many2one("building.purchase.need.service.provision", string="Prestation de service")
  mini_equipment = fields.Many2one("building.purchase.need.mini.equipment", string="Outillages")
  equipment = fields.Many2one("building.purchase.need.equipment", string="Matériels")
  small_equipment = fields.Many2one("building.purchase.need.small.equipment", string="Petit Matériels")
  fuel = fields.Many2one("building.purchase.need.fuel", string="Carburant")

  @api.onchange("categories")
  def _onchange_categories(self):
    current_purchase_need = self.env["building.purchase.need"].browse(self.env.context.get("active_id"))
    template = self.env["building.purchase.need"].search([("is_template", "=", True)], limit=1)

    category_mapping = {
        "ressource.humain": "ressource_humain",
        "line": "line",
        "service.provision": "service_provision",
        "mini.equipment": "mini_equipment",
        "equipment": "equipment",
        "small.equipment": "small_equipment",
        "fuel": "fuel",
    }

    category = category_mapping.get(self.categories)

    if category:
        check_need_category = template[f"{category}_ids"].filtered(
            lambda line_template: line_template.is_activated and line_template.display_type != "line_section"
        ) - getattr(current_purchase_need, f"{category}_ids").template_line_id

        return {"domain": {category: [("id", "in", check_need_category.ids)]}}

    return {}
  
  def create_line(self, current_need_id, category, model_name):
    get = self.read()[0]
    line = self.env[model_name].search([("id", "=", get[category][0])], limit=1)

    check_if_line_parent_exists = self.env[model_name].search([
        ("template_line_id", "=", line.section_id.id),
        ("need_id", "=", current_need_id.id),
        ("display_type", "=", "line_section")
    ], limit=1)

    if not check_if_line_parent_exists:
        line_vals = line.section_id.copy_data()[0]
        line_vals.update({
            "need_id": current_need_id.id,
            "sequence_number": False,
            "line_number": False,
            "section_id": False,
            "identification_number": False,
            "sequence_number_parent": 0,
            "line_number_parent": 0,
            "identification_number_parent": 0,
            "template_line_id": line.section_id.id,
        })

        current_need_id.write({f"{category}_ids": [(0, 0, line_vals)]})

    line_vals = line.copy_data()[0]
    line_vals.update({
        "need_id": current_need_id.id,
        "sequence_number": False,
        "line_number": False,
        "section_id": False,
        "identification_number": False,
        "sequence_number_parent": 0,
        "line_number_parent": 0,
        "identification_number_parent": 0,
        "template_line_id": line.id,
    })

    current_need_id.write({f"{category}_ids": [(0, 0, line_vals)]})

  def create_need_line(self):
      current_need_id = self.env["building.purchase.need"].search([("id", "=", self.env.context.get("active_id"))], limit=1)
      
      if current_need_id:
          get = self.read()[0]
          category = get["categories"].replace(".", "_")
          
          if category in ["ressource_humain", "line", "service_provision", "mini_equipment", "equipment", "fuel", "small_equipment"]:
              model_name = f"building.purchase.need.{get['categories']}"
              self.create_line(current_need_id, category, model_name)
