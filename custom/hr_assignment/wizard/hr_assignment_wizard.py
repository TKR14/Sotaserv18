from odoo import models, fields, api

from datetime import datetime, timedelta
import xlsxwriter
import base64
import os
import json
from math import floor
from calendar import monthrange


class HrAssignmentWizardMonth(models.Model):
    _name = "hr.assignment.wizard.month"

    number = fields.Integer(string="#")
    name = fields.Char(string="Nom")

    @api.model
    def initialize(self):
        if self.search_count([]) > 0: return
        months = [
            (1, "Janvier"),
            (2, "Février"),
            (3, "Mars"),
            (4, "Avril"),
            (5, "Mai"),
            (6, "Juin"),
            (7, "Juillet"),
            (8, "Août"),
            (9, "Septembre"),
            (10, "Octobre"),
            (11, "Novembre"),
            (12, "Décembre"),
        ]
        self.create([{"number": number, "name": name} for number, name in months])


class HrAssignmentWizardYear(models.Model):
    _name = "hr.assignment.wizard.year"

    name = fields.Integer("Année")

    @api.model
    def initialize(self, ids):
        lines = self.env["hr.assignment.timeclock.line"].search([("assignment_line_id.assignment_id", "in", ids)])
        years = sorted(list(set(date.year for date in lines.mapped("date"))))
        exist = self.search([("name", "in", years)]).mapped("name")

        self.search([("name", "not in", years)]).unlink()
        self.create([{"name": year} for year in years if year not in exist])

    def months(self, ids):
        lines = self.env["hr.assignment.timeclock.line"].search([("assignment_line_id.assignment_id", "in", ids)])
        dates = lines.filtered(lambda line: line.date.year == self.name).mapped("date")
        return [date.month for date in dates]


class HrAssignmentWizard(models.TransientModel):
    _name = "hr.assignment.wizard"

    @api.depends("year")
    def _year_months(self):
        months = self.year and self.year.months(self._context.get("active_ids")) or []
        self.months += self.env["hr.assignment.wizard.month"].search([("number", "in", months)])

    year = fields.Many2one("hr.assignment.wizard.year", string="Année")
    month = fields.Many2many("hr.assignment.wizard.month", string="Mois")
    months = fields.Many2many("hr.assignment.wizard.month", string="Mois", compute="_year_months")

    line_ids = fields.One2many("hr.assignment.wizard.line", "parent_id", string="Lignes")

    @api.onchange("year")
    def _onchange_year(self):
        self.month = False

    def button_download(self):
        def _day(line):
            day = line.date.day
            day = day + 3 if day > 15 else day + 2
            hours = line.hours
            return {
                "day": day,
                "hours": hours,
            }
        def _employee(employee, lines):
            employee = employee
            lines = lines.filtered(lambda line: line.employee_id == employee)
            return {
                "employee": {"number": employee.sudo().registration_number, "name": employee.name},
                "lines": [_day(line) for line in lines],
            }
        def _subsheet(job, site, lines):
            employees = lines.mapped("employee_id")
            return {
                "job": job.name,
                "site": site.name,
                "employees": [_employee(employee, lines) for employee in employees],
            }
        def _column(number):
            letter = ""
            while number > 0:
                number, remainder = divmod(number - 1, 26)
                letter = chr(65 + remainder) + letter
            return letter

        # START
        PATH = "/mnt/extra-addons/hr_assignment"
        all_assignments = self.env["hr.assignment"].browse(self._context.get("active_ids"))
        all_months = self.month
        all_jobs = all_assignments.mapped("line_ids").mapped("timeclock_line_ids").mapped("job_id")

        data_structure = [
            {
                "number": 1,
                "jobs": [
                    {
                        "name": "Macon",
                        "sites": [
                            {
                                "name": "COCODY",
                                "lines": [] 
                            }
                        ]
                    }
                ]
            }
        ]
        all_data = []
        for month in all_months:
            data_jobs = []
            for job in all_jobs:
                data_sites = []
                for assignment in all_assignments:
                    lines = assignment.line_ids.timeclock_line_ids.filtered(lambda line: line.date.year == self.year.name and line.date.month == month.number and line.job_id.id == job.id)
                    if bool(len(lines)):
                        data_sites.append({
                            "site": assignment.site_id,
                            "lines": lines,
                        })
                if bool(len(data_sites)):
                    data_jobs.append({
                        "job": job,
                        "sites": data_sites,
                    })
            if bool(len(data_jobs)):
                all_data.append({
                    "month": month,
                    "jobs": data_jobs,
                })

        if not bool(len(all_data)): return

        path = PATH + f"/Suivi.xlsx"
        workbook = xlsxwriter.Workbook(path)

        # FORMATS
        def _format(format, column=False):
            column_format = {"bg_color": "F2F2F2"}
            border_format = {
                "border": 1,
                "border_color": "#666666",
            }
            format.update(border_format)
            if column: format.update(column_format)
            return workbook.add_format(format)

        job_format = _format({"bold": True, "font_size": 14, "align": "center", "valign": "vcenter", "bg_color": "#D9D9D9"})

        column_day_format = _format({"align": "center"}, True)
        column_name_format = _format({"bold": True}, True)
        column_number_format = _format({"align": "right"}, True)

        th_format = _format({"align": "center", "bold": True}, True)
        tth_format = _format({"align": "center", "bold": True, "bg_color": "#D9D9D9"})
        ttth_format = _format({"align": "center", "bold": True, "bg_color": "#BFBFBF"})

        int_format = _format({"align": "center", "num_format": 1})
        str_format = _format({"bold": True})
        number_format = _format({"align": "right"})

        for data in all_data:
            # PARAMS
            month_name = data["month"].name
            month = data["month"].number
            _, month_days = monthrange(datetime.today().year, month)
            columns = ["#", "Nom et prénom"] + list(range(1, 16)) + ["TH"] + list(range(16, month_days + 1)) + ["TH", "TH"]

            # RANGES
            columns_len = len(columns)
            columns_half = floor(columns_len / 2)

            first_col = 1
            first_row = 1

            first_th = columns.index("TH") + 1
            first_from = columns.index(1) + 1
            first_to = columns.index(15) + 1

            second_th = columns.index("TH", first_th) + 1
            second_from = columns.index(16) + 1
            second_to = columns.index(month_days) + 1

            third_th = columns.index("TH", second_th) + 1
            hash = columns.index("#") + 1

            sheet = workbook.add_worksheet(month_name)

            row = first_row

            for job in data["jobs"]:
                sites = job["sites"]
                job = job["job"]

                sheet.merge_range(row, first_col, row + 1, columns_len, job.name, job_format)
                row += 2

                for i, column in enumerate(columns, first_col):
                    if i == 1:
                        format = column_number_format
                    elif i == 2:
                        format = column_name_format
                    elif i in [first_th, second_th]:
                        format = th_format
                    elif i == third_th:
                        format = tth_format
                    else:
                        format = column_day_format
                    sheet.write(row, i, column, format)
                row += 1

                for site in sites:
                    lines = site["lines"]
                    site = site["site"]
                    employees = _subsheet(job, site, lines)
                    employees = employees["employees"]
                    rows = len(employees)

                    sheet.write(row, 1, "", tth_format)
                    sheet.merge_range(row, 2, row, first_th - 1, site.name, tth_format)
                    # sheet.merge_range(row, 3, row, first_th - 1, "", th_format)
                    sheet.merge_range(row, first_th + 1, row, second_th - 1, "", tth_format)

                    sheet.write_formula(row, first_th, f"=SUM({_column(first_th + 1)}{row + 2}:{_column(first_th + 1)}{row + rows + 1})", tth_format)
                    sheet.write_formula(row, second_th, f"=SUM({_column(second_th + 1)}{row + 2}:{_column(second_th + 1)}{row + rows + 1})", tth_format)
                    sheet.write_formula(row, third_th, f"=SUM({_column(first_th + 1)}{row + 1},{_column(second_th + 1)}{row + 1})", ttth_format)
                    row += 1

                    for employee in employees:
                        sheet.conditional_format(row, 3, row, columns_len, {"type": "cell", "criteria": "==", "value": '""', "format": int_format})
                        sheet.conditional_format(row, 3, row, columns_len, {"type": "cell", "criteria": "!=", "value": 0, "format": int_format})

                        name = employee["employee"]["name"]
                        number = employee["employee"]["number"]
                        lines = employee["lines"]

                        sheet.write(row, 1, number, number_format)
                        sheet.write(row, 2, name, str_format)

                        for line in lines:
                            day = line["day"]
                            hours = line["hours"]
                            sheet.write(row, day, hours, int_format)

                        sheet.write_formula(row, first_th, f"=SUBTOTAL(109,{_column(first_from + 1)}{row + 1}:{_column(first_to + 1)}{row + 1})", th_format)
                        sheet.write_formula(row, second_th, f"=SUBTOTAL(109,{_column(second_from + 1)}{row + 1}:{_column(second_to + 1)}{row + 1})", th_format)
                        sheet.write_formula(row, third_th, f"=SUM({_column(first_th + 1)}{row + 1},{_column(second_th + 1)}{row + 1})", tth_format)
                        row += 1
                row += 1

            sheet.autofit()
            sheet.set_column(0, 0, 2)
            sheet.set_column(1, 1, 6)
            sheet.set_column(3, columns_half, 2.2)
            sheet.set_column(columns_half + 1, columns_len, 2.2)
            sheet.set_column(first_th, first_th, 6)
            sheet.set_column(second_th, second_th, 6)
            sheet.set_column(third_th, third_th, 6)
            sheet.ignore_errors({"number_stored_as_text": f"{_column(hash + 1)}1:{_column(hash + 1)}1048576"})

        workbook.close()

        actions = []
        path = PATH + f"/Suivi.xlsx"
        try:
            data = open(path, "rb").read()
        except FileNotFoundError:
            pass
        else:
            encoded = base64.b64encode(data)
            file_name = f"Suivi"
            attachment = self.env["ir.attachment"].create({
                "name": file_name,
                "datas": encoded,
            })
            actions.append({
                "type": "ir.actions.act_url",
                "url": f"/web/content/{attachment.id}?download=true",
                "target": "new"
            })
            os.remove(path)

        return {
            "type": "ir.actions.act_multi",
            "actions": actions + [{"type": "ir.actions.act_window_close"}],
            # "actions": actions,
        }


class HrAssignmentWizardLine(models.TransientModel):
    _name = "hr.assignment.wizard.line"

    @api.model
    def default_get(self, fields):
        result = super(HrAssignmentWizardLine, self).default_get(fields)
        last_line = self.search([("parent_id", "=", self._context.get("parent_id"))], order="id desc", limit=1)
        # raise Exception(self._context.get("parent_id"))
        # raise Exception(self.env["hr.assignment.wizard"].browse(self._context.get("parent_id")).line_ids)

        if bool(last_line):
            result["date"] = last_line["date"] + timedelta(days=1)
            result["job_category_id"] = last_line["job_category_id"].id
            result["job_id"] = last_line["job_id"].id
            result["uom_id"] = last_line["uom_id"].id
            result["employee_id"] = last_line["employee_id"].id
            result["is_present"] = last_line["is_present"]
            result["hours"] = last_line["hours"]

        return result

    parent_id = fields.Many2one("hr.assignment.wizard", "Parent")
    date = fields.Date("Date")
    job_category_id = fields.Many2one("hr.assignment.job.category", string="Catégorie")
    job_id = fields.Many2one("hr.job", string="Poste")
    uom_id = fields.Many2one("uom.uom", string="Unité")
    employee_id = fields.Many2one("hr.employee", string="Employé")
    is_present = fields.Boolean("Présent(e)", default=True)
    hours = fields.Integer("Heures travaillées")

    def button_add_timeclock_lines(self):
        model_request = self.env["hr.assignment.request"]
        model_request_line = self.env["hr.assignment.request.line"]
        model_assignment_line = self.env["hr.assignment.line"]
        model_timeclock = self.env["hr.assignment.timeclock"]
        model_timeclock_line = self.env["hr.assignment.timeclock.line"]

        assignment = self.env["hr.assignment"].browse(self._context.get("assignment_id"))
        site_id = assignment.site_id.id

        for line in self:
            request = model_request.search([("name", "=", "/"), ("site_id", "=", site_id), ("state", "=", "closed")], limit=1)
            if not bool(request):
                request = model_request.create(
                    {
                        "site_id": site_id,
                        "state": "closed",
                    }
                )

            request_line = request.line_ids.filtered(lambda l: l.job_id == line.job_id)
            if not bool(request_line):
                request_line = model_request_line.create(
                    {
                        "request_id": request.id,
                        "job_category_id": line.job_category_id.id,
                        "job_id": line.job_id.id,
                        "uom_id": line.uom_id.id,
                        "state": "closed",
                    }
                )

            assignment_line = assignment.line_ids.filtered(lambda l: l.request_line_id == request_line)
            if not bool(assignment_line):
                assignment_line = model_assignment_line.create(
                    {
                        "request_line_id": request_line.id,
                        "assignment_id": assignment.id,
                        "employee_id": line.employee_id.id,
                        "date_start": line.date,
                        "date_end": line.date,
                        "state": "done",
                        "is_clockable": False,
                    }
                )

            timeclock = model_timeclock.search([("assignment_id", "=", assignment.id), ("date", "=", line.date)], limit=1)
            if not bool(timeclock):
                timeclock = model_timeclock.create(
                    {
                        "assignment_id": assignment.id,
                        "date": line.date,
                    }
                )

            model_timeclock_line.create(
                {
                    "timeclock_id": timeclock.id,
                    "assignment_line_id": assignment_line.id,
                    "is_present": line.is_present,
                    "hours": line.hours,
                }
            )