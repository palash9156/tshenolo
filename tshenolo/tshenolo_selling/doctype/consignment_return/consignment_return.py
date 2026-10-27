import frappe
from frappe import _
from frappe.model.document import Document

from tshenolo.tshenolo_selling.consignment import validate_against_consignment_note
from tshenolo.utils import cancel_if_submitted, make_transfer_entry


class ConsignmentReturn(Document):
	def validate(self):
		note = validate_against_consignment_note(self)
		if not self.target_warehouse:
			self.target_warehouse = note.source_warehouse
		if frappe.db.get_value("Warehouse", self.target_warehouse, "company") != self.company:
			frappe.throw(_("Return To Warehouse {0} does not belong to {1}").format(self.target_warehouse, self.company))

	def on_submit(self):
		stock_entry = make_transfer_entry(
			self.company,
			self.posting_date,
			self.items,
			self.consignment_warehouse,
			self.target_warehouse,
			_("Consignment Return {0} against {1}").format(self.name, self.consignment_note),
		)
		self.db_set("stock_entry", stock_entry)
		frappe.get_doc("Consignment Note", self.consignment_note).update_consumed_qty()

	def on_cancel(self):
		cancel_if_submitted("Stock Entry", self.stock_entry)
		frappe.get_doc("Consignment Note", self.consignment_note).update_consumed_qty()
