frappe.ui.form.on("Purchase Order", {
	setup(frm) {
		frm.set_query("item_code", "supplier_follow_ups", () => ({
			filters: { name: ["in", (frm.doc.items || []).map((d) => d.item_code)] },
		}));
	},

	refresh(frm) {
		if (
			frm.doc.docstatus === 1 &&
			flt(frm.doc.per_received) < 100 &&
			!["Closed", "On Hold", "Completed"].includes(frm.doc.status)
		) {
			frm.add_custom_button(
				__("Advance Shipping Notice"),
				() =>
					frappe.model.open_mapped_doc({
						method: "tshenolo.tshenolo_buying.doctype.advance_shipping_notice.advance_shipping_notice.make_advance_shipping_notice",
						frm,
					}),
				__("Create")
			);
		}
	},
});

frappe.ui.form.on("Purchase Order Item", {
	is_sample(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.is_sample) {
			frappe.model.set_value(cdt, cdn, {
				price_list_rate: 0,
				discount_percentage: 0,
				margin_rate_or_amount: 0,
				rate: 0,
			});
		}
	},
});
