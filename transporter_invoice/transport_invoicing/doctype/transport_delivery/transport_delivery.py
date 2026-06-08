import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class TransportDelivery(Document):
	def validate(self):
		self.route = (self.route or "").strip()
		self._validate_configured_company()
		self._validate_capacity()
		self._validate_parties()
		self._apply_rate()
		self._validate_linked_invoices()

	def before_submit(self):
		if not self.proof_of_delivery:
			frappe.throw(_("Attach proof of delivery before submitting."))

	def on_cancel(self):
		active_invoices = []
		for doctype, invoice_name in (
			("Sales Invoice", self.sales_invoice),
			("Purchase Invoice", self.purchase_invoice),
		):
			if invoice_name and frappe.db.get_value(doctype, invoice_name, "docstatus") != 2:
				active_invoices.append(invoice_name)

		if active_invoices:
			frappe.throw(
				_("Cancel the linked invoices before cancelling this delivery: {0}").format(
					", ".join(active_invoices)
				)
			)

	def _validate_capacity(self):
		capacity = flt(self.capacity_tonnes, 2)
		if capacity <= 0 or capacity >= 10:
			frappe.throw(_("This rate workflow only supports capacities below 10 tonnes."))

	def _validate_configured_company(self):
		configured_company = frappe.db.get_value("Transport Invoice Settings", {}, "company")
		if not configured_company:
			frappe.throw(_("Create Transport Invoice Settings before creating deliveries."))
		if self.company != configured_company:
			frappe.throw(
				_("Transport invoicing is restricted to company {0}.").format(
					frappe.bold(configured_company)
				)
			)

	def _validate_parties(self):
		if frappe.db.get_value("Customer", self.customer, "disabled"):
			frappe.throw(_("Customer {0} is disabled.").format(frappe.bold(self.customer)))
		if frappe.db.get_value("Supplier", self.transporter, "disabled"):
			frappe.throw(_("Transporter {0} is disabled.").format(frappe.bold(self.transporter)))

	def _apply_rate(self):
		if self.docstatus == 1:
			return

		rate = get_applicable_rate(
			company=self.company,
			customer=self.customer,
			delivery_date=self.delivery_date,
			capacity_tonnes=self.capacity_tonnes,
			route=self.route,
		)
		self.rate_card = rate.rate_card
		self.rate_row = rate.rate_row
		self.customer_rate = rate.customer_rate
		self.transporter_rate = rate.transporter_rate
		self.margin = flt(rate.customer_rate) - flt(rate.transporter_rate)

	def _validate_linked_invoices(self):
		for doctype, invoice_name in (
			("Sales Invoice", self.sales_invoice),
			("Purchase Invoice", self.purchase_invoice),
		):
			if not invoice_name:
				continue
			invoice_company = frappe.db.get_value(doctype, invoice_name, "company")
			if invoice_company != self.company:
				frappe.throw(
					_("{0} {1} belongs to company {2}, not {3}.").format(
						doctype,
						frappe.bold(invoice_name),
						frappe.bold(invoice_company),
						frappe.bold(self.company),
					)
				)


@frappe.whitelist()
def get_applicable_rate(company, customer, delivery_date, capacity_tonnes, route=None):
	if not all((company, customer, delivery_date, capacity_tonnes)):
		frappe.throw(_("Company, customer, delivery date, and capacity are required."))

	configured_company = frappe.db.get_value("Transport Invoice Settings", {}, "company")
	if not configured_company:
		frappe.throw(_("Create Transport Invoice Settings before looking up rates."))
	if company != configured_company:
		frappe.throw(
			_("Transport invoicing is restricted to company {0}.").format(
				frappe.bold(configured_company)
			)
		)

	capacity = flt(capacity_tonnes, 2)
	if capacity <= 0 or capacity >= 10:
		frappe.throw(_("This rate workflow only supports capacities below 10 tonnes."))

	card_filters = {
		"company": company,
		"customer": customer,
		"docstatus": 1,
		"effective_from": ["<=", getdate(delivery_date)],
	}
	cards = frappe.get_list(
		"Transport Rate Card",
		filters=card_filters,
		or_filters=[
			["effective_to", "is", "not set"],
			["effective_to", ">=", getdate(delivery_date)],
		],
		fields=["name", "route", "effective_from"],
		order_by="effective_from desc",
	)

	route = (route or "").strip()
	matching_cards = [
		card for card in cards if (card.route or "").strip() == route
	]
	if not matching_cards and route:
		matching_cards = [card for card in cards if not (card.route or "").strip()]

	for card in matching_cards:
		rate = frappe.db.get_value(
			"Transport Rate",
			{
				"parent": card.name,
				"parenttype": "Transport Rate Card",
				"capacity_tonnes": capacity,
			},
			["name", "customer_rate", "transporter_rate"],
			as_dict=True,
		)
		if rate:
			return frappe._dict(
				rate_card=card.name,
				rate_row=rate.name,
				customer_rate=rate.customer_rate,
				transporter_rate=rate.transporter_rate,
			)

	frappe.throw(
		_(
			"No submitted rate was found for company {0}, customer {1}, delivery date {2}, "
			"route {3}, and capacity {4} tonnes."
		).format(
			frappe.bold(company),
			frappe.bold(customer),
			frappe.bold(delivery_date),
			frappe.bold(route or "General"),
			frappe.bold(capacity),
		)
	)


@frappe.whitelist()
def create_sales_invoice(delivery_name):
	return _create_invoice(delivery_name, "Sales Invoice")


@frappe.whitelist()
def create_purchase_invoice(delivery_name):
	return _create_invoice(delivery_name, "Purchase Invoice")


@frappe.whitelist()
def create_both_invoices(delivery_name):
	sales_invoice = _create_invoice(delivery_name, "Sales Invoice")
	purchase_invoice = _create_invoice(delivery_name, "Purchase Invoice")
	return {
		"sales_invoice": sales_invoice,
		"purchase_invoice": purchase_invoice,
	}


def _create_invoice(delivery_name, invoice_doctype):
	# Serialize invoice creation for this delivery so concurrent clicks cannot create duplicates.
	frappe.db.sql(
		"select name from `tabTransport Delivery` where name = %s for update",
		delivery_name,
	)
	delivery = frappe.get_doc("Transport Delivery", delivery_name)
	delivery.check_permission("write")
	if delivery.docstatus != 1:
		frappe.throw(_("Submit the Transport Delivery before creating invoices."))

	is_sales = invoice_doctype == "Sales Invoice"
	link_field = "sales_invoice" if is_sales else "purchase_invoice"
	existing_invoice = delivery.get(link_field)
	if existing_invoice:
		if frappe.db.exists(invoice_doctype, existing_invoice):
			return existing_invoice
		delivery.db_set(link_field, None, update_modified=False)

	settings = frappe.db.get_value(
		"Transport Invoice Settings",
		{"company": delivery.company},
		[
			"name",
			"sales_item",
			"purchase_item",
			"sales_cost_center",
			"purchase_cost_center",
			"auto_submit_invoices",
		],
		as_dict=True,
	)
	if not settings:
		frappe.throw(
			_("Transport invoicing is not configured for company {0}.").format(
				frappe.bold(delivery.company)
			)
		)

	item_code = settings.sales_item if is_sales else settings.purchase_item
	cost_center = settings.sales_cost_center if is_sales else settings.purchase_cost_center
	rate = delivery.customer_rate if is_sales else delivery.transporter_rate
	party_field = "customer" if is_sales else "supplier"
	party = delivery.customer if is_sales else delivery.transporter

	invoice = frappe.new_doc(invoice_doctype)
	invoice.company = delivery.company
	invoice.posting_date = delivery.delivery_date
	invoice.set_posting_time = 1
	invoice.set(party_field, party)
	invoice.remarks = _("Created from Transport Delivery {0} ({1}).").format(
		delivery.name, delivery.delivery_reference
	)
	invoice.append(
		"items",
		{
			"item_code": item_code,
			"qty": 1,
			"rate": rate,
			"description": _(
				"Transport delivery {0}; {1} tonnes; vehicle {2}; route {3}"
			).format(
				delivery.delivery_reference,
				delivery.capacity_tonnes,
				delivery.vehicle_registration or "-",
				delivery.route or "General",
			),
			"cost_center": cost_center,
		},
	)
	invoice.set_missing_values()
	invoice.calculate_taxes_and_totals()
	invoice.insert()
	if settings.auto_submit_invoices:
		invoice.submit()

	delivery.db_set(link_field, invoice.name, update_modified=False)
	return invoice.name
