import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from tshenolo.setup.custom_fields import get_custom_fields


def after_install():
	setup()


def after_migrate():
	setup()


def setup():
	create_custom_fields(get_custom_fields(), ignore_validate=True)
	set_settings_defaults()


def set_settings_defaults():
	# Single doctypes only fall back to field defaults while nothing is stored, so persist them.
	stored = frappe.db.get_singles_dict("Tshenolo Settings")
	for df in frappe.get_meta("Tshenolo Settings").fields:
		if df.default and df.fieldname not in stored:
			frappe.db.set_single_value("Tshenolo Settings", df.fieldname, df.default)
	frappe.clear_document_cache("Tshenolo Settings", "Tshenolo Settings")
