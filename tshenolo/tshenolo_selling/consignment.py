import frappe
from frappe import _
from frappe.utils import flt


def get_note_item_balance(row):
	return flt(row.qty) - flt(row.utilised_qty) - flt(row.returned_qty)


def validate_against_consignment_note(doc):
	"""Shared validation for Consignment Utilisation and Consignment Return."""
	note = frappe.get_doc("Consignment Note", doc.consignment_note)
	if note.docstatus != 1:
		frappe.throw(_("Consignment Note {0} must be submitted").format(note.name))
	if note.customer != doc.customer:
		frappe.throw(_("Consignment Note {0} belongs to customer {1}").format(note.name, note.customer))

	doc.company = note.company
	doc.consignment_warehouse = note.consignment_warehouse

	note_items = {d.name: d for d in note.items}
	requested = {}
	for row in doc.items:
		note_item = note_items.get(row.consignment_note_item)
		if not note_item:
			frappe.throw(_("Row #{0}: Item is not on Consignment Note {1}").format(row.idx, note.name))
		row.item_code = note_item.item_code
		row.uom = note_item.uom
		if not row.batch_no and note_item.batch_no:
			row.batch_no = note_item.batch_no
		if flt(row.qty) <= 0:
			frappe.throw(_("Row #{0}: Qty must be greater than zero").format(row.idx))
		requested[row.consignment_note_item] = requested.get(row.consignment_note_item, 0) + flt(row.qty)

	for name, qty in requested.items():
		balance = get_note_item_balance(note_items[name])
		if qty > flt(balance, 6):
			frappe.throw(
				_("Qty {0} for {1} exceeds the balance {2} remaining on Consignment Note {3}").format(
					qty, note_items[name].item_code, balance, note.name
				)
			)

	doc.total_qty = sum(flt(d.qty) for d in doc.items)
	return note


@frappe.whitelist()
def get_pending_items(consignment_note):
	note = frappe.get_doc("Consignment Note", consignment_note)
	note.check_permission("read")
	return {
		"customer": note.customer,
		"company": note.company,
		"source_warehouse": note.source_warehouse,
		"items": [
			{
				"consignment_note_item": d.name,
				"item_code": d.item_code,
				"item_name": d.item_name,
				"qty": get_note_item_balance(d),
				"uom": d.uom,
				"serial_no": d.serial_no,
				"batch_no": d.batch_no,
			}
			for d in note.items
			if get_note_item_balance(d) > 0
		],
	}
