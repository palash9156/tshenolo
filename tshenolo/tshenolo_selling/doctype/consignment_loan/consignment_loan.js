frappe.ui.form.on("Consignment Loan", {
	setup(frm) {
		frm.set_query("item_code", () => ({ filters: { is_stock_item: 1 } }));
		frm.set_query("serial_no", () => ({
			filters: { item_code: frm.doc.item_code, warehouse: frm.doc.source_warehouse },
		}));
		frm.set_query("source_warehouse", () => ({
			filters: { company: frm.doc.company, is_group: 0 },
		}));
		frm.set_query("delivery_note", () => ({
			filters: { customer: frm.doc.customer, docstatus: 1 },
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === "On Loan") {
			frm.add_custom_button(__("Mark Returned"), () => {
				frappe.prompt(
					{
						fieldname: "return_date",
						fieldtype: "Date",
						label: __("Return Date"),
						default: frappe.datetime.get_today(),
						reqd: 1,
					},
					(values) =>
						frm.call("mark_returned", { return_date: values.return_date }).then(() => frm.reload_doc()),
					__("Return Equipment"),
					__("Return")
				);
			});
		}
	},
});
