import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import flt, today

from tshenolo.utils import get_settings

VETTING_APPROVER_ROLES = {"Purchase Manager", "System Manager"}


def set_supplier_code(doc, method=None):
	if doc.get("supplier_code"):
		return
	if series := get_settings().supplier_code_series:
		doc.supplier_code = make_autoname(series, doc=doc)


def validate_supplier_vetting(doc, method=None):
	before = doc.get_doc_before_save()
	previous = (before.get("vetting_status") if before else None) or "Pending"
	current = doc.get("vetting_status") or "Pending"
	if current == previous:
		return

	if not VETTING_APPROVER_ROLES & set(frappe.get_roles()):
		frappe.throw(
			_("Only a Purchase Manager can change the Vetting Status of a supplier"),
			frappe.PermissionError,
		)

	if current == "Pending":
		doc.vetted_by = None
		doc.vetting_date = None
	else:
		doc.vetted_by = frappe.session.user
		doc.vetting_date = today()


def validate_supplier_is_vetted(doc, method=None):
	if not doc.get("supplier") or doc.get("is_return") or not get_settings().enforce_supplier_vetting:
		return

	supplier = frappe.db.get_value(
		"Supplier", doc.supplier, ["vetting_status", "is_internal_supplier"], as_dict=True
	)
	if not supplier or supplier.is_internal_supplier:
		return
	if supplier.vetting_status != "Approved":
		frappe.throw(
			_("Supplier {0} is not vetted (Vetting Status: {1}). Approve the supplier before creating a {2}.").format(
				frappe.bold(doc.supplier), supplier.vetting_status or "Pending", _(doc.doctype)
			),
			title=_("Unvetted Supplier"),
		)


def set_item_classification(doc, method=None):
	if doc.get("item_classification"):
		return
	if doc.is_fixed_asset:
		doc.item_classification = "Asset"
	elif not doc.is_stock_item:
		doc.item_classification = "Service"
	else:
		doc.item_classification = "Consumable"


def validate_consignment_request(doc, method=None):
	if not doc.get("is_consignment"):
		return
	if doc.material_request_type != "Material Transfer":
		frappe.throw(_("A Consignment Material Request must have the Purpose 'Material Transfer'"))
	if not doc.consignment_customer or not doc.sales_person:
		frappe.throw(_("Consignment Customer and Requesting Sales Person are mandatory for consignment requests"))


def apply_sample_pricing(doc, method=None):
	"""Samples are received at zero value; runs before the controller recalculates totals."""
	for item in doc.get("items") or []:
		if not item.get("is_sample"):
			continue
		item.price_list_rate = 0
		item.discount_percentage = 0
		item.discount_amount = 0
		item.margin_rate_or_amount = 0
		item.rate = 0
		if item.meta.has_field("allow_zero_valuation_rate"):
			item.allow_zero_valuation_rate = 1


def set_follow_up_po_items(doc, method=None):
	po_items = {}
	for item in doc.items:
		po_items.setdefault(item.item_code, item)

	for row in doc.get("supplier_follow_ups") or []:
		if not row.item_code:
			row.purchase_order_item = None
			continue
		po_item = po_items.get(row.item_code)
		if not po_item:
			frappe.throw(
				_("Row #{0} (Supplier Follow-ups): Item {1} is not on this Purchase Order").format(
					row.idx, frappe.bold(row.item_code)
				)
			)
		row.purchase_order_item = po_item.name
		if not row.eta:
			row.eta = po_item.expected_delivery_date or po_item.schedule_date


def update_asn_received_qty(doc, method=None):
	asn_details = {d.asn_detail for d in doc.items if d.get("asn_detail")}
	if not asn_details:
		return

	for asn_detail in asn_details:
		received = frappe.db.sql(
			"""
			select coalesce(sum(pri.received_qty), 0)
			from `tabPurchase Receipt Item` pri
			inner join `tabPurchase Receipt` pr on pr.name = pri.parent
			where pri.asn_detail = %s and pr.docstatus = 1 and pr.is_return = 0
			""",
			asn_detail,
		)[0][0]
		frappe.db.set_value("ASN Item", asn_detail, "received_qty", flt(received))

	for asn in {d.asn for d in doc.items if d.get("asn")}:
		frappe.get_doc("Advance Shipping Notice", asn).update_status()
