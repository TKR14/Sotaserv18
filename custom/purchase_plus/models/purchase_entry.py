from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError

class PurchaseEntry(models.Model):
    _name = "purchase.entry"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Purchase Entry'

    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.company.currency_id)

    purchase_id = fields.Many2one('purchase.order', string='Bon de Commande', required=True)
    supplier_id = fields.Many2one('res.partner', string='Fournisseur', required=True)
    site_id = fields.Many2one('building.site', string='Affaire', domain="[]", required=True)
    start_date = fields.Date(string='Date début')
    end_date = fields.Date(string='Date fin')
    number = fields.Char(string='Numéro décompte', readonly=True)
    is_done = fields.Boolean(string="Décompte final", default=False, tracking=True)
    is_automatically_done = fields.Boolean(default=False)

    amount_commande = fields.Float(string="Montant HT", compute='_compute_amount_commande', store=True)
    amount_avance = fields.Float(string="Montant d'avance (TTC)", compute='_compute_amount_avance')
    percentage_rg = fields.Float(related="purchase_id.return_of_guarantee", string="RG (%)")

    is_invoiced = fields.Boolean(string="is_invoiced", default=False)

    line_ids = fields.One2many('purchase.entry.line', 'entry_id')
    line_idss = fields.One2many('purchase.entry.line', 'entry_id')
    
    return_of_guarantee = fields.Float(string="RG (TTC)", compute='_compute_return_of_guarantee')

    accumulations_work =  fields.Float(string="Cumul travaux réalisés (HT)", compute="_compute_accumulations_work", store=True)
    accumulations_work_ttc =  fields.Float(string="Cumul travaux réalisés (HT)", compute="_compute_accumulations_work_ttc")
    accumulation_previous_amounts =  fields.Float(string="Cumul travaux facturé (HT)", compute="_compute_accumulation_previous_amounts") 
    # accumulation_previous_amounts_ttc =  fields.Float(string="Cumul travaux facturé (HT)", compute="_compute_accumulation_previous_amounts_ttc")
    amount_invoiced =  fields.Float(string=" Montant Brut de la situation (HT)", compute="_compute_amount_invoiced")
    amount_invoiced_ttc =  fields.Float(string="Montant Brut (TTC)", compute="_compute_amount_invoiced_ttc")
    avance_red =  fields.Float(string="Déduction Avance (TTC)", compute="_compute_advance_return_red")
    rg_red =  fields.Float(string="Déduction RG (TTC)", compute="_compute_advance_return_red")
    penalty_red =  fields.Float(string="Déduction Pénalité (HT)", compute="_compute_advance_return_red")
    net_amount_to_be_invoiced = fields.Float(string="Net à facturer en TTC", compute="_compute_net_amount_to_be_invoiced")

    remaining_advance =  fields.Float(string="Avance (TTC)", compute="_compute_avance_red")
    remaining_rg =  fields.Float(string="RG (TTC)", compute="_compute_avance_red")
    remaining_penalty =  fields.Float(string="Pénalité (HT)", compute="_compute_avance_red")
    executed =  fields.Float(string="Pourcentage éxécuté", compute="_comput_executed", store=True)

    is_avance_readonly = fields.Boolean(string='Is Avance Read-only', compute='_compute_is_avance_readonly')
    is_bill = fields.Boolean()

    account_move_id = fields.Many2one('account.move', string="Facture")

    is_facture_not_draft = fields.Boolean(
        string="Is Facture Not Draft",
        compute='_compute_is_facture_not_draft',
    )
    under_ninty_five = fields.Boolean(compute="_compute_under_ninty_five", store=True)

    gross_amount_ht = fields.Float(string="Montant Brut (HT)", compute="_gross_amount_ht", tracking=True)

    @api.depends('amount_invoiced', 'penalty')
    def _gross_amount_ht(self):
        for rec in self:
            rec.gross_amount_ht = (rec.amount_invoiced or 0.0) - (rec.penalty or 0.0)

    @api.depends("executed")
    def _compute_under_ninty_five(self):
        for pe in self:
            pe.under_ninty_five = True
            if pe.executed >= 95:
                pe.under_ninty_five = False

    @api.onchange('is_done', 'is_automatically_done')
    def _onchange_is_done(self):
        for rec in self:
            if rec.is_done or rec.is_automatically_done:
                rec.avance = rec.amount_avance - rec.remaining_advance
            else:
                rec.avance = 0.0

    @api.depends('amount_avance', 'remaining_advance', 'is_done', 'is_automatically_done')
    def _compute_is_avance_readonly(self):
        for entry in self:
            if entry.amount_avance == 0:
                entry.is_avance_readonly = True
            elif entry.remaining_advance == entry.amount_avance:
                entry.is_avance_readonly = True
            elif entry.is_done or entry.is_automatically_done:
                entry.is_avance_readonly = True
            else:
                entry.is_avance_readonly = False

    def print_attachment(self):
        return self.env.ref('purchase_plus.attachement_action').report_action(self)
    
    def print_decompt(self):
        return self.env.ref('purchase_plus.decompt_action').report_action(self)

    @api.depends('avance', 'return_of_guarantee', 'penalty')
    def _compute_advance_return_red(self):
        for record in self:
            record.avance_red = round(record.avance)
            record.rg_red = round(record.return_of_guarantee)
            record.penalty_red = round(record.penalty)
    
    @api.constrains('avance', 'amount_avance')
    def _check_avance_amount(self):
        for record in self:
            if record.avance > record.amount_avance:
                raise ValidationError("L'avance ne peut pas dépasser le montant d'avance disponible !")

    @api.depends('avance', 'return_of_guarantee', 'penalty')
    def _compute_avance_red(self):
        for record in self:
            sum_avance = 0
            sum_rg = 0
            sum_penalite = 0
            
            if record.id:
                purchase_ids = self.search([
                    ('site_id', '=', record.site_id.id), 
                    ('purchase_id', '=', record.purchase_id.id), 
                    ('id', '<=', record.id)
                ])

                for pi in purchase_ids:
                    sum_avance += pi.avance

                sum_rg = sum(rec.return_of_guarantee for rec in purchase_ids)
                sum_penalite = sum(rec.penalty for rec in purchase_ids)

            record.avance_red = record.remaining_advance = sum_avance
            record.rg_red = record.remaining_rg = round(sum_rg)
            record.penalty_red = record.remaining_penalty = round(sum_penalite)

    @api.depends('line_ids')
    def _compute_amount_invoiced_ttc(self):
        for record in self:
            if record.purchase_id:
                amount_invoiced_ttc = sum(line.amount_invoiced_tva for line in record.line_ids)
                record.amount_invoiced_ttc = round((record.amount_invoiced + amount_invoiced_ttc) - record.penalty)
            else:
                record.amount_invoiced_ttc = 0.0

    @api.depends('amount_invoiced_ttc', 'avance_red', 'rg_red', 'penalty_red')
    def _compute_net_amount_to_be_invoiced(self):
        for record in self:
            total_invoiced = record.amount_invoiced_ttc or 0.0
            total_deductions = (record.avance_red or 0.0) + (record.rg_red or 0.0)
            record.net_amount_to_be_invoiced = round(total_invoiced - total_deductions)

    def comput_executed(self):
        # for record in self.env["purchase.entry"].search([]):
        for record in self:
            record._compute_amount_commande()
            record._compute_accumulations_work()
            record._comput_executed()

    @api.depends('accumulations_work', 'amount_commande')
    def _comput_executed(self):
        for record in self:
            if record.amount_commande != 0:
                executed = (record.accumulations_work / record.amount_commande) * 100
                if executed > 99:
                    executed = round(executed)
                record.executed = executed
            else:
                record.executed = 0

    # @api.constrains('return_of_guarantee')
    # def _check_avance_retenue(self):
    #     for record in self:
    #         if record.return_of_guarantee < 0 or record.return_of_guarantee > 100:
    #             raise ValidationError("La valeur de 'Retenue de garantie' doit être comprise entre 0 et 100.")

    @api.depends('line_ids', 'line_ids.cumulative_ht')
    def _compute_accumulations_work(self):
        for record in self:
            if record.purchase_id:
                total_cumulative_amount = sum(line.cumulative_ht for line in record.line_ids)
                record.accumulations_work = round(total_cumulative_amount)
            else:
                record.accumulations_work = 0.0

    @api.depends('line_ids')
    def _compute_accumulations_work_ttc(self):
        for record in self:
            if record.purchase_id:
                total_cumulative_amount_ttc = sum(line.cumulative_ttc for line in record.line_ids)
                record.accumulations_work_ttc = round(total_cumulative_amount_ttc)
            else:
                record.accumulations_work_ttc = 0.0

    @api.depends('purchase_id')
    def _compute_accumulation_previous_amounts(self):
        for record in self:
            if record.purchase_id:
                entries = self.env['purchase.entry'].search([
                    ('purchase_id', '=', record.purchase_id.id),
                    ('id', '<', record.id)
                ])
                total_cumulative_amount = 0
                if entries:
                    for entry in entries:
                        for line in entry.line_idss:
                            total_cumulative_amount += line.amount_ht_invoiced
                    record.accumulation_previous_amounts = round(total_cumulative_amount)
                else:
                    record.accumulation_previous_amounts = 0.0
            else:
                record.accumulation_previous_amounts = 0.0
                
    # @api.depends('purchase_id')
    # def _compute_accumulation_previous_amounts_ttc(self):
    #     for record in self:
    #         if record.purchase_id:
    #             moves = self.env['account.move'].search([
    #                 ('purchase_id', '=', record.purchase_id.id),
    #                 ('invoice_type', '=', 'standard'),
    #             ], order="create_date asc")
                
    #             if moves:
    #                 total_cumulative_amount = sum(move.amount_total for move in moves[:-1])
    #                 record.accumulation_previous_amounts_ttc = total_cumulative_amount
    #             else:
    #                 record.accumulation_previous_amounts_ttc = 0.0
    #         else:
    #             record.accumulation_previous_amounts_ttc = 0.0

    # @api.depends('purchase_id')
    # def _compute_accumulation_previous_amounts_ttc(self):
    #     for record in self:
    #         total_cumulative_amount = 0
    #         if record.purchase_id:
    #             entries = self.env['purchase.entry'].search([
    #                 ('purchase_id', '=', record.purchase_id.id),
    #                 ('id', '<', record.id),
    #             ])
    #             if entries:
    #                 for entry in entries:
    #                     for line in entry.line_ids:
    #                         total_cumulative_amount += line.amount_ht

    #         record.accumulation_previous_amounts_ttc = total_cumulative_amount


    @api.depends('accumulations_work', 'accumulation_previous_amounts')
    def _compute_amount_invoiced(self):
        for record in self:
            record.amount_invoiced = round(record.accumulations_work - record.accumulation_previous_amounts)

    @api.depends('purchase_id.amount_total')
    def _compute_amount_commande(self):
        for rec in self:
            rec.amount_commande = rec.purchase_id.amount_untaxed

    def fixe_tit(self):
        self._compute_amount_avance()

    @api.depends('purchase_id.avance', 'purchase_id.amount_total')
    def _compute_amount_avance(self):
        for rec in self:
            rec.amount_avance = self.env['account.move'].search([('invoice_origin', '=', rec.purchase_id.name), ('move_type_code', '=', 'inv_advance'), ("state", "!=", "cancel")]).amount_total
        
    @api.depends('line_ids.montant_ligne')
    def _compute_cumul_travaux_realises(self):
        for entry in self:
            entry.cumul_travaux_realises = sum(line.montant_ligne for line in entry.line_ids)

    @api.depends('payment_ids.montant')
    def _compute_cumul_paiements_precedents(self):
        for entry in self:
            entry.cumul_paiements_precedents = sum(payment.montant for payment in entry.payment_ids if payment.state == 'paid')

    @api.depends('cumul_travaux_realises', 'cumul_paiements_precedents')
    def _compute_montant_brut_facturer(self):
        for entry in self:
            entry.montant_brut_facturer = entry.cumul_travaux_realises - entry.cumul_paiements_precedents

    @api.depends('advance_paid', 'advance_used')
    def _compute_reliquat_avance(self):
        for entry in self:
            entry.reliquat_avance = entry.advance_paid - entry.advance_used

    @api.depends('cumul_travaux_realises', 'retention_percentage')
    def _compute_reliquat_rg(self):
        for entry in self:
            entry.reliquat_rg = entry.retention_percentage * entry.cumul_travaux_realises

    @api.depends('total_penalty_amount', 'penalties_paid')
    def _compute_reliquat_penalite(self):
        for entry in self:
            entry.reliquat_penalite = entry.total_penalty_amount - entry.penalties_paid

    @api.depends('cumul_travaux_realises', 'total_contract_amount')
    def _compute_executed_percentage(self):
        for entry in self:
            if entry.total_contract_amount > 0:
                entry.executed_percentage = (entry.cumul_travaux_realises / entry.total_contract_amount) * 100
            else:
                entry.executed_percentage = 0.0

    state_attachemnet = fields.Selection([
        ('draft', 'Brouillon'),
        ('internal_validated', 'Validé CP/CT'),
    ], default="draft", string="Statut Attachement", tracking=True)

    state_decompte = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated_dz', 'Validé DZ'),
        ('provider_validated', 'Validé Aud'),
        ('done', 'Validé DT'),
        ('bill', 'Facturé'),
    ], default="draft", string="Statut Décompte", tracking=True)

    state_decompte_not_done = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated_dz', 'Validé DZ'),
        ('done', 'Validé DT'),
        ('bill', 'Facturé'),
    ], default="draft", string="Statut Décompte Final")

    penalty = fields.Float(string="Pénalité (HT)", tracking=True)
    avance = fields.Float(string="Avance (TTC)", tracking=True)

    # is_remaining_advance = fields.Boolean(string="Reliquat avance", default=False, tracking=True)
    is_remettre_invisible = fields.Boolean(compute="_compute_is_remettre_invisible")

    represent = fields.Char(string='Représentant', tracking=True)

    @api.onchange('avance', 'penalty')
    def _onchange_advance_penalty_round(self):
        for rec in self:
            rec.avance = rec.avance
            rec.penalty = round(rec.penalty)

    def action_get_user_attachments(self, readonly=False, nocreate=False):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
        ])

        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'search_default_group_by_requested_by': 1,
            'create': False,
            'group_by': ['site_id']
        }

        domain = [
            ('site_id', 'in', site_ids)
        ]

        return {
            'name': 'Attachements fournisseur',
            'type': 'ir.actions.act_window',
            'view_mode': 'lis,form',
            'res_model': 'purchase.entry',
            'views': [
                (self.env.ref('purchase_plus.view_purchase_entry_tree').id, 'list'),
                (self.env.ref('purchase_plus.purchase_entry_view_form').id, 'form')
            ],
            'domain': domain,
            'context': context,
        }

    def action_get_user_decompte(self, readonly=False, nocreate=False):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
        ])
        
        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'search_default_group_by_requested_by': 1,
            'create': False,
            "group_by": ["site_id"]
        }

        domain = [
            ('site_id', 'in', site_ids),
            ('state_attachemnet', '!=', "draft"),
        ]

        return {
            'name': 'Décompte fournisseurs',
            'type': 'ir.actions.act_window',
            'view_mode': 'lis,form',
            'res_model': 'purchase.entry',
            'views': [
                (self.env.ref('purchase_plus.view_purchase_entry_decompt_tree').id, 'list'),
                (self.env.ref('purchase_plus.purchase_entry_decompt_view_form').id, 'form')
            ],
            'domain': domain,
            'context': context,
            'target':'main',
        }
    
    def action_get_user_decompte_situation(self, readonly=False, nocreate=False):
        profile_ids = self.env['building.profile.assignment'].search([
            ('user_id', '=', self.env.user.id),
        ])
        
        site_ids = profile_ids.mapped('site_id').ids

        context = {
            'search_default_group_by_requested_by': 1,
            'create': False,
            "group_by": ["site_id"]
        }

        domain = [
            ('site_id', 'in', site_ids),
            ('state_attachemnet', '!=', "draft"),
        ]

        return {
            'name': 'Décompte fournisseurs',
            'type': 'ir.actions.act_window',
            'view_mode': 'lis,form',
            'res_model': 'purchase.entry',
            'views': [
                (self.env.ref('purchase_plus.view_purchase_entry_decompt_readonly_tree').id, 'list'),
                (self.env.ref('purchase_plus.purchase_entry_decompt_readonly_form').id, 'form')
            ],
            'domain': domain,
            'context': context,
            'target':'main',
        }

    @api.depends('purchase_id.return_of_guarantee')
    def _compute_return_of_guarantee(self):
        for rec in self:
            if rec.purchase_id:
                purchase_order = self.env['purchase.order'].search([('id', '=', rec.purchase_id.id)], limit=1)
                if purchase_order:
                    rec.return_of_guarantee = round((purchase_order.return_of_guarantee * rec.amount_invoiced_ttc) / 100)
                else:
                    rec.return_of_guarantee = False
            else:
                rec.return_of_guarantee = False

    # @api.onchange('is_done')
    # def toggle_is_done(self):
    #     for record in self:
    #         purchase_order = record.purchase_id
    #         if purchase_order:
    #             if record.is_done:
    #                 purchase_order.sudo().write({'is_done': True})
    #                 return {
    #                     'warning': {
    #                         'title': 'Confirmation',
    #                         'message': 'Êtes-vous sûr de vouloir marquer ce bon de commande comme terminé ?',
    #                     }
    #                 }
    #             else:
    #                 purchase_order.sudo().write({'is_done': False})
    #                 return {
    #                     'warning': {
    #                         'title': 'Confirmation',
    #                         'message': 'Êtes-vous sûr de vouloir réinitialiser l\'état de ce bon de commande ?',
    #                     }
    #                 }

    @api.constrains('penalty')
    def _check_required_fields(self):
        for record in self:
            if record.penalty < 0:
                raise ValidationError(
                    "La valeur de la pénalité ne peut pas être inférieure à zéro."
                )
    
    # @api.onchange('is_done')
    # def toggle_is_done(self):
    #     for record in self:
    #         purchase_order = record.purchase_id
    #         if purchase_order:
    #             if record.is_done:
    #                 purchase_order.write({'is_done': True})
    #             else:
    #                 purchase_order.write({'is_done': False})

    def name_get(self):
        result = []
        for record in self:
            name = record.number or ''
            result.append((record.id, name))
        return result

    def internal_validation_action(self):
        negative_cumulative_quantity = sum(self.line_ids.mapped("detail_id").mapped("cumulative_quantity")) == 0
        if negative_cumulative_quantity:
            raise ValidationError("La quantité cumulée de toutes les lignes ne peut pas être 0.")

        is_done = self.executed == 100
        self.write({
            "state_attachemnet": "internal_validated",
            "state_decompte": "draft",
            "is_done": is_done,
            "is_automatically_done": is_done,
        })
        self.line_ids.mapped("detail_id").is_validated = True

        self._update_purchase_order_state()
        self._onchange_is_done()

    def _update_purchase_order_state(self):
        self.purchase_id.sudo()._update_state_from_purchase_entry()

    def back_to_draft(self, reason=None):
        self.write({
            "state_attachemnet": "draft",
            "is_done": False,
            "is_automatically_done": False,
        })
        
        self.line_ids.mapped("detail_id").is_validated = False

        self.message_post(body=f"""<ul><li>Motif de Retour: {reason}</li><ul/>""")
        self._update_purchase_order_state()

        existing_invoices = self.env["account.move"].search([("ref", "=", self.number), ("move_type", "=", "in_invoice")])
        existing_invoices.unlink()

        return self.action_get_user_decompte()

    def remettre_to_draft_decompt(self, reason=None):
        self.write({
            "state_decompte": "draft",
            "state_decompte_not_done": "draft",
        })
        self.message_post(body=f"""<ul><li>Motif de Retour: {reason}</li><ul/>""")
        self._update_purchase_order_state()

    def remettre_to_draft(self):
        for rec in self:
            rec.state_attachemnet = "draft"

    def create_invoice(self):
        for rec in self:
            existing_invoices = self.env['account.move'].search([('id', '=', rec.account_move_id.id), ('move_type', '=', 'in_invoice')])

            if existing_invoices:
                existing_invoices.unlink()

            invoice_vals = {
                'move_type': 'in_invoice',
                'partner_id': rec.supplier_id.id,
                'invoice_origin': rec.purchase_id.name,
                'site_id': rec.site_id.id,
                'is_attachment': True,
                'decompte': rec.number,
                'currency_id': rec.purchase_id.currency_id.id,
                'avance': rec.avance,
                'penalty': rec.penalty,
                'return_of_guarantee': rec.return_of_guarantee,
                'invoice_type': 'standard',
                'invoice_line_ids': [],
            }

            tax_amount = 0
            for line in rec.line_ids:
                tax_amount = sum(tax.amount for tax in line.tax_ids)
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'quantity': 1,
                    'price_unit': line.amount_ht_invoiced,
                    'tax_ids': line.tax_ids,
                    'account_id': self.env['account.account'].search([('code', '=', '6058000')], limit=1).id,
                    'exclude_from_invoice_tab': False,
                    'credit': 0,
                }))

            tax_amount_invoiced = rec.amount_invoiced * (tax_amount / 100)
            # invoice_vals['invoice_line_ids'].append((0, 0, {
            #     'product_id': rec.line_ids[0].product_id.id,
            #     'account_id': self.env['account.account'].search([('code', '=', '4454000')], limit=1).id,
            #     'debit': rec.amount_invoiced * (tax_amount / 100),
            #     'name': 'TVA Recuperable sur services extérieurs et autres charges',
            #     'exclude_from_invoice_tab': True,
            #     'credit': 0,
            # }))
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'product_id': rec.line_ids[0].product_id.id,
                'name': 'Pénalité (- montant de la pénalité)',
                'quantity': 1,
                'price_unit': rec.penalty_red,
                'account_id': self.env['account.account'].search([('code', '=', '6058000')], limit=1).id,
                'exclude_from_invoice_tab': True,
                'credit': 0,
            }))
            total_credit = (rec.amount_invoiced + (tax_amount_invoiced) + rec.penalty_red) - (rec.avance_red + rec.rg_red + rec.penalty_red)
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'product_id': rec.line_ids[0].product_id.id,
                'quantity': 1,
                'price_unit': abs(total_credit) * -1,
                'account_id': self.env['account.account'].search([('code', '=', '4013000')], limit=1).id,
                'exclude_from_invoice_tab': True,
                'credit': total_credit,
            }))
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'product_id': rec.line_ids[0].product_id.id,
                'account_id': self.env['account.account'].search([('code', '=', '4817000')], limit=1).id,
                'quantity': 1,
                'price_unit': abs(rec.rg_red) * -1,
                'exclude_from_invoice_tab': True,
            }))
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'product_id': rec.line_ids[0].product_id.id,
                'account_id': self.env['account.account'].search([('code', '=', '4093000')], limit=1).id,
                'quantity': 1,
                'price_unit': abs(rec.avance_red) * -1,
                'exclude_from_invoice_tab': True,
            }))
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'product_id': rec.line_ids[0].product_id.id,
                'account_id': self.env['account.account'].search([('code', '=', '4013000')], limit=1).id,
                'quantity': 1,
                'price_unit': abs(rec.penalty_red) * -1,
                'exclude_from_invoice_tab': True,
            }))
            # raise Exception(len(invoice_vals['invoice_line_ids']), invoice_vals['invoice_line_ids'])
            invoice = self.env['account.move'].create(invoice_vals)

            rec.is_invoiced = True

            # invoice.write({
            #     'name': rec.number,
            # })

            rec.account_move_id = invoice.id

            # return {
            #     'type': 'ir.actions.act_window',
            #     'name': 'Invoice',
            #     'res_model': 'account.move',
            #     'res_id': invoice.id,
            #     'view_mode': 'form',
            #     'view_id': self.env.ref('account_plus.view_move_form_bo').id,
            #     'target': 'current',
            # }

    def open_confirmation_wizard(self):
        previous_entries = self.search([("purchase_id", "=", self.purchase_id.id)])
        sum_previous_avances = sum(entry.avance for entry in previous_entries)
        reliquat = self.amount_avance - sum_previous_avances

        message = None
        if self.is_bill:
            message = "Voulez-vous vraiment créer la facture de décompte?"
            if self.accumulations_work == self.accumulation_previous_amounts:
                message = "Rien à facturer. Continuer?"
        elif self.avance and reliquat != 0:
            message = f"Attention: La déduction d'avance a été saisie, mais un reliquat de {reliquat} reste à régler. Souhaitez-vous confirmer?"
        elif self.amount_avance and not self.avance:
            message = "Attention: La déduction d'avance n'a pas été saisie. Souhaitez-vous confirmer?"

        if message:
            return {
                "name": "Confirmation",
                "type": "ir.actions.act_window",
                "res_model": "decompte.confirmation.wizard",
                "view_mode": "form",
                "target": "new",
                "context": {
                    "default_message": message,
                }
            }

        method = self.env.context.get("method")
        if method == "validated_dz_action":
            self.validated_dz_action()
        elif method == "provider_validation_action":
            self.provider_validation_action()
        elif method:
            self.action_done()

        self._update_purchase_order_state()

    def validated_dz_action(self):
        for rec in self:
            rec.state_decompte = "validated_dz"
            rec.state_decompte_not_done = "validated_dz"

    def action_create_decompte_bill(self):
        move_id = self.env['account.move'].search([
            ('id', '=', self.account_move_id.id), 
            ('decompte', '=', self.number), 
            ('move_type', '=', 'in_invoice'), 
            ('move_type_code', '=', 'inv_entry')], limit=1
        )
        if self.accumulations_work != self.accumulation_previous_amounts:
            if not move_id:
                move_type = self.env["account.move.type"].search([("name", "=", "Décompte")], limit=1)
                invoice_vals = {
                    "move_type": "in_invoice",
                    "partner_id": self.supplier_id.id,
                    "invoice_payment_term_id": self.supplier_id.property_supplier_payment_term_id.id,
                    "invoice_origin": self.purchase_id.name,
                    "site_id": self.site_id.id,
                    "is_attachment": True,
                    "decompte": self.number,
                    "avance": self.avance,
                    "penalty": self.penalty,
                    "return_of_guarantee": self.return_of_guarantee,
                    "move_type_id": move_type.id if move_type else False,
                    "invoice_line_ids": [],
                }
                for line in self.line_ids:
                    if line.amount_ht_invoiced != 0:
                        percentage = (line.amount_ht_invoiced / self.amount_invoiced)
                        invoice_vals["invoice_line_ids"].append((0, 0, {
                            "product_id": line.product_id.id,
                            "name": line.name,
                            "quantity": 1,
                            "price_unit": line.amount_ht_invoiced - (self.penalty * percentage),
                            "tax_ids": line.tax_ids,
                            "account_id": self.env["account.account"].search([("code", "=", "6058000")], limit=1).id,
                            "exclude_from_invoice_tab": False,
                            "credit": 0,
                        }))
                invoice = self.env["account.move"].create(invoice_vals)
                invoice.recompute_dynamic_lines()
                self.account_move_id = invoice.id
            else:
                raise ValidationError("Une facture a déjà été créée pour ce décompte.")
        self.write({
            "state_decompte": "bill",
            "state_decompte_not_done": "bill",
            "is_invoiced": True,
        })

    def open_cancellation_reason_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Assistant de Retour",
            "res_model": "cancellation.reason",
            "view_mode": "form",
            "target": "new",
        }

    def provider_validation_action(self):
        if not self.is_done:
            self.write({
                "state_decompte": "done",
                "state_decompte_not_done": "done",
                "is_bill": True,
            })
        else:
            self.state_decompte = "provider_validated"
    
    def remettre_to_validated_dz_done(self, reason=None):
        self.write({
            "state_decompte": "validated_dz",
            "state_decompte_not_done": "validated_dz",
            "is_bill": False,
        })
        self.message_post(body=f"""<ul><li>Motif de Retour: {reason}</li><ul/>""")
        self._update_purchase_order_state()

    def remettre_to_validated_dz_not_done(self, reason=None):
        self.write({
            "state_decompte_not_done": "validated_dz",
            "state_decompte": "validated_dz",
            "is_bill": False,
        })
        self.message_post(body=f"""<ul><li>Motif de Retour: {reason}</li><ul/>""")
        self._update_purchase_order_state()

    def remettre_to_provider_validated(self, reason=None):
        self.write({
            "state_decompte": "provider_validated",
            "is_bill": False,
        })
        self.message_post(body=f"""<ul><li>Motif de Retour: {reason}</li><ul/>""")
        self._update_purchase_order_state()

    def remettre_to_dt(self, reason=None):
        self.write({
            "state_decompte": "done",
            "state_decompte_not_done": "done",
        })
        self.message_post(body=f"""<ul><li>Motif de Retour: {reason}</li><ul/>""")
        self._update_purchase_order_state()

    @api.depends('purchase_id', 'number')
    def _compute_is_remettre_invisible(self):
        for rec in self:
            invoice = self.env['account.move'].search([('invoice_origin', '=', rec.purchase_id.name), ('decompte', '=', rec.number)], limit=1)
            rec.is_remettre_invisible = not bool(invoice)

    def action_done(self):
        self.write({
            "is_bill": True,
            "state_decompte": "done",
            "state_decompte_not_done": "done",
        })

    def unlink(self):
        for record in self:
            if record.state_attachemnet != 'draft':
                raise ValidationError(
                    "Vous ne pouvez pas supprimer cet attachement car son état n'est pas 'Brouillon'."
                )
        return super(PurchaseEntry, self).unlink()
               
    @api.constrains('start_date', 'end_date')
    def _check_start_date_after_end_date(self):
        for record in self:
            if record.start_date >= record.end_date:
                raise ValidationError(_("La date de début d'attachement doit être postérieure à la date de fin d'attachement."))
            
            if record.purchase_id.date_approve:
                date_approve = fields.Date.from_string(record.purchase_id.date_approve)
                if record.start_date < date_approve:
                    raise ValidationError(_("La date de début d'attachement doit être postérieure à la date du bon de commande."))

            
            last_entry = self.env['purchase.entry'].search([('site_id', '=', record.site_id.id),('is_invoiced', '=', True),('purchase_id', '=', record.purchase_id.id)], order='id desc', limit=1)
            if last_entry and last_entry.end_date:
                if record.start_date <= last_entry.end_date:
                    last_date_formatted = last_entry.end_date.strftime('%d-%m-%Y')
                    raise ValidationError(_(
                        "La date de début d'attachement doit être postérieure à la date du dernier attachement ({last_date})."
                    ).format(last_date=last_date_formatted))

    def write(self, values):
        result = super().write(values)
        if "is_done" in values:
            self._update_purchase_order_state()
        return result

    @api.depends('number')
    def _compute_is_facture_not_draft(self):
        for entry in self:
            facture = self.env['account.move'].search([('ref', '=', entry.number)], limit=1)
            # raise Exception(facture.state)

            if facture and facture.state != 'draft':
                entry.is_facture_not_draft = True
            else:
                entry.is_facture_not_draft = False

    def action_mark_as_final(self):
        self.write({"is_done": True})

    def action_get_decompte_final(self, readonly=False, nocreate=False):
        # domain = [
        #     '|',
        #     ('is_done', '=', True),
        #     '&',
        #     ('under_ninty_five', '=', False),
        #     ('state_attachemnet', '=', 'internal_validated'),
        # ]

        self.env["purchase.entry"].search([])._compute_under_ninty_five()

        values = self.env["purchase.entry"]
        values |= self.env["purchase.entry"].search([('is_done', '=', True)])
        values |= self.env["purchase.entry"].search([('under_ninty_five', '=', False), ('state_attachemnet', '=', 'internal_validated')])

        context = {
            'delete' : 0,
            'create' : 0,
        }

        return {
            'name': 'Décompte final',
            'type': 'ir.actions.act_window',
            'view_mode': 'lis,form',
            'res_model': 'purchase.entry',
            'views': [
                (self.env.ref('purchase_plus.view_purchase_entry_decompt_tree').id, 'list'),
                (self.env.ref('purchase_plus.purchase_entry_decompt_view_form').id, 'form')
            ],
            'domain': [("id", "in", values.ids)],
            'context': context
        }