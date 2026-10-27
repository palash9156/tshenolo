frappe.ui.form.on("Sales Order", {
	setup(frm) {
		frm.set_query("contract", () => ({
			filters: { party_type: "Customer", party_name: frm.doc.customer, docstatus: ["<", 2] },
		}));
	},
});
