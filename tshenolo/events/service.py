import frappe
from frappe import _
from frappe.utils import add_months, flt, fmt_money, getdate, nowdate

from tshenolo.utils import get_settings


def get_next_service_date(base_date, interval_months):
	if not base_date or not interval_months:
		return None
	return add_months(getdate(base_date), interval_months)


def set_next_service_date(doc, method=None):
	doc.next_service_date = get_next_service_date(
		doc.get("last_service_date") or doc.get("installation_date"), doc.get("service_interval_months")
	)


def update_equipment_service_dates(doc, method=None):
	if doc.completion_status != "Fully Completed":
		return

	for serial_no in {d.serial_no for d in doc.purposes if d.get("serial_no")}:
		latest = frappe.db.sql(
			"""
			select max(mv.mntc_date)
			from `tabMaintenance Visit` mv
			inner join `tabMaintenance Visit Purpose` mvp on mvp.parent = mv.name
			where mvp.serial_no = %s and mv.docstatus = 1 and mv.completion_status = 'Fully Completed'
			""",
			serial_no,
		)[0][0]

		equipment = frappe.db.get_value(
			"Serial No",
			serial_no,
			["installation_date", "service_interval_months", "last_service_date"],
			as_dict=True,
		)
		if not equipment:
			continue
		if not latest and equipment.last_service_date and getdate(equipment.last_service_date) != getdate(doc.mntc_date):
			continue

		frappe.db.set_value(
			"Serial No",
			serial_no,
			{
				"last_service_date": latest,
				"next_service_date": get_next_service_date(
					latest or equipment.installation_date, equipment.service_interval_months
				),
			},
		)


def validate_issue(doc, method=None):
	if doc.get("contract"):
		party_type, party_name = frappe.db.get_value("Contract", doc.contract, ["party_type", "party_name"])
		if party_type != "Customer":
			frappe.throw(_("SLA Contract {0} is not a customer contract").format(doc.contract))
		if not doc.customer:
			doc.customer = party_name
		elif doc.customer != party_name:
			frappe.throw(_("SLA Contract {0} belongs to customer {1}").format(doc.contract, party_name))

	if doc.get("serial_no"):
		equipment_customer = frappe.db.get_value("Serial No", doc.serial_no, "customer")
		if equipment_customer and not doc.customer:
			doc.customer = equipment_customer
		elif equipment_customer and equipment_customer != doc.customer:
			frappe.msgprint(
				_("Equipment {0} is registered to customer {1}").format(doc.serial_no, equipment_customer),
				indicator="orange",
				alert=True,
			)


def validate_contract_party(contract, customer):
	details = frappe.db.get_value(
		"Contract", contract, ["party_type", "party_name", "docstatus", "start_date", "end_date"], as_dict=True
	)
	if details.docstatus == 2:
		frappe.throw(_("SLA Contract {0} is cancelled").format(contract))
	if details.party_type != "Customer" or details.party_name != customer:
		frappe.throw(_("SLA Contract {0} does not belong to customer {1}").format(contract, customer))
	return details


def validate_service_order(doc, method=None):
	if doc.get("issue"):
		doc.is_service_order = 1
		if not doc.get("contract"):
			doc.contract = frappe.db.get_value("Issue", doc.issue, "contract")
	if doc.get("is_service_order") and doc.order_type == "Sales":
		doc.order_type = "Maintenance"
	if doc.get("contract"):
		validate_contract_party(doc.contract, doc.customer)


def validate_contract(doc, method=None):
	if not doc.get("contract"):
		return
	details = validate_contract_party(doc.contract, doc.customer)
	posting_date = getdate(doc.posting_date)
	if (details.start_date and posting_date < getdate(details.start_date)) or (
		details.end_date and posting_date > getdate(details.end_date)
	):
		frappe.throw(
			_("Posting Date {0} is outside the period of SLA Contract {1}").format(doc.posting_date, doc.contract)
		)


def get_contract_utilised(contract, exclude_invoice=None):
	return flt(
		frappe.db.sql(
			"""
			select coalesce(sum(base_grand_total), 0)
			from `tabSales Invoice`
			where contract = %s and docstatus = 1 and name != %s
			""",
			(contract, exclude_invoice or ""),
		)[0][0]
	)


def validate_contract_balance(doc, method=None):
	if not doc.get("contract") or doc.is_return or not get_settings().block_contract_overrun:
		return
	contract_value = flt(frappe.db.get_value("Contract", doc.contract, "contract_value"))
	if contract_value <= 0:
		return
	remaining = contract_value - get_contract_utilised(doc.contract, doc.name)
	if flt(doc.base_grand_total) > remaining:
		frappe.throw(
			_("Invoice total {0} exceeds the remaining value {1} of SLA Contract {2}").format(
				fmt_money(doc.base_grand_total), fmt_money(remaining), doc.contract
			),
			title=_("Contract Value Exceeded"),
		)


def update_contract_value(doc, method=None):
	if not doc.get("contract"):
		return
	utilised = get_contract_utilised(doc.contract)
	contract_value = flt(frappe.db.get_value("Contract", doc.contract, "contract_value"))
	frappe.db.set_value(
		"Contract",
		doc.contract,
		{"utilised_value": utilised, "remaining_value": contract_value - utilised},
		update_modified=False,
	)


def set_contract_balance(doc, method=None):
	if flt(doc.get("contract_value")) < 0:
		frappe.throw(_("Contract Value cannot be negative"))
	doc.utilised_value = 0 if doc.is_new() else get_contract_utilised(doc.name)
	doc.remaining_value = flt(doc.get("contract_value")) - flt(doc.utilised_value)


@frappe.whitelist()
def make_service_sales_order(source_name):
	issue = frappe.get_doc("Issue", source_name)
	issue.check_permission("read")
	if not issue.customer:
		frappe.throw(_("Set the Customer on {0} before creating a Service Sales Order").format(issue.name))

	so = frappe.new_doc("Sales Order")
	so.customer = issue.customer
	if issue.company:
		so.company = issue.company
	so.order_type = "Maintenance"
	so.is_service_order = 1
	so.issue = issue.name
	so.contract = issue.get("contract")
	so.transaction_date = nowdate()
	so.delivery_date = nowdate()

	if service_item := get_settings().default_service_item:
		so.append(
			"items",
			{
				"item_code": service_item,
				"qty": 1,
				"delivery_date": nowdate(),
				"description": issue.subject,
			},
		)

	so.run_method("set_missing_values")
	so.run_method("calculate_taxes_and_totals")
	return so
