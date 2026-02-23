from odoo import api, fields, models
import base64


class CNSSImportTxtWizard(models.TransientModel):
    _name = 'cnss.import.txt.wizard'

    file = fields.Binary(string='Fichier')

    def import_file(self):
        txt_data = (base64.b64decode(self.file).decode('utf-8')).strip()
        data_list = txt_data.split('\n')

        year = data_list[1][10:14]
        month = data_list[1][14:16]

        cnss_bds = self.env['cnss.bds']
        records_with_traite = cnss_bds.search([('l_annee', '=', year), ('l_mois', '=', month), ('l_status', '=', 'TRAITE')])
        records_with_non_traite = cnss_bds.search([('l_annee', '=', year), ('l_mois', '=', month)])

        if records_with_traite:
            return {'type': 'ir.actions.act_window_close'}
        else:
            records_with_non_traite.unlink()
            for el in data_list[2:-1]:
                self.env['cnss.bds'].create({
                    'l_type_enreg': el[0:3],
                    'n_num_affilie': el[3:10],
                    'l_annee': el[10:14],
                    'l_mois': el[14:16],
                    'n_num_assure': el[16:25],
                    })
            return {'type': 'ir.actions.act_window_close'}
