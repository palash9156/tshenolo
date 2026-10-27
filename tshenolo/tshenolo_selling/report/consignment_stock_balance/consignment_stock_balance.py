import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Customer / Hospital"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
		{"label": _("Consignment Note"), "fieldname": "consignment_note", "fieldtype": "Link", "options": "Consignment Note", "width": 160},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
		{"label": _("Batch No"), "fieldname": "batch_no", "fieldtype": "Link", "options": "Batch", "width": 110},
		{"label": _("Serial Nos"), "fieldname": "serial_no", "fieldtype": "Data", "width": 140},
		{"label": _("Issued Qty"), "fieldname": "issued_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Utilised Qty"), "fieldname": "utilised_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Returned Qty"), "fieldname": "returned_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Balance Qty"), "fieldname": "balance_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Consignment Warehouse"), "fieldname": "consignment_warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 180},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
	]


def get_data(filters):
	conditions = ["cn.docstatus = 1"]
	for field in ("company", "customer"):
		if filters.get(field):
			conditions.append(f"cn.{field} = %({field})s")
	if filters.get("consignment_note"):
		conditions.append("cn.name = %(consignment_note)s")
	if filters.get("item_code"):
		conditions.append("cni.item_code = %(item_code)s")

	rows = frappe.db.sql(
		f"""
		select cn.customer, cn.name as consignment_note, cn.posting_date, cn.consignment_warehouse, cn.status,
			cni.item_code, cni.item_name, cni.batch_no, cni.serial_no,
			cni.qty as issued_qty, cni.utilised_qty, cni.returned_qty
		from `tabConsignment Note` cn
		inner join `tabConsignment Note Item` cni on cni.parent = cn.name
		where {" and ".join(conditions)}
		order by cn.customer, cn.posting_date, cn.name, cni.idx
		""",
		filters,
		as_dict=True,
	)

	data = []
	for r in rows:
		r.balance_qty = flt(r.issued_qty) - flt(r.utilised_qty) - flt(r.returned_qty)
		if filters.get("only_open") and r.balance_qty <= 0:
			continue
		data.append(r)
	return data
