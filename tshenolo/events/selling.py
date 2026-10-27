import frappe
from frappe import _
from frappe.utils import flt


def get_row_batches(row):
	batch_no, bundle = row.get("batch_no"), row.get("serial_and_batch_bundle")
	if not (batch_no or bundle) and row.docstatus == 1:
		# bundles created during submit are written to the database, not to the in-memory row
		batch_no, bundle = frappe.db.get_value(row.doctype, row.name, ["batch_no", "serial_and_batch_bundle"])
	if batch_no:
		return [batch_no]
	if bundle:
		return frappe.get_all(
			"Serial and Batch Entry",
			filters={"parent": bundle, "batch_no": ("is", "set")},
			pluck="batch_no",
			distinct=True,
		)
	return []


def set_supplier_lot_no(doc, method=None):
	for row in doc.items:
		batches = get_row_batches(row)
		lots = []
		if batches:
			lots = frappe.get_all(
				"Batch",
				filters={"name": ("in", batches), "supplier_lot_no": ("is", "set")},
				pluck="supplier_lot_no",
				distinct=True,
			)
		value = ", ".join(sorted(lots)) or None
		if value == row.get("supplier_lot_no"):
			continue
		if doc.docstatus == 1:
			row.db_set("supplier_lot_no", value, update_modified=False)
		else:
			row.supplier_lot_no = value


def copy_supplier_lot_to_batch(doc, method=None):
	for row in doc.items:
		if not row.get("supplier_lot_no"):
			continue
		for batch in get_row_batches(row):
			if not frappe.db.get_value("Batch", batch, "supplier_lot_no"):
				frappe.db.set_value("Batch", batch, "supplier_lot_no", row.supplier_lot_no)


def get_back_order_status(item, available_qty):
	pending = flt(item.qty) - flt(item.delivered_qty)
	if pending <= 0:
		return 0, "Delivered"
	back_order_qty = max(pending - flt(available_qty), 0) if item.get("is_stock_item") else 0
	if back_order_qty > 0:
		return back_order_qty, "Back Order"
	if flt(item.delivered_qty) > 0:
		return 0, "Partially Delivered"
	return 0, "Pending"


def get_available_qty(item_code, warehouse):
	if not warehouse:
		return 0
	return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"))


def set_back_order_status(doc, method=None):
	for item in doc.items:
		item.back_order_qty, item.line_status = get_back_order_status(
			item, get_available_qty(item.item_code, item.warehouse)
		)


def update_sales_order_back_orders(doc, method=None):
	if doc.doctype == "Sales Invoice" and not doc.update_stock:
		return

	so_field = "against_sales_order" if doc.doctype == "Delivery Note" else "sales_order"
	so_details = {d.so_detail for d in doc.items if d.get(so_field) and d.get("so_detail")}
	for so_detail in so_details:
		item = frappe.db.get_value(
			"Sales Order Item",
			so_detail,
			["name", "item_code", "warehouse", "qty", "delivered_qty", "is_stock_item"],
			as_dict=True,
		)
		if not item:
			continue
		back_order_qty, line_status = get_back_order_status(
			item, get_available_qty(item.item_code, item.warehouse)
		)
		frappe.db.set_value(
			"Sales Order Item",
			so_detail,
			{"back_order_qty": back_order_qty, "line_status": line_status},
			update_modified=False,
		)


def validate_consignment_utilisation(doc, method=None):
	if not doc.get("consignment_utilisation") or doc.is_return:
		return
	if not doc.update_stock:
		frappe.throw(_("Invoices raised against a Consignment Utilisation must have 'Update Stock' enabled"))

	existing = frappe.db.get_value(
		"Sales Invoice",
		{
			"consignment_utilisation": doc.consignment_utilisation,
			"docstatus": ("<", 2),
			"is_return": 0,
			"name": ("!=", doc.name),
		},
	)
	if existing:
		frappe.throw(
			_("Consignment Utilisation {0} is already invoiced in {1}").format(doc.consignment_utilisation, existing)
		)


def link_consignment_utilisation(doc, method=None):
	if not doc.get("consignment_utilisation") or doc.is_return:
		return
	value = doc.name if doc.docstatus == 1 else None
	frappe.db.set_value("Consignment Utilisation", doc.consignment_utilisation, "sales_invoice", value)
