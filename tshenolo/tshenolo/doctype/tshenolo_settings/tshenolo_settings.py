import frappe
from frappe import _
from frappe.model.document import Document


class TshenoloSettings(Document):
	def validate(self):
		for field in (
			"service_notification_months",
			"contract_expiry_notification_days",
			"asset_eol_notification_months",
		):
			if (self.get(field) or 0) < 0:
				frappe.throw(_("{0} cannot be negative").format(self.meta.get_label(field)))

		if self.consignment_parent_warehouse and not frappe.db.get_value(
			"Warehouse", self.consignment_parent_warehouse, "is_group"
		):
			frappe.throw(_("Consignment Parent Warehouse must be a group warehouse"))
