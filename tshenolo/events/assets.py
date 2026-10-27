import frappe
from frappe.utils import add_months, getdate

from tshenolo.events.service import get_next_service_date


def get_end_of_life_date(asset):
	if not asset.available_for_use_date:
		return None

	if asset.calculate_depreciation and asset.get("finance_books"):
		book = asset.finance_books[0]
		months = (book.total_number_of_depreciations or 0) * (book.frequency_of_depreciation or 0)
		months += book.get("increase_in_asset_life") or 0
	else:
		months = (asset.get("total_number_of_depreciations") or 0) * (asset.get("frequency_of_depreciation") or 0)

	if not months:
		return None
	return add_months(getdate(asset.available_for_use_date), months)


def set_asset_dates(doc, method=None):
	doc.end_of_life_date = get_end_of_life_date(doc)
	doc.next_service_date = get_next_service_date(
		doc.get("last_service_date") or doc.available_for_use_date, doc.get("service_interval_months")
	)


def update_asset_service_date(doc, method=None):
	if doc.maintenance_status != "Completed":
		return
	asset_name = frappe.db.get_value("Asset Maintenance", doc.asset_maintenance, "asset_name")
	if not asset_name:
		return

	latest = frappe.db.sql(
		"""
		select max(log.completion_date)
		from `tabAsset Maintenance Log` log
		inner join `tabAsset Maintenance` am on am.name = log.asset_maintenance
		where am.asset_name = %s and log.docstatus = 1 and log.maintenance_status = 'Completed'
		""",
		asset_name,
	)[0][0]

	asset = frappe.db.get_value(
		"Asset", asset_name, ["available_for_use_date", "service_interval_months"], as_dict=True
	)
	frappe.db.set_value(
		"Asset",
		asset_name,
		{
			"last_service_date": latest,
			"next_service_date": get_next_service_date(
				latest or asset.available_for_use_date, asset.service_interval_months
			),
		},
	)
