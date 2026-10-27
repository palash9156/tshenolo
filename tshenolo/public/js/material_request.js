frappe.ui.form.on("Material Request", {
	is_consignment(frm) {
		if (frm.doc.is_consignment) {
			frm.set_value("material_request_type", "Material Transfer");
		}
	},

	salesperson_warehouse(frm) {
		if (frm.doc.is_consignment && frm.doc.salesperson_warehouse) {
			frm.set_value("set_warehouse", frm.doc.salesperson_warehouse);
		}
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.is_consignment && frm.doc.status !== "Stopped") {
			frm.add_custom_button(
				__("Consignment Note"),
				() =>
					frappe.model.open_mapped_doc({
						method: "tshenolo.tshenolo_selling.doctype.consignment_note.consignment_note.make_consignment_note",
						frm,
					}),
				__("Create")
			);
		}
	},
});
