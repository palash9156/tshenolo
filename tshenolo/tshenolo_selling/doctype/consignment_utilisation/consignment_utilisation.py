import frappe
from frappe import _
from frappe.model.document import Document

from tshenolo.tshenolo_selling.consignment import validate_against_consignment_note


class ConsignmentUtilisation(Document):
	def validate(self):
		validate_against_consignment_note(self)

	def on_submit(self):
		frappe.get_doc("Consignment Note", self.consignment_note).update_consumed_qty()

	def on_cancel(self):
		frappe.get_doc("Consignment Note", self.consignment_note).update_consumed_qty()


@frappe.whitelist()
def make_sales_invoice(source_name):
	utilisation = frappe.get_doc("Consignment Utilisation", source_name)
	utilisation.check_permission("read")
	if utilisation.docstatus != 1:
		frappe.throw(_("Consignment Utilisation {0} must be submitted").format(source_name))
	if utilisation.sales_invoice and frappe.db.get_value("Sales Invoice", utilisation.sales_invoice, "docstatus") != 2:
		frappe.throw(_("Consignment Utilisation {0} is already invoiced in {1}").format(source_name, utilisation.sales_invoice))

	si = frappe.new_doc("Sales Invoice")
	si.customer = utilisation.customer
	si.company = utilisation.company
	si.update_stock = 1
	si.set_warehouse = utilisation.consignment_warehouse
	si.consignment_utilisation = utilisation.name

	for row in utilisation.items:
		si.append(
			"items",
			{
				"item_code": row.item_code,
				"qty": row.qty,
				"uom": row.uom,
				"stock_uom": row.uom,
				"conversion_factor": 1,
				"warehouse": utilisation.consignment_warehouse,
				"use_serial_batch_fields": 1 if (row.serial_no or row.batch_no) else 0,
				"serial_no": row.serial_no,
				"batch_no": row.batch_no,
			},
		)

	si.run_method("set_missing_values")
	si.run_method("calculate_taxes_and_totals")
	return si
