import frappe
from frappe import _
from frappe.utils import add_days, add_months, flt, formatdate, getdate, today

from tshenolo.utils import get_role_users, get_settings, notify_users


def get_buyers(owner, fallback_role):
	if owner and frappe.db.get_value("User", owner, "enabled") and owner not in ("Administrator", "Guest"):
		return [owner]
	return get_role_users(fallback_role)


def create_supplier_follow_up_todos():
	settings = get_settings()
	current = today()

	follow_ups = frappe.db.sql(
		"""
		select fu.parent, fu.item_code, fu.follow_up_date, fu.buyer, po.supplier, po.owner
		from `tabSupplier Follow Up` fu
		inner join `tabPurchase Order` po on po.name = fu.parent and fu.parenttype = 'Purchase Order'
		where po.docstatus = 1 and po.status not in ('Closed', 'Completed')
			and fu.status != 'Resolved' and fu.follow_up_date <= %s
		""",
		current,
		as_dict=True,
	)
	for fu in follow_ups:
		description = _("Supplier follow-up due on {0} for {1} on Purchase Order {2} ({3})").format(
			formatdate(fu.follow_up_date), fu.item_code or _("all items"), fu.parent, fu.supplier
		)
		users = [fu.buyer] if fu.buyer else get_buyers(fu.owner, settings.buyer_alert_role)
		notify_users(users, "Purchase Order", fu.parent, description, date=fu.follow_up_date)

	overdue = frappe.db.sql(
		"""
		select po.name, po.supplier, po.owner, count(*) as items,
			min(coalesce(poi.expected_delivery_date, poi.schedule_date)) as since
		from `tabPurchase Order` po
		inner join `tabPurchase Order Item` poi on poi.parent = po.name
		where po.docstatus = 1 and po.status not in ('Closed', 'Completed', 'On Hold')
			and poi.received_qty < poi.qty
			and coalesce(poi.expected_delivery_date, poi.schedule_date) < %s
		group by po.name, po.supplier, po.owner
		""",
		current,
		as_dict=True,
	)
	for po in overdue:
		description = _("Purchase Order {0} ({1}) has {2} item(s) overdue since {3}. Follow up with the supplier.").format(
			po.name, po.supplier, po.items, formatdate(po.since)
		)
		notify_users(get_buyers(po.owner, settings.buyer_alert_role), "Purchase Order", po.name, description)


def notify_service_due():
	settings = get_settings()
	horizon = add_months(today(), settings.service_notification_months or 0)

	equipment = frappe.get_all(
		"Serial No",
		filters=[
			["next_service_date", "is", "set"],
			["next_service_date", "<=", horizon],
			["status", "not in", ("Inactive", "Expired", "Consumed")],
		],
		fields=["name", "item_code", "customer", "next_service_date"],
	)
	service_users = get_role_users(settings.service_alert_role)
	for d in equipment:
		description = _("Service due on {0} for equipment {1} ({2}){3}").format(
			formatdate(d.next_service_date),
			d.name,
			d.item_code,
			_(" at {0}").format(d.customer) if d.customer else "",
		)
		notify_users(service_users, "Serial No", d.name, description, date=d.next_service_date)

	assets = frappe.get_all(
		"Asset",
		filters=[
			["docstatus", "=", 1],
			["status", "not in", ("Scrapped", "Sold")],
			["next_service_date", "is", "set"],
			["next_service_date", "<=", horizon],
		],
		fields=["name", "asset_name", "next_service_date"],
	)
	asset_users = get_role_users(settings.asset_alert_role)
	for d in assets:
		description = _("Service due on {0} for asset {1} ({2})").format(
			formatdate(d.next_service_date), d.name, d.asset_name
		)
		notify_users(asset_users, "Asset", d.name, description, date=d.next_service_date)


def notify_asset_end_of_life():
	settings = get_settings()
	horizon = add_months(today(), settings.asset_eol_notification_months or 0)
	assets = frappe.get_all(
		"Asset",
		filters=[
			["docstatus", "=", 1],
			["status", "not in", ("Scrapped", "Sold")],
			["end_of_life_date", "is", "set"],
			["end_of_life_date", "<=", horizon],
		],
		fields=["name", "asset_name", "end_of_life_date"],
	)
	users = get_role_users(settings.asset_alert_role)
	for d in assets:
		description = _("Asset {0} ({1}) reaches the end of its useful life on {2}. Plan replacement.").format(
			d.name, d.asset_name, formatdate(d.end_of_life_date)
		)
		notify_users(users, "Asset", d.name, description, date=d.end_of_life_date)


def notify_contract_status():
	settings = get_settings()
	users = get_role_users(settings.contract_alert_role)
	current = getdate(today())
	expiry_horizon = getdate(add_days(current, settings.contract_expiry_notification_days or 0))
	low_balance_percent = flt(settings.contract_low_balance_percent)

	contracts = frappe.get_all(
		"Contract",
		filters={"docstatus": ("<", 2), "status": ("!=", "Inactive")},
		fields=["name", "contract_no", "party_name", "end_date", "contract_value", "remaining_value"],
	)
	for c in contracts:
		label = f"{c.name} ({c.contract_no})" if c.contract_no else c.name
		if flt(c.contract_value) > 0:
			if flt(c.remaining_value) <= 0:
				description = _("SLA Contract {0} for {1} has used its full contract value.").format(
					label, c.party_name
				)
				notify_users(users, "Contract", c.name, description)
			elif flt(c.remaining_value) <= flt(c.contract_value) * low_balance_percent / 100:
				description = _("SLA Contract {0} for {1} is below {2}% of its contract value.").format(
					label, c.party_name, low_balance_percent
				)
				notify_users(users, "Contract", c.name, description)

		if c.end_date and current <= getdate(c.end_date) <= expiry_horizon:
			description = _("SLA Contract {0} for {1} expires on {2}.").format(
				label, c.party_name, formatdate(c.end_date)
			)
			notify_users(users, "Contract", c.name, description, date=c.end_date)
