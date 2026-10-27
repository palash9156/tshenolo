frappe.ui.form.on("Tshenolo Settings", {
	setup(frm) {
		frm.set_query("consignment_parent_warehouse", () => ({ filters: { is_group: 1 } }));
		frm.set_query("default_service_item", () => ({ filters: { is_stock_item: 0 } }));
	},
});
