import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from transporter_invoice.transport_invoicing.doctype.transport_delivery.transport_delivery import (
	append_transport_invoice_items,
	get_delivery_location_summary,
)
from transporter_invoice.transport_invoicing.invoice_links import set_if_has_field, sync_delivery_invoice_status
from transporter_invoice.transport_invoicing.invoice_permissions import transport_invoice_permission_context


class TransporterBillingBatch(Document):
	def validate(self):
		self._validate_company_and_dates()
		self._validate_deliveries()
		self.total_transporter_amount = sum(flt(row.transporter_amount) for row in self.deliveries)

	def before_submit(self):
		if not self.deliveries:
			frappe.throw(_("Add at least one delivery before submitting."))

	def on_submit(self):
		for row in self.deliveries:
			frappe.db.set_value(
				"Transport Delivery",
				row.transport_delivery,
				"transporter_billing_batch",
				self.name,
				update_modified=False,
			)

	def before_cancel(self):
		if self.purchase_invoice:
			docstatus = frappe.db.get_value("Purchase Invoice", self.purchase_invoice, "docstatus")
			if docstatus is not None and docstatus != 2:
				frappe.throw(_("Cancel the linked Purchase Invoice before cancelling this batch."))
		self._unlink_deliveries()

	def on_cancel(self):
		self._unlink_deliveries()

	def _unlink_deliveries(self):
		for row in self.deliveries:
			links = frappe.db.get_value("Transport Delivery", row.transport_delivery, ["transporter_billing_batch", "purchase_invoice"], as_dict=True)
			if not links or links.transporter_billing_batch != self.name:
				continue
			updates = {"transporter_billing_batch": None}
			if not self.purchase_invoice or links.purchase_invoice == self.purchase_invoice:
				updates["purchase_invoice"] = None
			frappe.db.set_value("Transport Delivery", row.transport_delivery, updates, update_modified=False)
			sync_delivery_invoice_status(row.transport_delivery)

	def _validate_company_and_dates(self):
		configured_company = frappe.db.get_value("Transport Invoice Settings", {}, "company")
		if not configured_company:
			frappe.throw(_("Create Transport Invoice Settings before creating billing batches."))
		if self.company != configured_company:
			frappe.throw(_("Transport invoicing is restricted to company {0}.").format(frappe.bold(configured_company)))
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Date cannot be before From Date."))

	def _validate_deliveries(self):
		seen = set()
		for row in self.deliveries:
			if row.transport_delivery in seen:
				frappe.throw(_("Delivery {0} is listed more than once.").format(row.transport_delivery))
			seen.add(row.transport_delivery)
			delivery = frappe.db.get_value("Transport Delivery", row.transport_delivery,
				["company", "transporter", "docstatus", "delivery_date", "delivery_reference", "destination", "truck_class", "actual_weight_kg", "transporter_rate", "transporter_amount", "purchase_invoice", "transporter_billing_batch"], as_dict=True)
			if not delivery:
				frappe.throw(_("Delivery {0} does not exist.").format(row.transport_delivery))
			if delivery.company != self.company or delivery.transporter != self.transporter:
				frappe.throw(_("Delivery {0} belongs to a different company or transporter.").format(row.transport_delivery))
			if delivery.docstatus != 1:
				frappe.throw(_("Delivery {0} must be submitted before payment billing.").format(row.transport_delivery))
			if not (getdate(self.from_date) <= getdate(delivery.delivery_date) <= getdate(self.to_date)):
				frappe.throw(_("Delivery {0} is outside the payment period.").format(row.transport_delivery))
			if delivery.purchase_invoice and delivery.purchase_invoice != self.purchase_invoice:
				frappe.throw(_("Delivery {0} is already linked to Purchase Invoice {1}.").format(row.transport_delivery, delivery.purchase_invoice))
			if delivery.transporter_billing_batch and delivery.transporter_billing_batch != self.name:
				frappe.throw(_("Delivery {0} is already linked to Transporter Billing Batch {1}.").format(row.transport_delivery, delivery.transporter_billing_batch))
			for fieldname in ("delivery_date", "delivery_reference", "destination", "truck_class", "actual_weight_kg", "transporter_rate", "transporter_amount"):
				row.set(fieldname, delivery.get(fieldname))
			row.location = get_delivery_location_summary(row.transport_delivery)


@frappe.whitelist()
def cancel_transporter_billing_batch_only(batch_name):
	frappe.db.sql("select name from `tabTransporter Billing Batch` where name = %s for update", batch_name)
	batch = frappe.get_doc("Transporter Billing Batch", batch_name)
	batch.check_permission("cancel")
	if batch.docstatus != 1:
		frappe.throw(_("Only a submitted transporter billing batch can be cancelled."))
	batch.cancel()
	return batch.name


@frappe.whitelist()
def get_unpaid_deliveries(company, transporter, from_date, to_date):
	if not all((company, transporter, from_date, to_date)):
		frappe.throw(_("Company, Transporter, From Date, and To Date are required."))
	if getdate(to_date) < getdate(from_date):
		frappe.throw(_("To Date cannot be before From Date."))
	configured_company = frappe.db.get_value("Transport Invoice Settings", {}, "company")
	if company != configured_company:
		frappe.throw(_("Transport invoicing is restricted to company {0}.").format(frappe.bold(configured_company or "")))
	deliveries = frappe.get_list("Transport Delivery", filters={"company": company, "transporter": transporter, "docstatus": 1, "purchase_invoice": ["is", "not set"], "transporter_billing_batch": ["is", "not set"], "delivery_date": ["between", [getdate(from_date), getdate(to_date)]]},
		fields=["name as transport_delivery", "delivery_date", "delivery_reference", "destination", "truck_class", "actual_weight_kg", "transporter_rate", "transporter_amount"], order_by="delivery_date asc, name asc")
	for delivery in deliveries:
		delivery.location = get_delivery_location_summary(delivery.transport_delivery)
	return deliveries


@frappe.whitelist()
def create_purchase_invoice(batch_name):
	frappe.db.sql("select name from `tabTransporter Billing Batch` where name = %s for update", batch_name)
	batch = frappe.get_doc("Transporter Billing Batch", batch_name)
	batch.check_permission("write")
	if batch.docstatus != 1:
		frappe.throw(_("Submit the transporter billing batch before creating the Purchase Invoice."))
	if batch.purchase_invoice:
		docstatus = frappe.db.get_value("Purchase Invoice", batch.purchase_invoice, "docstatus")
		if docstatus is not None and docstatus != 2:
			return batch.purchase_invoice
		batch.db_set("purchase_invoice", None, update_modified=False)

	settings = frappe.db.get_value("Transport Invoice Settings", {"company": batch.company}, ["purchase_item", "purchase_cost_center", "auto_submit_invoices"], as_dict=True)
	if not settings:
		frappe.throw(_("Transport invoicing is not configured for company {0}.").format(batch.company))
	invoice = frappe.new_doc("Purchase Invoice")
	invoice.company, invoice.supplier, invoice.posting_date, invoice.set_posting_time = batch.company, batch.transporter, batch.posting_date, 1
	set_if_has_field(invoice, "custom_transporter_billing_batch", batch.name)
	invoice.remarks = _("Bulk transporter billing batch {0}: {1} to {2}.").format(batch.name, batch.from_date, batch.to_date)
	for row in batch.deliveries:
		delivery = frappe.get_doc("Transport Delivery", row.transport_delivery)
		if delivery.purchase_invoice:
			docstatus = frappe.db.get_value("Purchase Invoice", delivery.purchase_invoice, "docstatus")
			if docstatus is not None and docstatus != 2:
				frappe.throw(_("Delivery {0} is already linked to Purchase Invoice {1}.").format(delivery.name, delivery.purchase_invoice))
			delivery.db_set("purchase_invoice", None, update_modified=False)
		append_transport_invoice_items(invoice, delivery, settings.purchase_item, settings.purchase_cost_center, is_sales=False, include_reference=True)
	with transport_invoice_permission_context(invoice):
		invoice.set_missing_values()
		invoice.calculate_taxes_and_totals()
		invoice.insert(ignore_permissions=True)
		if settings.auto_submit_invoices:
			invoice.submit()
	batch.db_set("purchase_invoice", invoice.name, update_modified=False)
	for row in batch.deliveries:
		frappe.db.set_value("Transport Delivery", row.transport_delivery, {"purchase_invoice": invoice.name, "transporter_billing_batch": batch.name}, update_modified=False)
		sync_delivery_invoice_status(row.transport_delivery)
	return invoice.name
