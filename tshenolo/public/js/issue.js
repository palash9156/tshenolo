frappe.ui.form.on("Issue", {
	setup(frm) {
		frm.set_query("contract", () => ({
			filters: {
				party_type: "Customer",
				docstatus: ["<", 2],
				...(frm.doc.customer ? { party_name: frm.doc.customer } : {}),
			},
		}));
		frm.set_query("serial_no", () => ({
			filters: frm.doc.customer ? { customer: frm.doc.customer } : {},
		}));
	},

	refresh(frm) {
		if (!frm.is_new() && frm.doc.customer && frm.doc.status !== "Closed") {
			frm.add_custom_button(
				__("Service Sales Order"),
				() =>
					frappe.model.open_mapped_doc({
						method: "tshenolo.events.service.make_service_sales_order",
						frm,
					}),
				__("Create")
			);
		}
	},
});
