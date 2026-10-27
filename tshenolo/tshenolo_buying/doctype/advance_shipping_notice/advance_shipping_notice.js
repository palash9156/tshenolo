frappe.ui.form.on("Advance Shipping Notice", {
	setup(frm) {
		frm.set_query("transporter", () => ({ filters: { is_transporter: 1 } }));
		frm.set_query("purchase_order", "items", () => ({
			filters: { supplier: frm.doc.supplier, docstatus: 1 },
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1 && ["In Transit", "Partially Received"].includes(frm.doc.status)) {
			frm.add_custom_button(
				__("Purchase Receipt"),
				() =>
					frappe.model.open_mapped_doc({
						method: "tshenolo.tshenolo_buying.doctype.advance_shipping_notice.advance_shipping_notice.make_purchase_receipt",
						frm,
					}),
				__("Create")
			);
			frm.page.set_inner_btn_group_as_primary(__("Create"));
		}

		if (frm.doc.docstatus === 0 && frm.doc.supplier) {
			frm.add_custom_button(
				__("Purchase Order"),
				() =>
					erpnext.utils.map_current_doc({
						method: "tshenolo.tshenolo_buying.doctype.advance_shipping_notice.advance_shipping_notice.make_advance_shipping_notice",
						source_doctype: "Purchase Order",
						target: frm,
						setters: { supplier: frm.doc.supplier },
						get_query_filters: {
							docstatus: 1,
							status: ["not in", ["Closed", "On Hold", "Completed"]],
							per_received: ["<", 100],
							company: frm.doc.company,
						},
					}),
				__("Get Items From")
			);
		}
	},
});
