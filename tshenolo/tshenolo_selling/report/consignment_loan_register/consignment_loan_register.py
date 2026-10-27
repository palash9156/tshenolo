import frappe
from frappe import _
from frappe.utils import date_diff, getdate, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Consignment Loan"), "fieldname": "name", "fieldtype": "Link", "options": "Consignment Loan", "width": 160},
		{"label": _("Customer / Hospital"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
		{"label": _("Equipment"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
		{"label": _("Serial No"), "fieldname": "serial_no", "fieldtype": "Link", "options": "Serial No", "width": 140},
		{"label": _("Loan Date"), "fieldname": "loan_date", "fieldtype": "Date", "width": 100},
		{"label": _("Expected Return"), "fieldname": "expected_return_date", "fieldtype": "Date", "width": 120},
		{"label": _("Days on Loan"), "fieldname": "days_on_loan", "fieldtype": "Int", "width": 100},
		{"label": _("Overdue"), "fieldname": "overdue", "fieldtype": "Check", "width": 80},
		{"label": _("Service Due"), "fieldname": "service_due_date", "fieldtype": "Date", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": _("Return Date"), "fieldname": "return_date", "fieldtype": "Date", "width": 100},
		{"label": _("Delivery Note"), "fieldname": "delivery_note", "fieldtype": "Link", "options": "Delivery Note", "width": 140},
	]


def get_data(filters):
	query_filters = {"docstatus": 1}
	for field in ("company", "customer", "item_code", "status"):
		if filters.get(field):
			query_filters[field] = filters[field]

	loans = frappe.get_all(
		"Consignment Loan",
		filters=query_filters,
		fields=[
			"name",
			"customer",
			"item_code",
			"serial_no",
			"loan_date",
			"expected_return_date",
			"service_due_date",
			"status",
			"return_date",
			"delivery_note",
		],
		order_by="loan_date desc",
	)

	current = getdate(today())
	for loan in loans:
		end = loan.return_date or current
		loan.days_on_loan = date_diff(end, loan.loan_date)
		loan.overdue = (
			1
			if loan.status == "On Loan" and loan.expected_return_date and getdate(loan.expected_return_date) < current
			else 0
		)
	return loans
