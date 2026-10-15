import frappe


def set_if_has_field(doc, fieldname, value):
	if doc.meta.has_field(fieldname):
		doc.set(fieldname, value)


def get_delivery_invoice_status(sales_invoice=None, purchase_invoice=None):
	if sales_invoice and purchase_invoice:
		return "Fully Invoiced"
	if sales_invoice:
		return "Customer Invoiced"
	if purchase_invoice:
		return "Transporter Invoiced"
	return "Ready for Invoicing"


def sync_delivery_invoice_status(delivery_name):
	links = frappe.db.get_value(
		"Transport Delivery",
		delivery_name,
		["sales_invoice", "purchase_invoice"],
		as_dict=True,
	)
	if not links:
		return

	sales_invoice = _get_active_invoice("Sales Invoice", links.sales_invoice)
	purchase_invoice = _get_active_invoice("Purchase Invoice", links.purchase_invoice)
	link_updates = {}
	if links.sales_invoice and not sales_invoice:
		link_updates["sales_invoice"] = None
	if links.purchase_invoice and not purchase_invoice:
		link_updates["purchase_invoice"] = None
	if link_updates:
		frappe.db.set_value("Transport Delivery", delivery_name, link_updates, update_modified=False)

	frappe.db.set_value(
		"Transport Delivery",
		delivery_name,
		"workflow_state",
		get_delivery_invoice_status(sales_invoice, purchase_invoice),
		update_modified=False,
	)


def _get_active_invoice(doctype, invoice_name):
	if not invoice_name:
		return None
	docstatus = frappe.db.get_value(doctype, invoice_name, "docstatus")
	return invoice_name if docstatus is not None and int(docstatus) != 2 else None


def unlink_transport_invoice(doc, method=None):
	link_field = "sales_invoice" if doc.doctype == "Sales Invoice" else "purchase_invoice"
	delivery_names = frappe.get_all(
		"Transport Delivery",
		filters={link_field: doc.name},
		pluck="name",
	)

	for delivery_name in delivery_names:
		frappe.db.set_value(
			"Transport Delivery",
			delivery_name,
			link_field,
			None,
			update_modified=False,
		)
		sync_delivery_invoice_status(delivery_name)

	if doc.doctype == "Sales Invoice":
		frappe.db.set_value(
			"Transport Billing Batch",
			{"sales_invoice": doc.name},
			"sales_invoice",
			None,
			update_modified=False,
		)
	else:
		frappe.db.set_value(
			"Transporter Billing Batch",
			{"purchase_invoice": doc.name},
			"purchase_invoice",
			None,
			update_modified=False,
		)
