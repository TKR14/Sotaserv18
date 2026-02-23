from odoo import models, fields, tools

class SuiviBudgetaire(models.Model):
    _name = 'suivi.budgetaire'
    _auto = False

    site = fields.Char(string='Affaire')
    need_id = fields.Many2one('building.purchase.need', string='Liste des besoins')
    volet = fields.Char("Volet")
    line_id = fields.Integer("Line ID")
    section = fields.Char("Section")
    category = fields.Char("Catégorie")
    type = fields.Char("Type")
    rubrique = fields.Char("Rubrique")
    uom_id = fields.Many2one('uom.uom', string='UDM')
    budget_qty = fields.Float("Budget Qty")
    budget_pu = fields.Float("Budget PU")
    commande_qty = fields.Float("Commande Qty")
    commande_mnt = fields.Float("Commande Mnt")

    def init(self):
        tools.drop_view_if_exists(self._cr, 'suivi_budgetaire')
        self._cr.execute("""
            CREATE OR REPLACE VIEW suivi_budgetaire AS (
                SELECT
                    CONCAT('1', rh.id) AS id,
                    bs.name::text AS site,
                    rh.need_id,
                    'Ressources Humaines' AS volet,
                    rh.id AS line_id,
                    s.name::text AS section,
                    CASE
                        WHEN rh.type_resource = 'supervisor' THEN 'Encadrement'
                        ELSE 'Main-d''œuvre'
                    END::text AS category,
                    p.name::text AS type,
                    j.name::text AS rubrique,
                    rh.uom_id,
                    rh.duree_j AS budget_qty,
                    rh.price_unit AS budget_pu,
                    0 AS commande_qty,
	                0 AS commande_mnt
                FROM
                    building_purchase_need_ressource_humain rh
                    LEFT JOIN building_site bs ON rh.site_id = bs.id
                    LEFT JOIN building_purchase_need_ressource_humain s ON rh.section_id = s.id
                    LEFT JOIN hr_job_profile p ON rh.profile_id = p.id
                    LEFT JOIN hr_job j ON rh.job_id = j.id
                WHERE
                    rh.display_type IS NULL AND rh.need_id != 3
                UNION
                SELECT
                    CONCAT('2', l.id) AS id,
                    bs.name::text AS site,
                    l.need_id,
                    'Fournitures' AS volet,
                    l.id AS line_id,
                    s.name::text AS section,
                    pc.name::text AS category,
                    CASE
                        WHEN l.type_produit = 'material' THEN 'Fourniture'
                        ELSE 'Consommable'
                    END::text AS type,
                    pt.name::text AS rubrique,
                    l.uom_id,
                    l.quantity AS budget_qty,
                    l.price_unit AS budget_pu,
                    (SELECT SUM(pol.product_qty)
                    FROM purchase_order_line pol
                    JOIN purchase_order po ON pol.order_id = po.id
                    WHERE pol.product_id = pp.id AND po.site_id = l.site_id AND po.state = 'purchase') AS commande_qty,
                    (SELECT SUM(pol.price_unit * pol.product_qty)
                    FROM purchase_order_line pol
                    JOIN purchase_order po ON pol.order_id = po.id
                    WHERE pol.product_id = pp.id AND po.site_id = l.site_id AND po.state = 'purchase') AS commande_mnt
                FROM
                    building_purchase_need_line l
                    LEFT JOIN building_site bs ON l.site_id = bs.id
                    LEFT JOIN building_purchase_need_line s ON l.section_id = s.id
                    LEFT JOIN product_product pp ON l.product_id = pp.id
                    LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    LEFT JOIN product_category pc ON pt.categ_id = pc.id
                WHERE
                    l.display_type IS NULL AND l.need_id != 3
                UNION
                SELECT
                    CONCAT('3', sp.id) AS id,
                    bs.name::text AS site,
                    sp.need_id,
                    'Prestations de service' AS volet,
                    sp.id AS line_id,
                    s.name::text AS section,
                    pc.name::text AS category,
                    ''::text AS type,
                    pt.name::text AS rubrique,
                    sp.uom_id,
                    sp.quantity AS budget_qty,
                    sp.price_unit AS budget_pu,
                    (SELECT SUM(pol.product_qty)
                    FROM purchase_order_line pol
                    JOIN purchase_order po ON pol.order_id = po.id
                    WHERE pol.product_id = pp.id AND po.site_id = sp.site_id AND po.state = 'purchase') AS commande_qty,
                    (SELECT SUM(pol.price_unit * pol.product_qty)
                    FROM purchase_order_line pol
                    JOIN purchase_order po ON pol.order_id = po.id
                    WHERE pol.product_id = pp.id AND po.site_id = sp.site_id AND po.state = 'purchase') AS commande_mnt
                FROM
                    building_purchase_need_service_provision sp
                    LEFT JOIN building_site bs ON sp.site_id = bs.id
                    LEFT JOIN building_purchase_need_service_provision s ON sp.section_id = s.id
                    LEFT JOIN product_product pp ON sp.product_id = pp.id
                    LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    LEFT JOIN product_category pc ON pt.categ_id = pc.id
                WHERE
                    sp.display_type IS NULL AND sp.need_id != 3
                UNION
                SELECT
                    CONCAT('4', me.id) AS id,
                    bs.name::text AS site,
                    me.need_id,
                    'Outillage' AS volet,
                    me.id AS line_id,
                    s.name::text AS section,
                    pc.name::text AS category,
                    ''::text AS type,
                    pt.name::text AS rubrique,
                    me.uom_id,
                    me.quantity AS budget_qty,
                    me.price_unit AS budget_pu,
                    (SELECT SUM(pol.product_qty)
                    FROM purchase_order_line pol
                    JOIN purchase_order po ON pol.order_id = po.id
                    WHERE pol.product_id = pp.id AND po.site_id = me.site_id AND po.state = 'purchase') AS commande_qty,
                    (SELECT SUM(pol.price_unit * pol.product_qty)
                    FROM purchase_order_line pol
                    JOIN purchase_order po ON pol.order_id = po.id
                    WHERE pol.product_id = pp.id AND po.site_id = me.site_id AND po.state = 'purchase') AS commande_mnt
                FROM
                    building_purchase_need_mini_equipment me
                    LEFT JOIN building_site bs ON me.site_id = bs.id
                    LEFT JOIN building_purchase_need_mini_equipment s ON me.section_id = s.id
                    LEFT JOIN product_product pp ON me.product_id = pp.id
                    LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    LEFT JOIN product_category pc ON pt.categ_id = pc.id
                WHERE
                    me.display_type IS NULL AND me.need_id != 3
                UNION
                SELECT
                    CONCAT('5', sm.id) AS id,
                    bs.name::text AS site,
                    sm.need_id,
                    'Petit Matériel' AS volet,
                    sm.id AS line_id,
                    s.name::text AS section,
                    mvc.name::text AS category,
                    ''::text AS type,
                    fv.name::text AS rubrique,
                    sm.uom_id,
                    sm.quantity AS budget_qty,
                    sm.price_unit AS budget_pu,
                    0 AS commande_qty,
	                0 AS commande_mnt
                FROM
                    building_purchase_need_small_equipment sm
                    LEFT JOIN building_site bs ON sm.site_id = bs.id
                    LEFT JOIN building_purchase_need_small_equipment s ON sm.section_id = s.id
                    LEFT JOIN fleet_vehicle fv ON sm.equipment_id = fv.id
                    LEFT JOIN maintenance_vehicle_category mvc ON fv.categ_fleet_id = mvc.id
                WHERE
                    sm.display_type IS NULL AND sm.need_id != 3
                UNION
                SELECT
                    CONCAT('6', n.id) AS id,
                    bs.name::text AS site,
                    n.need_id,
                    'Matériel' AS volet,
                    n.id AS line_id,
                    s.name::text AS section,
                    '' as category,
                    ''::text AS type,
                    mvc.name::text AS rubrique,
                    n.uom_id,
                    n.quantity AS budget_qty,
                    n.price_unit AS budget_pu,
                    0 AS commande_qty,
	                0 AS commande_mnt
                FROM
                    building_purchase_need_equipment n
                    LEFT JOIN building_site bs ON n.site_id = bs.id
                    LEFT JOIN building_purchase_need_equipment s ON n.section_id = s.id
                    LEFT JOIN maintenance_vehicle_category mvc ON n.equipment_category_id = mvc.id
                WHERE
                    n.display_type IS NULL AND n.need_id != 3
                )""")
        
    def update_sections(self):
        template = self.env["building.purchase.need"].search([("is_template", "=", True)])
        tables = ['building.purchase.need.ressource.humain','building.purchase.need.line','building.purchase.need.service.provision','building.purchase.need.mini.equipment','building.purchase.need.equipment','building.purchase.need.small.equipment']
        table_field = {
            "building.purchase.need.ressource.humain": "ressource_humain_ids",
            "building.purchase.need.line": "line_ids",
            "building.purchase.need.service.provision": "service_provision_ids",
            "building.purchase.need.mini.equipment": "mini_equipment_ids",
            "building.purchase.need.equipment": "equipment_ids",
            "building.purchase.need.small.equipment": "small_equipment_ids"
        }
        for table in tables:
            sections = template[table_field[table]].filtered(lambda line:line.display_type == False)
            for line in sections:
                pbn_lines = self.env[table].search([("template_line_id", "=", line.id)])
                for pbn_line in pbn_lines:
                    line_template_section_id = pbn_line.template_line_id.section_id
                    section_id = pbn_lines = self.env[table].search([("template_line_id", "=", line_template_section_id.id), ("need_id", "=", pbn_line.need_id.id)])
                    pbn_line.section_id = section_id.id
