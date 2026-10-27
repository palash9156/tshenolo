frappe.ui.form.on("Consignment Return", {
	setup(frm) {
		tshenolo_consignment.setup_note_query(frm);
		frm.set_query("target_warehouse", () => ({
			filters: { company: frm.doc.company, is_group: 0 },
		}));
	},

	consignment_note(frm) {
		tshenolo_consignment.load_pending_items(frm, (data) => {
			if (!frm.doc.target_warehouse) {
				frm.set_value("target_warehouse", data.source_warehouse);
			}
		});
	},
});
