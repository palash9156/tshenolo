frappe.query_reports["Consignment Loan Register"] = {
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
		{ fieldname: "item_code", label: __("Equipment"), fieldtype: "Link", options: "Item" },
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nOn Loan\nReturned",
			default: "On Loan",
		},
	],
};
