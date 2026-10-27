import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from tshenolo.events.selling import get_back_order_status


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 160},
		{"label": _("Date"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
		{"label": _("Customer PO"), "fieldname": "po_no", "fieldtype": "Data", "width": 120},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 140},
		{"label": _("Ordered Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
		{"label": _("Delivered Qty"), "fieldname": "delivered_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Pending Qty"), "fieldname": "pending_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Available Qty"), "fieldname": "available_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Back Order Qty"), "fieldname": "back_order_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Line Status"), "fieldname": "line_status", "fieldtype": "Data", "width": 130},
		{"label": _("Delivery Date"), "fieldname": "delivery_date", "fieldtype": "Date", "width": 110},
		{"label": _("ETA"), "fieldname": "eta", "fieldtype": "Date", "width": 100},
		{"label": _("Overdue"), "fieldname": "overdue", "fieldtype": "Check", "width": 80},
	]


def get_data(filters):
	conditions = [
		"so.docstatus = 1",
		"so.status not in ('Closed', 'Completed', 'On Hold')",
		"soi.qty > soi.delivered_qty",
		"soi.delivered_by_supplier = 0",
	]
	if filters.get("company"):
		conditions.append("so.company = %(company)s")
	if filters.get("customer"):
		conditions.append("so.customer = %(customer)s")
	if filters.get("sales_order"):
		conditions.append("so.name = %(sales_order)s")
	if filters.get("item_code"):
		conditions.append("soi.item_code = %(item_code)s")
	if filters.get("from_date"):
		conditions.append("so.transaction_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("so.transaction_date <= %(to_date)s")

	rows = frappe.db.sql(
		f"""
		select so.name as sales_order, so.transaction_date, so.customer, so.po_no,
			soi.item_code, soi.item_name, soi.warehouse, soi.qty, soi.delivered_qty, soi.is_stock_item,
			soi.delivery_date, soi.eta, bin.actual_qty as available_qty
		from `tabSales Order` so
		inner join `tabSales Order Item` soi on soi.parent = so.name
		left join `tabBin` bin on bin.item_code = soi.item_code and bin.warehouse = soi.warehouse
		where {" and ".join(conditions)}
		order by so.transaction_date, so.name, soi.idx
		""",
		filters,
		as_dict=True,
	)

	data = []
	current = getdate(today())
	for r in rows:
		r.available_qty = flt(r.available_qty)
		r.pending_qty = flt(r.qty) - flt(r.delivered_qty)
		r.back_order_qty, r.line_status = get_back_order_status(r, r.available_qty)
		expected = r.eta or r.delivery_date
		r.overdue = 1 if expected and getdate(expected) < current else 0
		if filters.get("only_back_orders") and not r.back_order_qty:
			continue
		data.append(r)
	return data
