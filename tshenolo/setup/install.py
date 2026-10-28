import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from tshenolo.setup.custom_fields import get_custom_fields


def after_install():
	setup()


def after_migrate():
	setup()


EMAIL_TEMPLATES = {
	"Tshenolo GRN Receipt": ("Purchase Receipt", "grn_notification"),
	"Tshenolo Remittance Advice": ("Payment Entry", "remittance_notification"),
}

DEFAULT_PRINT_FORMATS = {
	"Purchase Order": "Tshenolo Purchase Order",
	"Purchase Receipt": "Tshenolo GRN",
	"Payment Entry": "Tshenolo Remittance Advice",
}


def setup():
	create_custom_fields(get_custom_fields(), ignore_validate=True)
	set_settings_defaults()
	sync_email_templates()
	set_default_print_formats()


def set_settings_defaults():
	# Single doctypes only fall back to field defaults while nothing is stored, so persist them.
	stored = frappe.db.get_singles_dict("Tshenolo Settings")
	for df in frappe.get_meta("Tshenolo Settings").fields:
		if df.default and df.fieldname not in stored:
			frappe.db.set_single_value("Tshenolo Settings", df.fieldname, df.default)
	frappe.clear_document_cache("Tshenolo Settings", "Tshenolo Settings")


def sync_email_templates():
	# Email Template is not synced from module folders. Its render context is the doc's fields, not `doc`, so
	# load the doc and include the same body and subject the Notifications use, keeping both in step.
	for name, (doctype, template) in EMAIL_TEMPLATES.items():
		load_doc = "{% set doc = frappe.get_doc(doctype, name) %}"
		values = {
			"reference_doctype": doctype,
			"use_html": 1,
			"subject": f'{load_doc}{{% include "tshenolo/templates/emails/{template}_subject.txt" %}}',
			"response_html": f'{load_doc}{{% include "tshenolo/templates/emails/{template}.html" %}}',
		}
		if frappe.db.exists("Email Template", name):
			frappe.db.set_value("Email Template", name, values)
		else:
			frappe.get_doc({"doctype": "Email Template", "name": name, **values}).insert(ignore_permissions=True)


def set_default_print_formats():
	# Only set once, so a default the user picks later is not overwritten on migrate.
	for doctype, print_format in DEFAULT_PRINT_FORMATS.items():
		if not frappe.get_meta(doctype).default_print_format:
			make_property_setter(doctype, None, "default_print_format", print_format, "Data", for_doctype=True)
