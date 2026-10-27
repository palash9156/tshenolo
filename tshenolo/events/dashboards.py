from frappe import _


def add_transactions(data, label, items, fieldname, link_fieldname=None):
	"""Append a group of linked doctypes to a dashboard, keeping any existing configuration."""
	data.setdefault("fieldname", fieldname)
	data.setdefault("transactions", [])
	link_fieldname = link_fieldname or fieldname
	if data["fieldname"] != link_fieldname:
		data.setdefault("non_standard_fieldnames", {})
		for doctype in items:
			data["non_standard_fieldnames"][doctype] = link_fieldname

	for group in data["transactions"]:
		if group.get("label") == label:
			group["items"].extend(d for d in items if d not in group["items"])
			break
	else:
		data["transactions"].append({"label": label, "items": list(items)})
	return data


def purchase_order(data):
	return add_transactions(data, _("Shipping"), ["Advance Shipping Notice"], "purchase_order")


def material_request(data):
	return add_transactions(data, _("Consignment"), ["Consignment Note"], "material_request")


def customer(data):
	return add_transactions(
		data,
		_("Consignment"),
		["Consignment Note", "Consignment Utilisation", "Consignment Return", "Consignment Loan"],
		"customer",
	)


def issue(data):
	return add_transactions(data, _("Service"), ["Sales Order"], "issue")


def contract(data):
	return add_transactions(data, _("Service Billing"), ["Sales Order", "Sales Invoice"], "contract")
