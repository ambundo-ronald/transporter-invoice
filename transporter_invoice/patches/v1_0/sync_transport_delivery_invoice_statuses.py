import frappe

from transporter_invoice.transport_invoicing.invoice_links import sync_delivery_invoice_status


def execute():
	delivery_names = frappe.get_all(
		"Transport Delivery",
		filters={"docstatus": 1},
		pluck="name",
	)
	for delivery_name in delivery_names:
		sync_delivery_invoice_status(delivery_name)
