import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from transporter_invoice.transport_invoicing.invoice_links import set_if_has_field


TRUCK_RATE_FIELDS = {
	"10 MT": ("customer_10mt_rate", "transporter_10_13mt_rate"),
	"14 MT": ("customer_14mt_rate", "transporter_14_17mt_rate"),
	"Trailer": ("customer_trailer_rate", "transporter_28mt_rate"),
}
UNDER_10_TRUCK_CLASSES = {"1.5 MT", "3 MT", "5 MT", "7 MT"}
ABOVE_10_TRUCK_CLASSES = set(TRUCK_RATE_FIELDS)


class TransportDelivery(Document):
	def validate(self):
		self.destination = (self.destination or "").strip()
		self._validate_configured_company()
		self._validate_delivery_details()
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

	def _validate_delivery_details(self):
		if self.rate_category not in {"Under 10 Tonnes", "10 Tonnes and Above"}:
			frappe.throw(_("Select a valid rate category."))
		if self.rate_category == "Under 10 Tonnes":
			if self.truck_class not in UNDER_10_TRUCK_CLASSES:
				frappe.throw(_("Under 10 Tonnes deliveries must use 1.5 MT, 3 MT, 5 MT, or 7 MT."))
			self.actual_distance_km = 0
		if self.rate_category == "10 Tonnes and Above":
			if self.truck_class not in ABOVE_10_TRUCK_CLASSES:
				frappe.throw(_("10 Tonnes and Above deliveries must use 10 MT, 14 MT, or Trailer."))
			if not self.destination:
				frappe.throw(_("Destination is required for 10 Tonnes and Above route matrix deliveries."))
			if flt(self.actual_distance_km) <= 0:
				frappe.throw(_("Actual Distance (KM) must be greater than zero for above-10-tonne deliveries."))
		if self.truck_class not in UNDER_10_TRUCK_CLASSES | ABOVE_10_TRUCK_CLASSES:
			frappe.throw(_("Select a valid truck class."))

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
			transporter=self.transporter,
			delivery_date=self.delivery_date,
			destination=self.destination,
			rate_category=self.rate_category,
			truck_class=self.truck_class,
			actual_distance_km=self.actual_distance_km,
		)
		self.rate_card = rate.rate_card
		self.rate_row = rate.rate_row
		self.distance_band = rate.distance_band
		self.rate_unit = rate.rate_unit
		self.customer_rate = rate.customer_rate
		self.transporter_rate = rate.transporter_rate

		quantity = flt(self.actual_distance_km) if rate.rate_unit == "Per Km" else 1
		self.customer_amount = quantity * flt(rate.customer_rate)
		self.transporter_amount = quantity * flt(rate.transporter_rate)
		self.margin = flt(self.customer_amount) - flt(self.transporter_amount)

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
def get_applicable_rate(company, customer, transporter, delivery_date, destination, rate_category, truck_class, actual_distance_km=None):
	if not all((company, customer, transporter, delivery_date, rate_category, truck_class)):
		frappe.throw(
			_("Company, customer, transporter, delivery date, rate category, and truck class are required.")
		)

	configured_company = frappe.db.get_value("Transport Invoice Settings", {}, "company")
	if not configured_company:
		frappe.throw(_("Create Transport Invoice Settings before looking up rates."))
	if company != configured_company:
		frappe.throw(
			_("Transport invoicing is restricted to company {0}.").format(
				frappe.bold(configured_company)
			)
		)
	if rate_category == "Under 10 Tonnes" and truck_class not in UNDER_10_TRUCK_CLASSES:
		frappe.throw(_("Under 10 Tonnes deliveries must use 1.5 MT, 3 MT, 5 MT, or 7 MT."))
	if rate_category == "10 Tonnes and Above" and truck_class not in ABOVE_10_TRUCK_CLASSES:
		frappe.throw(_("10 Tonnes and Above deliveries must use 10 MT, 14 MT, or Trailer."))
	if rate_category == "10 Tonnes and Above" and not (destination or "").strip():
		frappe.throw(_("Destination is required for 10 Tonnes and Above route matrix rates."))
	if rate_category == "10 Tonnes and Above" and flt(actual_distance_km) <= 0:
		frappe.throw(_("Actual Distance (KM) must be greater than zero for above-10-tonne rates."))

	cards = frappe.get_list(
		"Transport Rate Card",
		filters={
			"company": company,
			"rate_category": rate_category,
			"docstatus": 1,
			"effective_from": ["<=", getdate(delivery_date)],
		},
		or_filters=[
			["effective_to", "is", "not set"],
			["effective_to", ">=", getdate(delivery_date)],
		],
		fields=["name", "customer", "transporter", "rate_unit", "effective_from"],
		order_by="effective_from desc",
	)
	cards = [
		card
		for card in cards
		if (not card.customer or card.customer == customer)
		and (not card.transporter or card.transporter == transporter)
	]
	cards.sort(
		key=lambda card: (
			1 if card.customer == customer else 0,
			1 if card.transporter == transporter else 0,
			getdate(card.effective_from),
		),
		reverse=True,
	)

	if rate_category == "Under 10 Tonnes":
		return _get_under_10_rate(cards, truck_class)

	return _get_above_10_rate(cards, destination, truck_class, delivery_date, actual_distance_km)


def _get_under_10_rate(cards, truck_class):
	for card in cards:
		rate = frappe.db.get_value(
			"Transport Rate",
			{
				"parent": card.name,
				"parenttype": "Transport Rate Card",
				"truck_capacity": truck_class,
			},
			[
				"name",
				"distance_band",
				"location",
				"under_10_customer_rate",
				"under_10_transporter_rate",
			],
			as_dict=True,
		)
		if rate:
			customer_rate = flt(rate.under_10_customer_rate)
			transporter_rate = flt(rate.under_10_transporter_rate)
			return frappe._dict(
				rate_card=card.name,
				rate_row=rate.name,
				distance_band=rate.distance_band,
				rate_unit="Fixed Trip Amount",
				customer_rate=customer_rate,
				transporter_rate=transporter_rate,
			)

	frappe.throw(
		_("No submitted under-10 rate was found for {0}.").format(frappe.bold(truck_class))
	)


def _get_above_10_rate(cards, destination, truck_class, delivery_date, actual_distance_km):
	destination_key = destination.strip().casefold()
	actual_distance = flt(actual_distance_km)
	customer_field, transporter_field = TRUCK_RATE_FIELDS[truck_class]
	for card in cards:
		rows = frappe.get_all(
			"Transport Rate",
			filters={"parent": card.name, "parenttype": "Transport Rate Card"},
			fields=["name", "distance_band", "from_km", "to_km", "location", customer_field, transporter_field],
			order_by="idx asc",
		)
		for row in rows:
			if (row.location or "").strip().casefold() != destination_key:
				continue
			if actual_distance < flt(row.from_km):
				continue
			if row.to_km and actual_distance > flt(row.to_km):
				continue
			customer_rate = flt(row.get(customer_field))
			transporter_rate = flt(row.get(transporter_field))
			if not customer_rate or not transporter_rate:
				frappe.throw(
					_("Rates for {0} and {1} are missing on rate card {2}.").format(
						frappe.bold(destination),
						frappe.bold(truck_class),
						frappe.bold(card.name),
					)
				)
			return frappe._dict(
				rate_card=card.name,
				rate_row=row.name,
				distance_band=row.distance_band,
				rate_unit=card.rate_unit,
				customer_rate=customer_rate,
				transporter_rate=transporter_rate,
			)

	frappe.throw(
		_("No submitted above-10 route rate was found for {0}, {1}, on {2}.").format(
			frappe.bold(destination),
			frappe.bold(truck_class),
			frappe.bold(delivery_date),
		)
	)


@frappe.whitelist()
def create_sales_invoice(delivery_name):
	"""Create a one-off customer invoice.

	For monthly billing, use Transport Billing Batch instead.
	"""
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
	quantity = flt(delivery.actual_distance_km) if delivery.rate_unit == "Per Km" else 1

	invoice = frappe.new_doc(invoice_doctype)
	invoice.company = delivery.company
	invoice.posting_date = delivery.delivery_date
	invoice.set_posting_time = 1
	invoice.set(party_field, party)
	set_if_has_field(invoice, "custom_transport_delivery", delivery.name)
	invoice.remarks = _("Created from Transport Delivery {0}.").format(delivery.name)
	if delivery.delivery_reference:
		invoice.remarks += " " + _("External Reference: {0}.").format(delivery.delivery_reference)
	item = invoice.append(
		"items",
		{
			"item_code": item_code,
			"qty": quantity,
			"rate": rate,
			"description": get_invoice_item_description(delivery),
			"cost_center": cost_center,
		},
	)
	set_if_has_field(item, "custom_transport_delivery", delivery.name)
	invoice.set_missing_values()
	invoice.calculate_taxes_and_totals()
	invoice.insert()
	if settings.auto_submit_invoices:
		invoice.submit()

	delivery.db_set(link_field, invoice.name, update_modified=False)
	return invoice.name


def get_invoice_item_description(delivery, include_reference=False):
	prefix = ""
	if include_reference:
		prefix = _("{0}: ").format(delivery.name)
		if delivery.delivery_reference:
			prefix += _("Ref {0}: ").format(delivery.delivery_reference)

	vehicle = delivery.vehicle_registration or "-"
	if delivery.rate_unit == "Per Km":
		return prefix + _(
			"Transport to {0}; band {1}; actual distance {2} KM; truck {3}; vehicle {4}"
		).format(
			delivery.destination or "-",
			delivery.distance_band or "-",
			delivery.actual_distance_km,
			delivery.truck_class,
			vehicle,
		)

	destination = (delivery.destination or "").strip()
	delivery_label = _("Transport fixed small-truck trip")
	if destination:
		delivery_label = _("{0} to {1}").format(delivery_label, destination)

	return prefix + _("{0}; truck {1}; vehicle {2}").format(
		delivery_label,
		delivery.truck_class,
		vehicle,
	)
