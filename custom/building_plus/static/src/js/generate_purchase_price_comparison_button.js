odoo.define("building_plus.tree_button", function (require) {
  "use strict";
  var ListController = require("web.ListController");
  var ListView = require("web.ListView");
  var viewRegistry = require("web.view_registry");
  var rpc = require("web.rpc");
  var TreeButton = ListController.extend({
    buttons_template: "building_plus.buttons",
    events: _.extend({}, ListController.prototype.events, {
      "click .open_wizard_action": "_OpenWizard",
    }),
    _OpenWizard: function () {
      var self = this;
      rpc
        .query({
          model: "purchase.price.comparison",
          method: "return_request_purchase_price_comparison",
          args: [""],
        })
        .then(function (action) {
          self.do_action(action);
        })
    },
  });
  var LotsBulletinsListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
      Controller: TreeButton,
    }),
  });
  viewRegistry.add("generate_purchase_price_comparison", LotsBulletinsListView);
});
