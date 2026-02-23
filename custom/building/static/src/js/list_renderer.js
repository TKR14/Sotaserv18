odoo.define('production_operator_missiongroup.custom_list_renderer', function (require) {

    "use strict";

    console.log("Javascript works!");

    var ListRenderer = require('web.ListRenderer');
    var CustomListRenderer = ListRenderer.include({

        events: _.extend({}, ListRenderer.prototype.events, {
            'click thead th.o_column_sortable': '_onSortColumn',
        }),

        _onSortColumn: function (ev) {
            if (this.$el.hasClass('disable_sort')) {
                ev.preventDefault();
                return false;
            }
            return this._super.apply(this, arguments);
        },
    });

    return CustomListRenderer;
});