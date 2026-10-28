import json

import frappe
from frappe.email.doctype.email_template import email_template


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_email_templates(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict | str | None = None,
):
	# The v16 email composer's "Use template" sends `filters` as a JSON string, which the core method calls
	# `.get()` on, so the dropdown fails with "Couldn't load options". Drop this override once fixed upstream.
	if isinstance(filters, str):
		filters = json.loads(filters or "{}")
	return email_template.get_email_templates(
		doctype=doctype, txt=txt, searchfield=searchfield, start=start, page_len=page_len, filters=filters
	)
