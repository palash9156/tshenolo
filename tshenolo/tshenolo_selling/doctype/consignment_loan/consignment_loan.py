import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate

from tshenolo.utils import cancel_if_submitted, get_consignment_warehouse, make_transfer_entry


class ConsignmentLoan(Document):
	def validate(self):
		self.loan_value = 0
		item = frappe.get_cached_value("Item", self.item_code, ["is_stock_item", "has_serial_no"], as_dict=True)
		if not item.is_stock_item:
			frappe.throw(_("{0} is not a stock item").format(self.item_code))
		if item.has_serial_no:
			if not self.serial_no:
				frappe.throw(_("Serial No is mandatory for serialised equipment {0}").format(self.item_code))
			if frappe.db.get_value("Serial No", self.serial_no, "item_code") != self.item_code:
				frappe.throw(_("Serial No {0} does not belong to {1}").format(self.serial_no, self.item_code))
			self.qty = 1
		elif self.serial_no:
			frappe.throw(_("{0} is not a serialised item").format(self.item_code))
		if flt(self.qty) <= 0:
			frappe.throw(_("Qty must be greater than zero"))

		if self.expected_return_date and getdate(self.expected_return_date) < getdate(self.loan_date):
			frappe.throw(_("Expected Return Date cannot be before the Loan Date"))

		if self.delivery_note:
			dn = frappe.db.get_value("Delivery Note", self.delivery_note, ["customer", "docstatus"], as_dict=True)
			if dn.docstatus != 1 or dn.customer != self.customer:
				frappe.throw(
					_("Delivery Note {0} must be submitted and belong to {1}").format(self.delivery_note, self.customer)
				)

		if self.docstatus == 0:
			self.status = "Draft"

	def on_submit(self):
		self.loan_warehouse = get_consignment_warehouse(self.customer, self.company, "Loan")
		stock_entry = make_transfer_entry(
			self.company,
			self.loan_date,
			[self._stock_row()],
			self.source_warehouse,
			self.loan_warehouse,
			_("Consignment Loan {0} to {1}").format(self.name, self.customer),
		)
		self.db_set({"loan_warehouse": self.loan_warehouse, "stock_entry": stock_entry, "status": "On Loan"})

	def on_cancel(self):
		cancel_if_submitted("Stock Entry", self.return_stock_entry)
		cancel_if_submitted("Stock Entry", self.stock_entry)
		self.db_set("status", "Cancelled")

	def _stock_row(self):
		return frappe._dict(item_code=self.item_code, qty=self.qty, serial_no=self.serial_no)

	@frappe.whitelist()
	def mark_returned(self, return_date=None):
		self.check_permission("submit")
		if self.docstatus != 1 or self.status != "On Loan":
			frappe.throw(_("Only submitted loans that are On Loan can be returned"))

		return_date = return_date or nowdate()
		if getdate(return_date) < getdate(self.loan_date):
			frappe.throw(_("Return Date cannot be before the Loan Date"))

		stock_entry = make_transfer_entry(
			self.company,
			return_date,
			[self._stock_row()],
			self.loan_warehouse,
			self.source_warehouse,
			_("Return of Consignment Loan {0} from {1}").format(self.name, self.customer),
		)
		self.db_set({"return_stock_entry": stock_entry, "return_date": return_date, "status": "Returned"})
