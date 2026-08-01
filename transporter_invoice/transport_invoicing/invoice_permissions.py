import frappe


TRANSPORT_LINK_FIELDS = (
	"custom_transport_delivery",
	"custom_transport_billing_batch",
)


def allow_generated_transport_invoice_submit(doc, method=None):
	"""Generated transport invoices may be submitted by transport users.

	The user permission is checked on the source Transport Delivery or Billing Batch
	when the invoice is created. If the generated invoice remains in draft and the
	user submits it later, ERPNext otherwise re-checks Item read permission and can
	block users who should not have general Item access.
	"""
	if not _is_generated_transport_invoice(doc):
		return

	doc.flags.ignore_permissions = True
	for row in getattr(doc, "items", []) or []:
		row.flags.ignore_permissions = True


def _is_generated_transport_invoice(doc):
	for fieldname in TRANSPORT_LINK_FIELDS:
		if doc.meta.has_field(fieldname) and doc.get(fieldname):
			return True

	for row in getattr(doc, "items", []) or []:
		if row.meta.has_field("custom_transport_delivery") and row.get("custom_transport_delivery"):
			return True

	return False