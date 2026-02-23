from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    # registration_number =  fields.Char(string='Matricule', required=True, default = None)
    state = fields.Selection([('available', 'Disponible'), ('assigned', 'Affecté')], string="status",
                             default='available')
    work_location = fields.Char('Lieu de Travail', compute='_compute_work_location')
    # _sql_constraints = [('registration_number_uniq', 'unique(registration_number)','Le Numéro de Matricule doit
    # etre unique!'),]

    def _compute_work_location(self):
        for emp in self:
            contract = self.env['hr.contract'].search([('employee_id', '=', emp.id), ('state', '=', 'open')])
            if contract and len(contract) == 1:
                if contract.site_id:
                    emp.work_location = contract.site_id.name
                else:
                    emp.work_location = ''
            else:
                emp.work_location = ''


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    site_id = fields.Many2one('building.site', string='Affaire')

    @api.model
    def create(self, vals):
        res = super(HrAttendance, self).create(vals)
        analytic_obj = self.env['account.analytic.account']
        # analytic_account = analytic_obj.search([('account_analytic_type', '=', 'workforce')])[0]
        analytic_line_obj = self.env['account.analytic.line']
        assignment_obj = self.env['building.assignment.line']
        executed_ressource_obj = self.env['building.executed.ressource']
        uom_id = None
        uom = self.env['uom.uom'].search([('name', '=', 'H')])
        if uom:
            uom_id = uom[0].id
        assignment = assignment_obj.search(
            [('employee_id', '=', res.employee_id.id), ('site_id', '=', res.site_id.id), ('state', '=', 'open')])
        # if assignment:
        #     record_analytic_line = {
        #         'date': res.check_in.date(),
        #         # 'account_id': analytic_account.id,
        #         'site_id': res.site_id.id,
        #         'employee_id': res.employee_id.id,
        #         'product_uom_id': uom_id,
        #         'name': res.employee_id.name,
        #         'amount': res.worked_hours*assignment.cost,
        #         # 'type_analytic_line': 'workforce',
        #         'timesheet_invoice_type': 'non_billable',
        #         'project_id':1,
        #         'unit_amount':res.worked_hours
        #     }

        #     analytic_line_obj.create(record_analytic_line)
        # il faut obligatoirement rajouter filtre par periode excution
        if assignment:
            assignment = assignment[0]
            building_exec = self.env['building.executed'].search(
                [('date_start', '<=', res.check_in), ('date_end', '>=', res.check_in), ('state', '=', 'open')])
            if building_exec:
                executed_ressource = executed_ressource_obj.search(
                    [('executed_id', '=', building_exec.id), ('site_id', '=', res.site_id.id),
                     ('assignment_id', '=', assignment.id)])
                day = (res.check_in.day - building_exec.date_start).days
                attr_to_upate = 'quantity' + str(day)
                if executed_ressource:
                    executed_ressource = executed_ressource[0]
                    executed_ressource.write({attr_to_upate: res.worked_hours, 'attendance_id': res.id})
        return res

    def write(self, vals):
        res = super(HrAttendance, self).write(vals)
        for att in self:
            dat = att.check_in.date().day
            attr_to_upate = 'quantity' + str(day)
            for val in vals:
                if 'worked_hours' in val:
                    assignment = assignment_obj.search(
                        [('employee_id', '=', att.employee_id.id), ('site_id', '=', att.site_id.id),
                         ('state', '=', 'open')])[0]
                    if assignment:
                        amount = val['worked_hours'] * assignment[0].cost,
                        analytic_line = analytic_line_obj.search(
                            [('employee_id', '=', att.employee_id.id), ('site_id', '=', att.site_id.id),
                             ('date', '=', date)])[0]
                        if analytic_line:
                            analytic_line[0].amount = amount
                        executed_ressource = executed_ressource_obj.search(
                            [('employee_id', '=', att.employee_id.id), ('site_id', '=', att.site_id.id),
                             ('assignment_id', '=', assignment.id)])[0]
                        if executed_ressource:
                            executed_ressource[0].wrtie({attr_to_upate: val['worked_hours'], 'attendance_id': att.id})

        return res


# class hr_analytic_timesheet(models.Model):

#     _inherit = "hr.analytic.timesheet"

#     emp_id = fields.Many2one('building.resource', string='Employé',domain=[('type','=','human')])
#     site_id =  fields.Many2one('building.site', string='Affaire')
#     unit_cost = fields.Float('Coût unitaire')

#     @api.multi
#     def on_change_emp_id(self,emp_id=False):
#         res = {'value':{}}
#         if emp_id:
#             emp = self.env['building.resource'].browse(emp_id)
#             res['value'].update({'unit_cost':emp.schedule_cost})
#         return res

#     def on_change_unit_amount(self,unit_amount=False,unit_cost=False):
#         res = {'value':{}}
#         if unit_cost and unit_amount:
#             amount = unit_amount*unit_cost or 0.0
#             prec = self.env['decimal.precision'].precision_get('Account')
#             result = round(amount, prec)
#             res['value'].update({'amount': result})
#         return res

#     @api.v7
#     def create(self,cr,uid,vals,context=None):
#         if context is None:context = {}
#         res = super(hr_analytic_timesheet,self).create(cr,uid,vals,context=context)
#         hrat = self.browse(cr,uid,res,context=context)
#         self.pool.get('account.analytic.line').write(cr,uid,[hrat.line_id.id],{'site_id':hrat.site_id.id,'type':'timesheet'})
#         return res


#     def _getEmployeeProduct(self, cr, uid, context=None):
#         if context is None:
#             context = {}
#         prod_obj = self.pool.get('product.product')
#         prod_id = prod_obj.search(cr, uid, [('is_timesheet', '=',True)], context=context,limit=1)
#         if prod_id:
#             prod = prod_obj.browse(cr, uid, prod_id[0], context=context)
#             return prod.id
#         return False

#     def _getEmployeeUnit(self, cr, uid, context=None):
#         if context is None:
#             context = {}
#         prod_obj = self.pool.get('product.product')
#         prod_id = prod_obj.search(cr, uid, [('is_timesheet', '=',True)], context=context,limit=1)
#         if prod_id:
#             prod = prod_obj.browse(cr, uid, prod_id[0], context=context)
#             return prod.uom_id.id
#         return False

#     def _getGeneralAccount(self, cr, uid, context=None):
#         if context is None:
#             context = {}
#         prod_obj = self.pool.get('product.product')
#         prod_id = prod_obj.search(cr, uid, [('is_timesheet', '=',True)], context=context,limit=1)
#         if prod_id:
#             prod = prod_obj.browse(cr, uid, prod_id[0], context=context)
#             a = prod.property_account_expense.id
#             if not a:
#                 a = prod.categ_id.property_account_expense_categ.id
#             if a:
#                 return a
#         return False


class HrJob(models.Model):
    _inherit = 'hr.job'

    cost = fields.Float(string='Cout Unitaire')
    uom_id = fields.Many2one('uom.uom', string='Unité')
    categ_job = fields.Selection([('executor', 'Main d\'œuvre'), ('supervisor', 'Encadrant'), ('manager', 'Management')]
                                 , string="Catégorie Poste", default='executor', required=True)
    profile = fields.Char('Profil', required=True)
    profile_id = fields.Many2one('hr.job.profile', string='Profil ID')
    job_code = fields.Char(related='profile_id.job_code_id.code', string="Code d'emploi", store=True)      # @api.depends('profile_id')
    
    @api.onchange('profile_id')
    def _onchange_profile(self):
        if self.profile_id:
            code = self.env['hr.job.code'].search([('profile_id', '=', self.profile_id.id)], limit=1)
            if code:
                self.job_code_id = code.id

    @api.constrains('name')
    def check_name(self):
        for job in self:
            job_id = self.env['hr.job'].search([('name', '=', job.name), ('id', '!=', job.id),
                                                ('categ_job', '=', job.categ_job), ('profile', '=', job.profile)])
            if job_id:
                raise ValidationError(_('Il existe deja un poste avec le même nom %s!', job.name))

    @api.model
    def create(self, vals):
        res = super(HrJob, self).create(vals)
        if res.profile:
            profile = self.env['hr.job.profile'].search([('name', '=', res.profile), ('categ_job', '=', res.categ_job)])
            if profile:
                res.profile_id = profile[0].id

            else:
                profile = self.env['hr.job.profile'].create({'name': res.profile, 'categ_job': res.categ_job})
                res.profile_id = profile.id
        return res

    def write(self, vals):
        if vals.get("profile") or vals.get("categ_job"):
            profile_id = False
            profile = self.env['hr.job.profile'].search([
                ('name', '=', vals.get('profile', self.profile)),
                ('categ_job', '=', vals.get('categ_job', self.categ_job))
            ])

            if not profile:
                profile = self.env['hr.job.profile'].create({
                    'name': vals.get('profile', self.profile),
                    'categ_job': vals.get('categ_job', self.categ_job)
                })

            profile_id = profile.id

            check_if_old_profile_is_used = self.env['hr.job'].search([
                ('profile_id', '=', self.profile_id.id),
                ('id', '!=', self.id)
            ])

            if not check_if_old_profile_is_used:
                self.profile_id.unlink()

            vals['profile_id'] = profile_id
        return super(HrJob, self).write(vals)

    def unlink(self):
        check_if_profile_is_used = self.env['hr.job'].search([('profile_id', '=', self.profile_id.id), ('id', '!=', self.id)])
        if not check_if_profile_is_used:
            self.profile_id.unlink()

        return super(HrJob, self).unlink()

    def update_profiles(self):
        for job in self.env['hr.job'].search([]):
            if job.profile:
                profile = self.env['hr.job.profile'].search([('name', '=', job.profile), ('categ_job', '=', job.categ_job)], limit=1)
                if not profile:
                    profile = self.env['hr.job.profile'].create({'name': job.profile, 'categ_job': job.categ_job})
                job.update({
                    "profile_id": profile.id
                })


class HrJobProfile(models.Model):
    _name = 'hr.job.profile'

    name = fields.Char('Profil')
    categ_job = fields.Selection(
        [('executor', 'Main d\'œuvre'), ('supervisor', 'Encadrant'), ('manager', 'Management')],
        string="Catégorie Poste", default='executor')
    job_code_id = fields.Many2one('hr.job.code', string="Code d'emploi") 

class JobCode(models.Model):
    _name = 'hr.job.code'
    _description = 'Code d\'emploi'

    code = fields.Char(string='Code', required=True)
    profile_id = fields.Many2one('hr.job.profile', string='Profil')
    profile_ids = fields.One2many('hr.job.profile', 'job_code_id', string="Profils associés")

class MaintenanceEquipmentCategory(models.Model):
    _inherit = 'maintenance.equipment.category'

    cost = fields.Float(string='Cout Unitaire')
    uom_id = fields.Many2one('uom.uom', string='Unité')
    nature_equip = fields.Selection(
        [('install_site', 'Installation Chantier'), ('other', 'Outillage'), ('other_elec', 'Outillage Electrique')],
        string="Nature équipement", default='install_site')


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    state = fields.Selection(
        [('available', 'Disponible'), ('assigned', 'Affecté'), ('under_reparation', 'En réparation'),
         ('scrapped', 'En rebut')], string="status", default='available')
    consumption = fields.Float(string='Consommation(L/J)')
    nature_equip = fields.Selection(related='category_id.nature_equip', string="Nature équipement", store=True)
    code = fields.Char('Code')
    code_immo = fields.Char('Numéro Immo')


class HrAttendance(models.Model):
    _inherit = "hr.contract"

    site_id = fields.Many2one('building.site', string='Affaire')

    @api.onchange('site_id')
    def _onchange_site_id(self):
        if self.site_id:
            self.workplace = self.site_id.name


class HrTimePayroll(models.Model):
    _inherit = "hr.time.payroll"

    site_id = fields.Many2one('building.site', string='Affaire')


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()
        for slip in self:
            slip.move_id.site_id = slip.contract_id.site_id.id
        return res