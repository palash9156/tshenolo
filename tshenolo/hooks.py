app_name = "tshenolo"
app_title = "Tshenolo"
app_publisher = "Exacuer"
app_description = "Custom app for Tshenolo"
app_email = "admin@example.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext"]

# The module-wise developments are navigated from the single Tshenolo workspace, which groups
# them by module, so these modules do not get a sidebar of their own.
code_only_modules = {
	"Tshenolo Buying": ["Tshenolo"],
	"Tshenolo Selling": ["Tshenolo"],
	"Tshenolo Service": ["Tshenolo"],
	"Tshenolo Assets": ["Tshenolo"],
}

after_install = "tshenolo.setup.install.after_install"
after_migrate = "tshenolo.setup.install.after_migrate"

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "like", "Tshenolo%"]]},
	{"dt": "Property Setter", "filters": [["module", "like", "Tshenolo%"]]},
]

app_include_js = "/assets/tshenolo/js/consignment.js"

doctype_js = {
	"Purchase Order": "public/js/purchase_order.js",
	"Material Request": "public/js/material_request.js",
	"Issue": "public/js/issue.js",
	"Sales Order": "public/js/sales_order.js",
	"Sales Invoice": "public/js/sales_invoice.js",
}

doc_events = {
	"Supplier": {
		"before_insert": "tshenolo.events.buying.set_supplier_code",
		"validate": "tshenolo.events.buying.validate_supplier_vetting",
	},
	"Item": {
		"validate": "tshenolo.events.buying.set_item_classification",
	},
	"Material Request": {
		"validate": "tshenolo.events.buying.validate_consignment_request",
	},
	"Supplier Quotation": {
		"validate": "tshenolo.events.buying.validate_supplier_is_vetted",
	},
	"Purchase Order": {
		"before_validate": "tshenolo.events.buying.apply_sample_pricing",
		"validate": [
			"tshenolo.events.buying.validate_supplier_is_vetted",
			"tshenolo.events.buying.set_follow_up_po_items",
		],
		"before_update_after_submit": "tshenolo.events.buying.set_follow_up_po_items",
	},
	"Purchase Receipt": {
		"before_validate": "tshenolo.events.buying.apply_sample_pricing",
		"on_submit": [
			"tshenolo.events.buying.update_asn_received_qty",
			"tshenolo.events.selling.copy_supplier_lot_to_batch",
		],
		"on_cancel": "tshenolo.events.buying.update_asn_received_qty",
	},
	"Purchase Invoice": {
		"validate": "tshenolo.events.buying.validate_supplier_is_vetted",
	},
	"Sales Order": {
		"validate": [
			"tshenolo.events.selling.set_back_order_status",
			"tshenolo.events.service.validate_service_order",
		],
	},
	"Delivery Note": {
		"validate": "tshenolo.events.selling.set_supplier_lot_no",
		"on_submit": [
			"tshenolo.events.selling.set_supplier_lot_no",
			"tshenolo.events.selling.update_sales_order_back_orders",
		],
		"on_cancel": "tshenolo.events.selling.update_sales_order_back_orders",
	},
	"Sales Invoice": {
		"validate": [
			"tshenolo.events.selling.set_supplier_lot_no",
			"tshenolo.events.selling.validate_consignment_utilisation",
			"tshenolo.events.service.validate_contract",
		],
		"before_submit": "tshenolo.events.service.validate_contract_balance",
		"on_submit": [
			"tshenolo.events.selling.set_supplier_lot_no",
			"tshenolo.events.selling.update_sales_order_back_orders",
			"tshenolo.events.selling.link_consignment_utilisation",
			"tshenolo.events.service.update_contract_value",
		],
		"on_cancel": [
			"tshenolo.events.selling.update_sales_order_back_orders",
			"tshenolo.events.selling.link_consignment_utilisation",
			"tshenolo.events.service.update_contract_value",
		],
	},
	"Contract": {
		"validate": "tshenolo.events.service.set_contract_balance",
	},
	"Issue": {
		"validate": "tshenolo.events.service.validate_issue",
	},
	"Serial No": {
		"validate": "tshenolo.events.service.set_next_service_date",
	},
	"Maintenance Visit": {
		"on_submit": "tshenolo.events.service.update_equipment_service_dates",
		"on_cancel": "tshenolo.events.service.update_equipment_service_dates",
	},
	"Asset": {
		"validate": "tshenolo.events.assets.set_asset_dates",
		"before_update_after_submit": "tshenolo.events.assets.set_asset_dates",
	},
	"Asset Maintenance Log": {
		"on_submit": "tshenolo.events.assets.update_asset_service_date",
		"on_cancel": "tshenolo.events.assets.update_asset_service_date",
	},
}

scheduler_events = {
	"daily": [
		"tshenolo.tasks.create_supplier_follow_up_todos",
		"tshenolo.tasks.notify_service_due",
		"tshenolo.tasks.notify_asset_end_of_life",
		"tshenolo.tasks.notify_contract_status",
	],
}

override_doctype_dashboards = {
	"Purchase Order": "tshenolo.events.dashboards.purchase_order",
	"Material Request": "tshenolo.events.dashboards.material_request",
	"Customer": "tshenolo.events.dashboards.customer",
	"Issue": "tshenolo.events.dashboards.issue",
	"Contract": "tshenolo.events.dashboards.contract",
}

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "tshenolo",
# 		"logo": "/assets/tshenolo/logo.png",
# 		"title": "Tshenolo",
# 		"route": "/tshenolo",
# 		"has_permission": "tshenolo.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/tshenolo/css/tshenolo.css"
# app_include_js = "/assets/tshenolo/js/tshenolo.js"

# include js, css files in header of web template
# web_include_css = "/assets/tshenolo/css/tshenolo.css"
# web_include_js = "/assets/tshenolo/js/tshenolo.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "tshenolo/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "tshenolo/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
jinja = {
	"methods": ["tshenolo.print_utils"],
}

# Installation
# ------------

# before_install = "tshenolo.install.before_install"
# after_install = "tshenolo.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "tshenolo.uninstall.before_uninstall"
# after_uninstall = "tshenolo.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "tshenolo.utils.before_app_install"
# after_app_install = "tshenolo.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "tshenolo.utils.before_app_uninstall"
# after_app_uninstall = "tshenolo.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "tshenolo.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "tshenolo.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["tshenolo.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"tshenolo.tasks.all"
# 	],
# 	"daily": [
# 		"tshenolo.tasks.daily"
# 	],
# 	"hourly": [
# 		"tshenolo.tasks.hourly"
# 	],
# 	"weekly": [
# 		"tshenolo.tasks.weekly"
# 	],
# 	"monthly": [
# 		"tshenolo.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "tshenolo.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "tshenolo.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"frappe.email.doctype.email_template.email_template.get_email_templates": (
		"tshenolo.overrides.get_email_templates"
	),
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "tshenolo.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["tshenolo.utils.before_request"]
# after_request = ["tshenolo.utils.after_request"]

# Job Events
# ----------
# before_job = ["tshenolo.utils.before_job"]
# after_job = ["tshenolo.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"tshenolo.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

