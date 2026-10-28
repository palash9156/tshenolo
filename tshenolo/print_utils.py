"""Jinja helpers for the supplier-facing print formats and emails.

Registered via the `jinja` hook, so they are globals in every template; the `tshenolo_` prefix keeps them
from colliding with other apps. Docs may arrive as Documents (print, Notification) or plain dicts, so only
`.get()` access is used.
"""

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_company_address
from frappe.utils import flt

from tshenolo.utils import get_settings


def tshenolo_settings():
	return get_settings()


def tshenolo_company(company):
	details = frappe.db.get_value(
		"Company", company, ["company_name", "tax_id", "sahpra_license_no", "email", "phone_no"], as_dict=True
	) or frappe._dict()
	details.address_display = get_company_address(company).get("company_address_display")
	return details


def tshenolo_po_numbers(doc):
	"""Distinct Purchase Orders a Purchase Receipt was made against, in row order."""
	orders = (row.get("purchase_order") for row in doc.get("items") or [])
	return ", ".join(dict.fromkeys(po for po in orders if po))


def tshenolo_grn_rows(doc):
	"""Purchase Receipt lines with the ordered qty from the PO and a supplier-facing status."""
	po_qty = {}
	po_items = [row.get("purchase_order_item") for row in doc.get("items") or []]
	if po_items := [name for name in po_items if name]:
		po_qty = dict(
			frappe.get_all(
				"Purchase Order Item", filters={"name": ("in", po_items)}, fields=["name", "qty"], as_list=True
			)
		)

	rows = []
	for row in doc.get("items") or []:
		received = flt(row.get("received_qty"))
		rejected = flt(row.get("rejected_qty"))
		ordered = po_qty.get(row.get("purchase_order_item"))
		if rejected:
			status = row.get("rejection_reason") or _("Rejected")
		elif ordered is not None and received < flt(ordered):
			status = _("Accepted – Short Delivery")
		else:
			status = _("Accepted in Full")

		rows.append(
			frappe._dict(
				item_code=row.get("item_code"),
				nappi_code=row.get("nappi_code"),
				item_name=row.get("item_name"),
				uom=row.get("uom"),
				ordered_qty=ordered,
				received_qty=received,
				accepted_qty=flt(row.get("qty")),
				rejected_qty=rejected,
				status=status,
			)
		)
	return rows


def tshenolo_remittance_rows(doc):
	"""Payment Entry allocations, with debit notes (returns) labelled as credit notes and shown negative."""
	invoices = [
		row.get("reference_name")
		for row in doc.get("references") or []
		if row.get("reference_doctype") == "Purchase Invoice"
	]
	invoice_details = {}
	if invoices:
		invoice_details = {
			d.name: d
			for d in frappe.get_all(
				"Purchase Invoice",
				filters={"name": ("in", invoices)},
				fields=["name", "bill_no", "is_return"],
			)
		}

	rows = []
	for row in doc.get("references") or []:
		reference = row.get("reference_name")
		total, allocated = flt(row.get("total_amount")), flt(row.get("allocated_amount"))
		if row.get("reference_doctype") == "Purchase Invoice":
			invoice = invoice_details.get(reference) or frappe._dict()
			number = row.get("bill_no") or invoice.bill_no or reference
			if invoice.is_return:
				label = _("Less: Credit Note #{0}").format(number)
				total, allocated = -abs(total), -abs(allocated)
			else:
				label = _("Invoice #{0}").format(number)
		else:
			label = f"{_(row.get('reference_doctype'))} #{reference}"

		rows.append(frappe._dict(label=label, total_amount=total, allocated_amount=allocated))
	return rows
