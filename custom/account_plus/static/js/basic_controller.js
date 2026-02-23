odoo.define('account_plus.BasicController', function (require) {
    "use strict";

    const BasicController = require('web.BasicController');
    const core = require('web.core');
    const Dialog = require('web.Dialog');
    const _t = core._t;

    BasicController.include({
        _deleteRecords: function (ids) {
            const self = this;

            function doIt() {
                return self.model
                    .deleteRecords(ids, self.modelName)
                    .then(self._onDeletedRecords.bind(self, ids));
            }

            if (this.confirmOnDelete) {
                let isPaymentWithCheck = false;
            
                if (this.modelName === 'account.payment') {
                    for (let handle in self.model.localData) {
                        const record = self.model.localData[handle];
                
                        // Check if this handle is in the list of ids to delete
                        if (ids.includes(handle) && record.data && record.data.check_id) {
                            console.log('Check ID:', record.data.check_id);
                            isPaymentWithCheck = true;
                            break;
                        }
                    }
                }
            
                const message = isPaymentWithCheck
                    ? (ids.length > 1
                        ? "Voulez-vous réellement supprimer ces enregistrements? Les chèques liés seront annulés."
                        : "Voulez-vous réellement supprimer cet enregistrement? Le chèque lié sera annulé.")
                    : (ids.length > 1
                        ? _t("Are you sure you want to delete these records?")
                        : _t("Are you sure you want to delete this record?"));
            
                Dialog.confirm(this, message, {
                    confirm_callback: doIt
                });
            } else {
                doIt();
            }
        }
    });

    return BasicController;
});
