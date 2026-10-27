import frappe
from frappe import _
from frappe.utils import flt, getdate, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Purchase Order"), "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 160},
		{"label": _("Date"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
		{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 160},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
		{"label": _("Ordered Qty"), "fieldname": "ordered_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Received Qty"), "fieldname": "received_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Pending Qty"), "fieldname": "pending_qty", "fieldtype": "Float", "width": 100},
		{"label": _("In Transit (ASN) Qty"), "fieldname": "in_transit_qty", "fieldtype": "Float", "width": 120},
		{"label": _("Back Order Qty"), "fieldname": "back_order_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Expected Date"), "fieldname": "expected_date", "fieldtype": "Date", "width": 110},
		{"label": _("ETA"), "fieldname": "eta", "fieldtype": "Date", "width": 100},
		{"label": _("Overdue"), "fieldname": "overdue", "fieldtype": "Check", "width": 80},
		{"label": _("Follow-up Date"), "fieldname": "follow_up_date", "fieldtype": "Date", "width": 110},
		{"label": _("Follow-up Status"), "fieldname": "follow_up_status", "fieldtype": "Data", "width": 120},
		{"label": _("Supplier Response"), "fieldname": "supplier_response", "fieldtype": "Data", "width": 200},
		{"label": _("Buyer"), "fieldname": "buyer", "fieldtype": "Link", "options": "User", "width": 140},
	]


def get_data(filters):
	conditions = ["po.docstatus = 1", "po.status not in ('Closed', 'Completed')", "poi.qty > poi.received_qty"]
	for field in ("company", "supplier"):
		if filters.get(field):
			conditions.append(f"po.{field} = %({field})s")
	if filters.get("purchase_order"):
		conditions.append("po.name = %(purchase_order)s")
	if filters.get("item_code"):
		conditions.append("poi.item_code = %(item_code)s")
	if filters.get("from_date"):
		conditions.append("po.transaction_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("po.transaction_date <= %(to_date)s")

	rows = frappe.db.sql(
		f"""
		select po.name as purchase_order, po.transaction_date, po.supplier, po.owner,
			poi.name as po_item, poi.item_code, poi.item_name, poi.qty as ordered_qty, poi.received_qty,
			coalesce(poi.expected_delivery_date, poi.schedule_date) as expected_date
		from `tabPurchase Order` po
		inner join `tabPurchase Order Item` poi on poi.parent = po.name
		where {" and ".join(conditions)}
		order by po.transaction_date, po.name, poi.idx
		""",
		filters,
		as_dict=True,
	)
	if not rows:
		return []

	po_items = [r.po_item for r in rows]
	in_transit = get_in_transit(po_items)
	follow_ups = get_latest_follow_ups(po_items)

	data = []
	for r in rows:
		transit = in_transit.get(r.po_item, {})
		follow_up = follow_ups.get(r.po_item, {})
		r.pending_qty = flt(r.ordered_qty) - flt(r.received_qty)
		r.in_transit_qty = flt(transit.get("qty"))
		r.back_order_qty = max(r.pending_qty - r.in_transit_qty, 0)
		r.eta = follow_up.get("eta") or transit.get("eta") or r.expected_date
		r.overdue = 1 if r.eta and getdate(r.eta) < getdate(today()) else 0
		r.follow_up_date = follow_up.get("follow_up_date")
		r.follow_up_status = follow_up.get("status")
		r.supplier_response = follow_up.get("supplier_response")
		r.buyer = follow_up.get("buyer") or r.owner
		if filters.get("only_overdue") and not r.overdue:
			continue
		data.append(r)
	return data


def get_in_transit(po_items):
	rows = frappe.db.sql(
		"""
		select ai.purchase_order_item, sum(greatest(ai.qty - ai.received_qty, 0)) as qty, max(asn.eta) as eta
		from `tabASN Item` ai
		inner join `tabAdvance Shipping Notice` asn on asn.name = ai.parent
		where asn.docstatus = 1 and ai.purchase_order_item in %(items)s
		group by ai.purchase_order_item
		""",
		{"items": po_items},
		as_dict=True,
	)
	return {r.purchase_order_item: r for r in rows}


def get_latest_follow_ups(po_items):
	rows = frappe.get_all(
		"Supplier Follow Up",
		filters={"parenttype": "Purchase Order", "purchase_order_item": ("in", po_items)},
		fields=["purchase_order_item", "eta", "follow_up_date", "status", "supplier_response", "buyer"],
		order_by="follow_up_date asc, idx asc",
	)
	return {r.purchase_order_item: r for r in rows}
