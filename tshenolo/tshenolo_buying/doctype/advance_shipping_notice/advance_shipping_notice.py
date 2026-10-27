import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate


class AdvanceShippingNotice(Document):
	def validate(self):
		if self.eta and getdate(self.eta) < getdate(self.dispatch_date):
			frappe.throw(_("ETA cannot be before the Dispatch Date"))
		self.validate_items()
		self.total_qty = sum(flt(d.qty) for d in self.items)
		self.status = self.get_status()

	def validate_items(self):
		seen = set()
		for d in self.items:
			if d.purchase_order_item in seen:
				frappe.throw(_("Row #{0}: Purchase Order Item is listed more than once").format(d.idx))
			seen.add(d.purchase_order_item)

			po = frappe.db.get_value(
				"Purchase Order", d.purchase_order, ["supplier", "company", "docstatus", "status"], as_dict=True
			)
			if not po or po.docstatus != 1:
				frappe.throw(_("Row #{0}: Purchase Order {1} must be submitted").format(d.idx, d.purchase_order))
			if po.supplier != self.supplier or po.company != self.company:
				frappe.throw(
					_("Row #{0}: Purchase Order {1} belongs to a different supplier or company").format(
						d.idx, d.purchase_order
					)
				)
			if po.status in ("Closed", "On Hold"):
				frappe.throw(_("Row #{0}: Purchase Order {1} is {2}").format(d.idx, d.purchase_order, po.status))

			po_item = frappe.db.get_value(
				"Purchase Order Item",
				d.purchase_order_item,
				["parent", "item_code", "qty", "received_qty", "uom", "warehouse"],
				as_dict=True,
			)
			if not po_item or po_item.parent != d.purchase_order:
				frappe.throw(_("Row #{0}: Invalid Purchase Order Item reference").format(d.idx))

			d.item_code = po_item.item_code
			d.uom = po_item.uom
			d.warehouse = po_item.warehouse

			if flt(d.qty) <= 0:
				frappe.throw(_("Row #{0}: Shipped Qty must be greater than zero").format(d.idx))

			pending = (
				flt(po_item.qty) - flt(po_item.received_qty) - get_in_transit_qty(d.purchase_order_item, self.name)
			)
			if flt(d.qty) > flt(pending, d.precision("qty")):
				frappe.throw(
					_("Row #{0}: Shipped Qty {1} for {2} exceeds the quantity still pending on {3} ({4})").format(
						d.idx, d.qty, d.item_code, d.purchase_order, max(pending, 0)
					)
				)

	def get_status(self):
		if self.docstatus == 0:
			return "Draft"
		if self.docstatus == 2:
			return "Cancelled"
		total = sum(flt(d.qty) for d in self.items)
		received = sum(min(flt(d.received_qty), flt(d.qty)) for d in self.items)
		if received <= 0:
			return "In Transit"
		if received < total:
			return "Partially Received"
		return "Received"

	def on_submit(self):
		self.db_set("status", self.get_status())

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	def update_status(self):
		self.db_set("status", self.get_status())


def get_in_transit_qty(purchase_order_item, exclude_asn=None):
	"""Quantity shipped on other submitted ASNs that has not been received yet."""
	rows = frappe.db.sql(
		"""
		select ai.qty, ai.received_qty
		from `tabASN Item` ai
		inner join `tabAdvance Shipping Notice` asn on asn.name = ai.parent
		where ai.purchase_order_item = %s and asn.docstatus = 1 and asn.name != %s
		""",
		(purchase_order_item, exclude_asn or ""),
		as_dict=True,
	)
	return sum(max(flt(r.qty) - flt(r.received_qty), 0) for r in rows)


@frappe.whitelist()
def make_advance_shipping_notice(source_name, target_doc=None):
	def pending_qty(source):
		return flt(source.qty) - flt(source.received_qty) - get_in_transit_qty(source.name)

	def update_item(source, target, source_parent):
		target.qty = pending_qty(source)

	return get_mapped_doc(
		"Purchase Order",
		source_name,
		{
			"Purchase Order": {
				"doctype": "Advance Shipping Notice",
				"validation": {"docstatus": ["=", 1]},
			},
			"Purchase Order Item": {
				"doctype": "ASN Item",
				"field_map": {"name": "purchase_order_item", "parent": "purchase_order"},
				"postprocess": update_item,
				"condition": lambda d: pending_qty(d) > 0 and not d.delivered_by_supplier,
			},
		},
		target_doc,
	)


@frappe.whitelist()
def make_purchase_receipt(source_name, target_doc=None):
	from erpnext.buying.doctype.purchase_order.purchase_order import (
		make_purchase_receipt as make_receipt_from_po,
	)

	asn = frappe.get_doc("Advance Shipping Notice", source_name)
	asn.check_permission("read")
	if asn.docstatus != 1:
		frappe.throw(_("Advance Shipping Notice {0} must be submitted").format(asn.name))

	pending = {d.purchase_order_item: d for d in asn.items if flt(d.qty) > flt(d.received_qty)}
	if not pending:
		frappe.throw(_("All items on {0} have already been received").format(asn.name))

	purchase_orders = list(dict.fromkeys(d.purchase_order for d in pending.values()))
	receipt = None
	for po in purchase_orders:
		children = [name for name, d in pending.items() if d.purchase_order == po]
		receipt = make_receipt_from_po(po, target_doc=receipt, args={"filtered_children": children})

	for item in receipt.items:
		row = pending.get(item.purchase_order_item)
		if not row:
			continue
		qty = flt(row.qty) - flt(row.received_qty)
		item.qty = qty
		item.received_qty = qty
		item.stock_qty = qty * flt(item.conversion_factor or 1)
		item.asn = asn.name
		item.asn_detail = row.name

	receipt.asn = asn.name
	receipt.run_method("set_missing_values")
	receipt.run_method("calculate_taxes_and_totals")
	return receipt
