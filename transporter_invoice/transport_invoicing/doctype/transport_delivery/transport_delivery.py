import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate

from transporter_invoice.transport_invoicing.invoice_links import set_if_has_field
from transporter_invoice.transport_invoicing.invoice_permissions import transport_invoice_permission_context


TRUCK_RATE_FIELDS = {
	"10 MT": ("customer_10mt_rate", "transporter_10_13mt_rate"),
	"14 MT": ("customer_14mt_rate", "transporter_14_17mt_rate"),
	"Trailer": ("customer_trailer_rate", "transporter_28mt_rate"),
}
UNDER_10_TRUCK_CLASSES = {"1.5 MT", "3 MT", "5 MT", "7 MT"}
UNDER_10_CAPACITY_KG = {
	"1.5 MT": 1500,
	"3 MT": 3000,
	"5 MT": 5000,
	"7 MT": 7000,
}
ABOVE_10_CAPACITY_KG = {
	"10 MT": 10000,
	"14 MT": 14000,
	"Trailer": 28000,
}
ABOVE_10_TRUCK_CLASSES = set(TRUCK_RATE_FIELDS)
ABOVE_10_HEADER_TRUCK_CLASSES = ABOVE_10_TRUCK_CLASSES | {"Mixed"}


class TransportDelivery(Document):
	def validate(self):
		self.destination = (self.destination or "").strip()
		self._validate_configured_company()
		self._validate_delivery_details()
		self._validate_parties()
		self._apply_rate()
		self._validate_linked_invoices()

	def on_cancel(self):
		submitted_invoices = []
		for doctype, fieldname, invoice_name in (
			("Sales Invoice", "sales_invoice", self.sales_invoice),
			("Purchase Invoice", "purchase_invoice", self.purchase_invoice),
		):
			if not invoice_name:
				continue

			docstatus = frappe.db.get_value(doctype, invoice_name, "docstatus")
			if docstatus is None:
				self.db_set(fieldname, None, update_modified=False)
				continue

			if cint(docstatus) == 1:
				submitted_invoices.append(invoice_name)
			elif cint(docstatus) == 0:
				_unlink_draft_invoice(doctype, invoice_name)
				self.db_set(fieldname, None, update_modified=False)

		if submitted_invoices:
			frappe.throw(
				_("Cancel the submitted linked invoices before cancelling this delivery: {0}").format(
					", ".join(submitted_invoices)
				)
			)

	def _validate_delivery_details(self):
		if self.rate_category not in {"Under 10 Tonnes", "10 Tonnes and Above"}:
			frappe.throw(_("Select a valid rate category."))
		if self.rate_category == "Under 10 Tonnes":
			if self.truck_class not in UNDER_10_TRUCK_CLASSES:
				frappe.throw(_("Under 10 Tonnes deliveries must use 1.5 MT, 3 MT, 5 MT, or 7 MT."))
			self._set_under_10_trip_weight()
			self._validate_under_10_weight()
			self.actual_distance_km = 0
		if self.rate_category == "10 Tonnes and Above":
			self._set_above_10_trip_details()
		if self.truck_class not in UNDER_10_TRUCK_CLASSES | ABOVE_10_HEADER_TRUCK_CLASSES:
			frappe.throw(_("Select a valid truck class."))

	def _set_under_10_trip_weight(self):
		total_weight = 0
		for row in self.get("under_10_trips") or []:
			if flt(row.weight_kg) <= 0:
				frappe.throw(_("Weight (KG) must be greater than zero for every under-10 trip row."))
			total_weight += flt(row.weight_kg)

		if total_weight:
			self.actual_weight_kg = total_weight

	def _validate_under_10_weight(self):
		total_weight = flt(self.actual_weight_kg)
		if total_weight <= 0:
			frappe.throw(_("Actual Weight (Kg) is required for under-10 deliveries. Add trip rows or enter the total weight."))

		capacity = UNDER_10_CAPACITY_KG.get(self.truck_class)
		if capacity and total_weight > capacity:
			frappe.throw(
				_("Total under-10 trip weight {0} KG is above the selected truck class capacity of {1} KG. Select a larger truck class.").format(
					total_weight,
					capacity,
				)
			)

	def _set_above_10_trip_details(self):
		trip_rows = self.get("above_10_trips") or []
		if trip_rows:
			truck_classes = set()
			total_weight = 0
			for row in trip_rows:
				row.destination = (row.destination or "").strip()
				if not row.destination:
					frappe.throw(_("Row {0}: Destination is required for above-10 trip rows.").format(row.idx))
				if flt(row.weight_kg) <= 0:
					frappe.throw(_("Row {0}: Weight (KG) must be greater than zero for above-10 trip rows.").format(row.idx))
				row.truck_class = get_above_10_truck_class(row.weight_kg)
				truck_classes.add(row.truck_class)
				total_weight += flt(row.weight_kg)

			self.actual_weight_kg = total_weight
			self.truck_class = truck_classes.pop() if len(truck_classes) == 1 else "Mixed"
			if len(trip_rows) == 1:
				self.destination = trip_rows[0].destination
			return

		if not self.destination:
			frappe.throw(_("Destination is required for 10 Tonnes and Above deliveries."))
		if flt(self.actual_weight_kg) <= 0:
			frappe.throw(_("Actual Weight (Kg) is required for 10 Tonnes and Above deliveries."))
		self.truck_class = get_above_10_truck_class(self.actual_weight_kg)

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

		if self.rate_category == "10 Tonnes and Above" and self.get("above_10_trips"):
			self._apply_above_10_trip_rates()
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

		quantity = get_invoice_quantity(self)
		self.customer_amount = quantity * flt(rate.customer_rate)
		self.transporter_amount = quantity * flt(rate.transporter_rate)
		self.margin = flt(self.customer_amount) - flt(self.transporter_amount)

	def _apply_above_10_trip_rates(self):
		self.customer_amount = 0
		self.transporter_amount = 0
		self.customer_rate = 0
		self.transporter_rate = 0
		self.rate_unit = "Fixed Trip Amount"
		rate_cards = set()
		distance_bands = set()
		for row in self.get("above_10_trips") or []:
			rate = get_applicable_rate(
				company=self.company,
				customer=self.customer,
				transporter=self.transporter,
				delivery_date=self.delivery_date,
				destination=row.destination,
				rate_category=self.rate_category,
				truck_class=row.truck_class,
			)
			row.rate_card = rate.rate_card
			row.rate_row = rate.rate_row
			row.distance_band = rate.distance_band
			row.customer_rate = rate.customer_rate
			row.transporter_rate = rate.transporter_rate
			row.customer_amount = flt(rate.customer_rate)
			row.transporter_amount = flt(rate.transporter_rate)
			self.customer_amount += flt(row.customer_amount)
			self.transporter_amount += flt(row.transporter_amount)
			rate_cards.add(rate.rate_card)
			distance_bands.add(rate.distance_band)

		self.rate_card = next(iter(rate_cards)) if len(rate_cards) == 1 else None
		self.rate_row = None
		self.distance_band = next(iter(distance_bands)) if len(distance_bands) == 1 else "Multiple"
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

	return _get_above_10_rate(cards, destination, truck_class, delivery_date)


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


def _get_above_10_rate(cards, destination, truck_class, delivery_date):
	destination_key = destination.strip().casefold()
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
				rate_unit="Fixed Trip Amount",
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
def get_route_location_options(company, delivery_date=None, customer=None, transporter=None, rate_category="10 Tonnes and Above"):
	if not company:
		return []

	filters = {"company": company, "rate_category": rate_category, "docstatus": 1}
	or_filters = None
	if delivery_date:
		filters["effective_from"] = ["<=", getdate(delivery_date)]
		or_filters = [
			["effective_to", "is", "not set"],
			["effective_to", ">=", getdate(delivery_date)],
		]

	cards = frappe.get_list(
		"Transport Rate Card",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "customer", "transporter", "effective_from"],
		order_by="effective_from desc",
	)
	cards = [
		card
		for card in cards
		if (not card.customer or card.customer == customer)
		and (not card.transporter or card.transporter == transporter)
	]
	if not cards:
		return []

	locations = frappe.get_all(
		"Transport Rate",
		filters={"parent": ["in", [card.name for card in cards]], "parenttype": "Transport Rate Card"},
		fields=["location"],
		order_by="location asc",
	)
	seen = set()
	options = []
	for row in locations:
		location = (row.location or "").strip()
		location_key = location.casefold()
		if not location or location_key in seen:
			continue
		seen.add(location_key)
		options.append(location)
	return options


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


def _unlink_draft_invoice(doctype, invoice_name):
	if frappe.get_meta(doctype).has_field("custom_transport_delivery"):
		frappe.db.set_value(
			doctype,
			invoice_name,
			"custom_transport_delivery",
			None,
			update_modified=False,
		)

	child_doctype = "Sales Invoice Item" if doctype == "Sales Invoice" else "Purchase Invoice Item"
	if frappe.get_meta(child_doctype).has_field("custom_transport_delivery"):
		frappe.db.set_value(
			child_doctype,
			{"parent": invoice_name},
			"custom_transport_delivery",
			None,
			update_modified=False,
		)


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
	party_field = "customer" if is_sales else "supplier"
	party = delivery.customer if is_sales else delivery.transporter

	invoice = frappe.new_doc(invoice_doctype)
	invoice.company = delivery.company
	invoice.posting_date = delivery.delivery_date
	invoice.set_posting_time = 1
	invoice.set(party_field, party)
	set_if_has_field(invoice, "custom_transport_delivery", delivery.name)
	invoice.remarks = _("Created from Transport Delivery {0}.").format(delivery.name)
	if delivery.delivery_reference:
		invoice.remarks += " " + _("External Reference: {0}.").format(delivery.delivery_reference)
	append_transport_invoice_items(invoice, delivery, item_code, cost_center, is_sales)
	with transport_invoice_permission_context(invoice):
		invoice.set_missing_values()
		invoice.calculate_taxes_and_totals()
		invoice.insert(ignore_permissions=True)
		if settings.auto_submit_invoices:
			invoice.submit()

	delivery.db_set(link_field, invoice.name, update_modified=False)
	return invoice.name


def append_transport_invoice_items(invoice, delivery, item_code, cost_center, is_sales, include_reference=False):
	if delivery.rate_category == "10 Tonnes and Above" and delivery.get("above_10_trips"):
		for row in delivery.get("above_10_trips") or []:
			rate = flt(row.customer_rate) if is_sales else flt(row.transporter_rate)
			item = invoice.append(
				"items",
				{
					"item_code": item_code,
					"qty": 1,
					"rate": rate,
					"description": get_above_10_trip_description(delivery, row, include_reference=include_reference),
					"cost_center": cost_center,
				},
			)
			set_if_has_field(item, "custom_transport_delivery", delivery.name)
			set_invoice_item_transport_details(item, delivery, rate, row=row)
		return

	rate = delivery.customer_rate if is_sales else delivery.transporter_rate
	detail_row = None
	if delivery.rate_category == "Under 10 Tonnes" and delivery.get("under_10_trips"):
		detail_row = delivery.get("under_10_trips")[0]
	item = invoice.append(
		"items",
		{
			"item_code": item_code,
			"qty": get_invoice_quantity(delivery),
			"rate": rate,
			"description": get_invoice_item_description(delivery, include_reference=include_reference),
			"cost_center": cost_center,
		},
	)
	set_if_has_field(item, "custom_transport_delivery", delivery.name)
	set_invoice_item_transport_details(item, delivery, rate, row=detail_row)


def get_invoice_item_description(delivery, include_reference=False):
	prefix = ""
	if include_reference:
		prefix = _("{0}: ").format(delivery.name)
		if delivery.delivery_reference:
			prefix += _("Ref {0}: ").format(delivery.delivery_reference)

	vehicle = delivery.vehicle_registration or "-"
	if delivery.rate_category == "10 Tonnes and Above":
		return prefix + _(
			"Transport to {0}; band {1}; truck {2}; total weight {3} KG; vehicle {4}"
		).format(
			delivery.destination or "-",
			delivery.distance_band or "-",
			delivery.truck_class,
			flt(delivery.actual_weight_kg),
			vehicle,
		)

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

	return prefix + _("{0}; truck {1}; total weight {2} KG; billed quantity {3}; vehicle {4}").format(
		delivery_label,
		delivery.truck_class,
		flt(delivery.actual_weight_kg),
		get_invoice_quantity(delivery),
		vehicle,
	)


def get_above_10_trip_description(delivery, row, include_reference=False):
	prefix = _("{0}: ").format(delivery.name) if include_reference else ""
	if include_reference and delivery.delivery_reference:
		prefix += _("Ref {0}: ").format(delivery.delivery_reference)
	vehicle = row.get("truck_no") or delivery.vehicle_registration or "-"
	return prefix + _("Transport to {0}; band {1}; truck {2}; weight {3} KG; vehicle {4}").format(
		row.destination or "-",
		row.distance_band or "-",
		row.truck_class or "-",
		flt(row.weight_kg),
		vehicle,
	)


def get_invoice_quantity(delivery):
	if delivery.rate_unit == "Per Km" and delivery.rate_category != "10 Tonnes and Above":
		return flt(delivery.actual_distance_km)

	if delivery.rate_category == "Under 10 Tonnes":
		return get_under_10_weight_factor(delivery)

	return 1


def get_above_10_truck_class(weight_kg):
	weight = flt(weight_kg)
	if weight <= 0:
		frappe.throw(_("Weight (KG) must be greater than zero."))
	if weight <= ABOVE_10_CAPACITY_KG["10 MT"]:
		return "10 MT"
	if weight <= ABOVE_10_CAPACITY_KG["14 MT"]:
		return "14 MT"
	if weight <= ABOVE_10_CAPACITY_KG["Trailer"]:
		return "Trailer"
	frappe.throw(_("Weight {0} KG is above the Trailer capacity of {1} KG.").format(weight, ABOVE_10_CAPACITY_KG["Trailer"]))


def get_under_10_weight_factor(delivery):
	capacity = UNDER_10_CAPACITY_KG.get(delivery.truck_class)
	weight = flt(delivery.actual_weight_kg)
	if not capacity or weight <= 0:
		return 1

	return min(weight / capacity, 1)


def set_invoice_item_transport_details(item, delivery, rate, row=None):
	destination = row.get("destination") if row else delivery.destination
	truck_class = row.get("truck_class") if row else delivery.truck_class
	weight_kg = row.get("weight_kg") if row else delivery.actual_weight_kg
	trip_reference = row.get("trip_reference") if row else delivery.delivery_reference
	truck_no = row.get("truck_no") if row else delivery.vehicle_registration
	set_if_has_field(item, "custom_trip_reference", trip_reference)
	set_if_has_field(item, "custom_destination", destination)
	set_if_has_field(item, "custom_truck_no", truck_no)
	set_if_has_field(item, "custom_truck_type", truck_class)
	set_if_has_field(item, "custom_net_weight_kg", flt(weight_kg))
	set_if_has_field(item, "custom_transport_rate", flt(rate))
	set_if_has_field(
		item,
		"custom_km_amount",
		flt(delivery.actual_distance_km) if delivery.rate_unit == "Per Km" else None,
	)
