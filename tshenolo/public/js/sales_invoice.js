frappe.ui.form.on("Sales Invoice", {
	setup(frm) {
		frm.set_query("contract", () => ({
			filters: { party_type: "Customer", party_name: frm.doc.customer, docstatus: ["<", 2] },
		}));
	},
});
