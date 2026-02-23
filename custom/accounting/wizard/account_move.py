from odoo import models
from datetime import datetime
import re


class account_move(models.Model):
    _inherit = 'account.move'

    def get_solde(self, date_range, state,  compte, to_date=None):
        compte_debiteur = ['2', '3', '5', '6']
        compte_crediteur = ['1', '4', '7', '29', '55', '28', '39']

        debit = 0
        credit = 0
        amount = 0

        to_date = datetime.strptime(to_date, "%Y-%m-%d").date()

        # La date N
        if date_range == 1:
            from_date = datetime.strptime(f"{to_date.year}-01-01", "%Y-%m-%d").date()
        # La date N - 1
        elif date_range == -1:
            to_date = datetime.strptime(f"{to_date.year - 1}-12-31", "%Y-%m-%d").date()
            from_date = datetime.strptime(f"{to_date.year}-01-01", "%Y-%m-%d").date()

        # Toutes les pieces
        if state == "all":
            for piece in self:
                if piece.date <= to_date and piece.date >= from_date:
                    for line in piece.line_ids:
                        if re.search(f'^{compte}', str(line.account_id.code)):
                            debit += line.debit
                            credit += line.credit

        
        # Les pieces confirmé
        elif state == "posted":
            for piece in self:
                if piece.state == "posted" and piece.date <= to_date and piece.date >= from_date:
                        for line in piece.line_ids:
                            if re.search(f'^{compte}', str(line.account_id.code)):
                                debit += line.debit
                                credit += line.credit
                

        if compte[0] in compte_crediteur:
            amount = credit - debit
        elif compte[0] in compte_debiteur:
            amount = debit - credit

        return amount


    # CALC BILAN
    def calc_bilan(self, type, date, account):
        to_date = datetime.strptime(date, "%Y-%m-%d").date()
        from_date = datetime.strptime(f"{to_date.year}-01-01", "%Y-%m-%d").date()

        def check_date(piece_date):
            # if account[0] in ['6', '7']:
            #     if piece_date <= to_date and piece_date >= from_date:
            #         return True
            if piece_date <= to_date:
                return True
            return False
        
        debit = 0
        credit = 0

        for piece in self:
            if check_date(piece.date):
                for line in piece.line_ids:
                    if re.search(f'^{account}', str(line.account_id.code)):
                        debit += line.debit
                        credit += line.credit

        if type == 1:
            return debit - credit
        if type == 0:
            return credit - debit
        if type == 2:
            return credit
        if type == 3:
            return debit