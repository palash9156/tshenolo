frappe.query_reports["Consignment Stock Balance"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{ fieldname: "customer", label: __("Customer / Hospital"), fieldtype: "Link", options: "Customer" },
		{ fieldname: "consignment_note", label: __("Consignment Note"), fieldtype: "Link", options: "Consignment Note" },
		{ fieldname: "item_code", label: __("Item"), fieldtype: "Link", options: "Item" },
		{ fieldname: "only_open", label: __("Only Open Balances"), fieldtype: "Check", default: 1 },
	],
};
