window.tshenolo_consignment = {
	setup_note_query(frm) {
		frm.set_query("consignment_note", () => ({
			filters: {
				docstatus: 1,
				status: ["in", ["Issued", "Partially Utilised"]],
				...(frm.doc.customer ? { customer: frm.doc.customer } : {}),
			},
		}));
	},

	load_pending_items(frm, on_load) {
		frm.clear_table("items");
		if (!frm.doc.consignment_note) {
			frm.refresh_field("items");
			return;
		}
		frappe.call({
			method: "tshenolo.tshenolo_selling.consignment.get_pending_items",
			args: { consignment_note: frm.doc.consignment_note },
			callback(r) {
				if (!r.message) return;
				frm.set_value("customer", r.message.customer);
				frm.set_value("company", r.message.company);
				r.message.items.forEach((row) => frm.add_child("items", row));
				frm.refresh_field("items");
				on_load && on_load(r.message);
			},
		});
	},
};
