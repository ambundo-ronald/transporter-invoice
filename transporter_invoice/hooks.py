app_name = "transporter_invoice"
app_title = "Transporter Invoice"
app_publisher = "Norwa Africa"
app_description = "Company-scoped transport rate cards and delivery invoicing for ERPNext"
app_email = "support@example.com"
app_license = "MIT"

required_apps = ["frappe", "erpnext"]

fixtures = [
	"Custom Field",
]

after_install = "transporter_invoice.transport_invoicing.seed_data.create_default_rate_cards"

doc_events = {
	"Transport Invoice Settings": {
		"after_insert": "transporter_invoice.transport_invoicing.seed_data.create_default_rate_cards",
		"on_update": "transporter_invoice.transport_invoicing.seed_data.create_default_rate_cards",
	},
	"Sales Invoice": {
		"before_validate": "transporter_invoice.transport_invoicing.invoice_permissions.allow_generated_transport_invoice_submit",
		"validate": "transporter_invoice.transport_invoicing.invoice_permissions.allow_generated_transport_invoice_submit",
		"before_submit": "transporter_invoice.transport_invoicing.invoice_permissions.allow_generated_transport_invoice_submit",
	},
	"Purchase Invoice": {
		"before_validate": "transporter_invoice.transport_invoicing.invoice_permissions.allow_generated_transport_invoice_submit",
		"validate": "transporter_invoice.transport_invoicing.invoice_permissions.allow_generated_transport_invoice_submit",
		"before_submit": "transporter_invoice.transport_invoicing.invoice_permissions.allow_generated_transport_invoice_submit",
	},
}
