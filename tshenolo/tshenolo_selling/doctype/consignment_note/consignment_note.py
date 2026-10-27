import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

from tshenolo.utils import cancel_if_submitted, get_consignment_warehouse, make_transfer_entry


class ConsignmentNote(Document):
	def validate(self):
		if frappe.db.get_value("Warehouse", self.source_warehouse, "company") != self.company:
			frappe.throw(_("Source Warehouse {0} does not belong to {1}").format(self.source_warehouse, self.company))

		for row in self.items:
			if flt(row.qty) <= 0:
				frappe.throw(_("Row #{0}: Issued Qty must be greater than zero").format(row.idx))
			if not frappe.get_cached_value("Item", row.item_code, "is_stock_item"):
				frappe.throw(_("Row #{0}: {1} is not a stock item").format(row.idx, row.item_code))
		self.total_qty = sum(flt(d.qty) for d in self.items)
		self.status = "Draft"

	def on_submit(self):
		self.consignment_warehouse = get_consignment_warehouse(self.customer, self.company, "Consignment")
		stock_entry = make_transfer_entry(
			self.company,
			self.posting_date,
			self.items,
			self.source_warehouse,
			self.consignment_warehouse,
			_("Consignment Note {0} for {1}").format(self.name, self.customer),
		)
		self.db_set({"consignment_warehouse": self.consignment_warehouse, "stock_entry": stock_entry})
		self.update_status()

	def on_cancel(self):
		cancel_if_submitted("Stock Entry", self.stock_entry)
		self.db_set("status", "Cancelled")

	def update_consumed_qty(self):
		for doctype, field in (("Consignment Utilisation", "utilised_qty"), ("Consignment Return", "returned_qty")):
			totals = dict(
				frappe.db.sql(
					f"""
					select cti.consignment_note_item, sum(cti.qty)
					from `tabConsignment Transaction Item` cti
					inner join `tab{doctype}` parent on parent.name = cti.parent
					where cti.parenttype = %s and parent.docstatus = 1 and parent.consignment_note = %s
					group by cti.consignment_note_item
					""",
					(doctype, self.name),
				)
			)
			for row in self.items:
				qty = flt(totals.get(row.name))
				if flt(row.get(field)) != qty:
					row.db_set(field, qty, update_modified=False)
		self.update_status()

	def update_status(self):
		if self.docstatus == 2:
			status = "Cancelled"
		else:
			issued = sum(flt(d.qty) for d in self.items)
			utilised = sum(flt(d.utilised_qty) for d in self.items)
			returned = sum(flt(d.returned_qty) for d in self.items)
			if utilised + returned >= issued:
				status = "Fully Utilised" if not returned else "Closed"
			elif utilised or returned:
				status = "Partially Utilised"
			else:
				status = "Issued"
		self.db_set("status", status)


@frappe.whitelist()
def make_consignment_note(source_name, target_doc=None):
	def set_header(source, target):
		target.customer = source.consignment_customer
		target.sales_person = source.sales_person
		target.material_request = source.name
		target.source_warehouse = source.salesperson_warehouse or source.set_warehouse

	def update_item(source, target, source_parent):
		target.qty = flt(source.stock_qty)
		target.uom = source.stock_uom
		target.material_request_item = source.name

	return get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Consignment Note",
				"validation": {"docstatus": ["=", 1], "is_consignment": ["=", 1]},
				"field_no_map": ["customer", "naming_series", "status"],
			},
			"Material Request Item": {
				"doctype": "Consignment Note Item",
				"field_no_map": ["warehouse"],
				"postprocess": update_item,
			},
		},
		target_doc,
		set_header,
	)


@frappe.whitelist()
def make_consignment_utilisation(source_name):
	return make_consignment_transaction(source_name, "Consignment Utilisation")


@frappe.whitelist()
def make_consignment_return(source_name):
	doc = make_consignment_transaction(source_name, "Consignment Return")
	doc.target_warehouse = frappe.db.get_value("Consignment Note", source_name, "source_warehouse")
	return doc


def make_consignment_transaction(source_name, doctype):
	from tshenolo.tshenolo_selling.consignment import get_pending_items

	pending = get_pending_items(source_name)
	if not pending["items"]:
		frappe.throw(_("Nothing is pending on Consignment Note {0}").format(source_name))

	doc = frappe.new_doc(doctype)
	doc.customer = pending["customer"]
	doc.company = pending["company"]
	doc.consignment_note = source_name
	doc.consignment_warehouse = frappe.db.get_value("Consignment Note", source_name, "consignment_warehouse")
	for row in pending["items"]:
		doc.append("items", row)
	return doc
