import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class LegacyAccountMapping(Document):
	def validate(self):
		self.legacy_account_code = (self.legacy_account_code or "").strip()
		self.validate_unique_legacy_code()
		self.validate_new_account()
		if flt(self.opening_debit) and flt(self.opening_credit):
			frappe.throw(_("Enter either an Opening Debit or an Opening Credit, not both"))

	def validate_unique_legacy_code(self):
		duplicate = frappe.db.get_value(
			"Legacy Account Mapping",
			{
				"company": self.company,
				"legacy_account_code": self.legacy_account_code,
				"name": ("!=", self.name),
			},
		)
		if duplicate:
			frappe.throw(
				_("Legacy Account Code {0} is already mapped in {1}").format(
					frappe.bold(self.legacy_account_code), duplicate
				)
			)

	def validate_new_account(self):
		if not self.new_account:
			if self.mapping_status != "Pending":
				frappe.throw(_("Select the New Account before setting the status to {0}").format(self.mapping_status))
			return

		account = frappe.db.get_value("Account", self.new_account, ["company", "is_group"], as_dict=True)
		if account.company != self.company:
			frappe.throw(_("Account {0} does not belong to company {1}").format(self.new_account, self.company))
		if account.is_group:
			frappe.throw(_("Account {0} is a group account. Map to a ledger account.").format(self.new_account))
		if self.mapping_status == "Pending":
			self.mapping_status = "Mapped"
