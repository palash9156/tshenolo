frappe.ui.form.on("Consignment Note", {
	setup(frm) {
		frm.set_query("source_warehouse", () => ({
			filters: { company: frm.doc.company, is_group: 0 },
		}));
		frm.set_query("item_code", "items", () => ({ filters: { is_stock_item: 1 } }));
		frm.set_query("batch_no", "items", (doc, cdt, cdn) => ({
			filters: { item: locals[cdt][cdn].item_code },
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1 && ["Issued", "Partially Utilised"].includes(frm.doc.status)) {
			const method_root = "tshenolo.tshenolo_selling.doctype.consignment_note.consignment_note.";
			frm.add_custom_button(
				__("Consignment Utilisation"),
				() => frappe.model.open_mapped_doc({ method: method_root + "make_consignment_utilisation", frm }),
				__("Create")
			);
			frm.add_custom_button(
				__("Consignment Return"),
				() => frappe.model.open_mapped_doc({ method: method_root + "make_consignment_return", frm }),
				__("Create")
			);
			frm.page.set_inner_btn_group_as_primary(__("Create"));
		}
	},
});
