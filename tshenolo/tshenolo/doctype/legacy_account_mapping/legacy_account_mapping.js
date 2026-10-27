frappe.ui.form.on("Legacy Account Mapping", {
	setup(frm) {
		frm.set_query("new_account", () => ({
			filters: { company: frm.doc.company, is_group: 0 },
		}));
	},
});
