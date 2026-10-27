frappe.ui.form.on("Consignment Utilisation", {
	setup(frm) {
		tshenolo_consignment.setup_note_query(frm);
	},

	consignment_note(frm) {
		tshenolo_consignment.load_pending_items(frm);
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.sales_invoice) {
			frm.add_custom_button(
				__("Sales Invoice"),
				() =>
					frappe.model.open_mapped_doc({
						method: "tshenolo.tshenolo_selling.doctype.consignment_utilisation.consignment_utilisation.make_sales_invoice",
						frm,
					}),
				__("Create")
			);
			frm.page.set_inner_btn_group_as_primary(__("Create"));
		}
	},
});
