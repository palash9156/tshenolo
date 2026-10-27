import frappe
from frappe import _
from frappe.utils import flt, nowdate
from frappe.utils.user import get_users_with_role


def get_settings():
	return frappe.get_cached_doc("Tshenolo Settings")


def get_role_users(role):
	if not role:
		return []
	return [u for u in get_users_with_role(role) if u not in ("Administrator", "Guest")]


def notify_users(users, reference_doctype, reference_name, description, subject=None, date=None):
	"""Create one ToDo per user and email the users that did not already have it.

	The description doubles as the de-duplication key, so callers must include anything
	that makes an alert unique (e.g. the due date) in it.
	"""
	notified = []
	for user in set(users or []):
		if frappe.db.exists(
			"ToDo",
			{
				"allocated_to": user,
				"reference_type": reference_doctype,
				"reference_name": reference_name,
				"description": description,
			},
		):
			continue
		frappe.get_doc(
			{
				"doctype": "ToDo",
				"allocated_to": user,
				"reference_type": reference_doctype,
				"reference_name": reference_name,
				"description": description,
				"date": date,
				"priority": "Medium",
			}
		).insert(ignore_permissions=True)
		notified.append(user)

	if notified:
		recipients = [
			email for email in frappe.get_all("User", {"name": ("in", notified)}, pluck="email") if email
		]
		if recipients:
			frappe.sendmail(
				recipients=recipients,
				subject=subject or description,
				message=description,
				reference_doctype=reference_doctype,
				reference_name=reference_name,
			)
	return notified


def get_root_warehouse(company):
	return frappe.db.get_value(
		"Warehouse",
		{"company": company, "is_group": 1, "parent_warehouse": ("in", ("", None))},
		"name",
	)


def get_consignment_parent_warehouse(company):
	parent = get_settings().consignment_parent_warehouse
	if parent and frappe.db.get_value("Warehouse", parent, "company") == company:
		return parent

	abbr = frappe.get_cached_value("Company", company, "abbr")
	name = f"{_('Consignment Warehouses')} - {abbr}"
	if not frappe.db.exists("Warehouse", name):
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": _("Consignment Warehouses"),
				"company": company,
				"is_group": 1,
				"parent_warehouse": get_root_warehouse(company),
			}
		).insert(ignore_permissions=True)
	return name


def get_consignment_warehouse(customer, company, warehouse_type="Consignment"):
	"""Return (creating if needed) the hospital-specific consignment or loan warehouse."""
	filters = {
		"consignment_customer": customer,
		"consignment_type": warehouse_type,
		"company": company,
		"is_group": 0,
	}
	if name := frappe.db.get_value("Warehouse", filters, "name"):
		return name

	customer_name = frappe.db.get_value("Customer", customer, "customer_name") or customer
	warehouse = frappe.get_doc(
		{
			"doctype": "Warehouse",
			"warehouse_name": f"{customer_name} {warehouse_type}",
			"company": company,
			"parent_warehouse": get_consignment_parent_warehouse(company),
			"consignment_customer": customer,
			"consignment_type": warehouse_type,
		}
	).insert(ignore_permissions=True)
	return warehouse.name


def make_transfer_entry(company, posting_date, items, source_warehouse, target_warehouse, remarks):
	"""Submit a Material Transfer Stock Entry. `items` rows need item_code and qty (stock UOM)."""
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Transfer"
	se.purpose = "Material Transfer"
	se.company = company
	se.posting_date = posting_date or nowdate()
	se.set_posting_time = 1
	se.from_warehouse = source_warehouse
	se.to_warehouse = target_warehouse
	se.remarks = remarks

	for row in items:
		stock_uom = frappe.get_cached_value("Item", row.item_code, "stock_uom")
		se.append(
			"items",
			{
				"item_code": row.item_code,
				"qty": flt(row.qty),
				"transfer_qty": flt(row.qty),
				"uom": stock_uom,
				"stock_uom": stock_uom,
				"conversion_factor": 1,
				"s_warehouse": source_warehouse,
				"t_warehouse": target_warehouse,
				"use_serial_batch_fields": 1 if (row.get("serial_no") or row.get("batch_no")) else 0,
				"serial_no": row.get("serial_no"),
				"batch_no": row.get("batch_no"),
			},
		)

	se.flags.ignore_permissions = True
	se.insert()
	se.submit()
	return se.name


def cancel_if_submitted(doctype, name):
	if name and frappe.db.get_value(doctype, name, "docstatus") == 1:
		doc = frappe.get_doc(doctype, name)
		doc.flags.ignore_permissions = True
		doc.cancel()
