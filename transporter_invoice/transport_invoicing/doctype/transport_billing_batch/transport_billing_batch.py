import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from transporter_invoice.transport_invoicing.invoice_links import set_if_has_field


class TransportBillingBatch(Document):
	def validate(self):
		self._validate_configured_company()
		self._validate_dates()
		self._validate_deliveries()
		self._calculate_total()

	def before_submit(self):
		if not self.deliveries:
			frappe.throw(_("Add at least one delivery before submitting."))

	def on_cancel(self):
		if self.sales_invoice and frappe.db.get_value("Sales Invoice", self.sales_invoice, "docstatus") != 2:
			frappe.throw(_("Cancel the linked Sales Invoice before cancelling this billing batch."))
		for row in self.deliveries:
			frappe.db.set_value(
				"Transport Delivery",
				row.transport_delivery,
				{"sales_invoice": None, "billing_batch": None},
				update_modified=False,
			)

	def _validate_configured_company(self):
		configured_company = frappe.db.get_value("Transport Invoice Settings", {}, "company")
		if not configured_company:
			frappe.throw(_("Create Transport Invoice Settings before creating billing batches."))
		if self.company != configured_company:
			frappe.throw(
				_("Transport invoicing is restricted to company {0}.").format(
					frappe.bold(configured_company)
				)
			)

	def _validate_dates(self):
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Date cannot be before From Date."))

	def _validate_deliveries(self):
		seen = set()
		for row in self.deliveries:
			if row.transport_delivery in seen:
				frappe.throw(_("Delivery {0} is listed more than once.").format(row.transport_delivery))
			seen.add(row.transport_delivery)

			delivery = frappe.db.get_value(
				"Transport Delivery",
				row.transport_delivery,
				[
					"company",
					"customer",
					"docstatus",
					"delivery_date",
					"delivery_reference",
					"destination",
					"truck_class",
					"actual_weight_kg",
					"customer_rate",
					"customer_amount",
					"sales_invoice",
				],
				as_dict=True,
			)
			if not delivery:
				frappe.throw(_("Delivery {0} does not exist.").format(row.transport_delivery))
			if delivery.company != self.company or delivery.customer != self.customer:
				frappe.throw(_("Delivery {0} belongs to a different company or customer.").format(row.transport_delivery))
			if delivery.docstatus != 1:
				frappe.throw(_("Delivery {0} must be submitted before billing.").format(row.transport_delivery))
			if not (getdate(self.from_date) <= getdate(delivery.delivery_date) <= getdate(self.to_date)):
				frappe.throw(_("Delivery {0} is outside the billing period.").format(row.transport_delivery))
			if delivery.sales_invoice and delivery.sales_invoice != self.sales_invoice:
				frappe.throw(_("Delivery {0} is already linked to Sales Invoice {1}.").format(
					row.transport_delivery, delivery.sales_invoice
				))

			row.delivery_date = delivery.delivery_date
			row.delivery_reference = delivery.delivery_reference
			row.destination = delivery.destination
			row.truck_class = delivery.truck_class
			row.actual_weight_kg = delivery.actual_weight_kg
			row.customer_rate = delivery.customer_rate
			row.customer_amount = delivery.customer_amount

	def _calculate_total(self):
		self.total_customer_amount = sum(flt(row.customer_amount) for row in self.deliveries)


@frappe.whitelist()
def get_unbilled_deliveries(company, customer, from_date, to_date):
	if not all((company, customer, from_date, to_date)):
		frappe.throw(_("Company, customer, From Date, and To Date are required."))
	if getdate(to_date) < getdate(from_date):
		frappe.throw(_("To Date cannot be before From Date."))

	configured_company = frappe.db.get_value("Transport Invoice Settings", {}, "company")
	if not configured_company:
		frappe.throw(_("Create Transport Invoice Settings before fetching deliveries."))
	if company != configured_company:
		frappe.throw(
			_("Transport invoicing is restricted to company {0}.").format(
				frappe.bold(configured_company or "")
			)
		)

	deliveries = frappe.get_list(
		"Transport Delivery",
		filters={
			"company": company,
			"customer": customer,
			"docstatus": 1,
			"sales_invoice": ["is", "not set"],
			"delivery_date": ["between", [getdate(from_date), getdate(to_date)]],
		},
		fields=[
			"name as transport_delivery",
			"delivery_date",
			"delivery_reference",
			"destination",
			"truck_class",
			"actual_weight_kg",
			"customer_rate",
			"customer_amount",
		],
		order_by="delivery_date asc, name asc",
	)
	return deliveries


@frappe.whitelist()
def create_sales_invoice(batch_name):
	frappe.db.sql(
		"select name from `tabTransport Billing Batch` where name = %s for update",
		batch_name,
	)
	batch = frappe.get_doc("Transport Billing Batch", batch_name)
	batch.check_permission("write")
	if batch.docstatus != 1:
		frappe.throw(_("Submit the billing batch before creating the Sales Invoice."))
	if batch.sales_invoice and frappe.db.exists("Sales Invoice", batch.sales_invoice):
		return batch.sales_invoice

	settings = frappe.db.get_value(
		"Transport Invoice Settings",
		{"company": batch.company},
		["sales_item", "sales_cost_center", "auto_submit_invoices"],
		as_dict=True,
	)
	if not settings:
		frappe.throw(_("Transport invoicing is not configured for company {0}.").format(batch.company))

	invoice = frappe.new_doc("Sales Invoice")
	invoice.company = batch.company
	invoice.customer = batch.customer
	invoice.posting_date = batch.posting_date
	invoice.set_posting_time = 1
	set_if_has_field(invoice, "custom_transport_billing_batch", batch.name)
	invoice.remarks = _("Monthly transport billing batch {0}: {1} to {2}.").format(
		batch.name, batch.from_date, batch.to_date
	)

	for row in batch.deliveries:
		delivery = frappe.get_doc("Transport Delivery", row.transport_delivery)
		if delivery.sales_invoice:
			frappe.throw(
				_("Delivery {0} is already linked to Sales Invoice {1}.").format(
					delivery.name, delivery.sales_invoice
				)
			)
		quantity = flt(delivery.actual_weight_kg) if delivery.rate_unit == "Per Kg" else 1
		item = invoice.append(
			"items",
			{
				"item_code": settings.sales_item,
				"qty": quantity,
				"rate": delivery.customer_rate,
				"description": _(
					"{0}: Transport to {1}; distance {2}; truck {3}; weight {4} Kg"
				).format(
					delivery.delivery_reference,
					delivery.destination,
					delivery.distance_band,
					delivery.truck_class,
					delivery.actual_weight_kg,
				),
				"cost_center": settings.sales_cost_center,
			},
		)
		set_if_has_field(item, "custom_transport_delivery", delivery.name)

	invoice.set_missing_values()
	invoice.calculate_taxes_and_totals()
	invoice.insert()
	if settings.auto_submit_invoices:
		invoice.submit()

	batch.db_set("sales_invoice", invoice.name, update_modified=False)
	for row in batch.deliveries:
		frappe.db.set_value(
			"Transport Delivery",
			row.transport_delivery,
			{"sales_invoice": invoice.name, "billing_batch": batch.name},
			update_modified=False,
		)

	return invoice.name
