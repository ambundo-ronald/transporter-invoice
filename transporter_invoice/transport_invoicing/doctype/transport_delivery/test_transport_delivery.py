import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from transporter_invoice.transport_invoicing.doctype.transport_delivery.transport_delivery import (
	append_transport_invoice_items,
	get_above_10_truck_class,
	get_invoice_item_description,
	get_invoice_quantity,
)


class _FakeMeta:
	def has_field(self, fieldname):
		return True


class _FakeInvoiceItem(frappe._dict):
	meta = _FakeMeta()

	def set(self, fieldname, value):
		self[fieldname] = value


class _FakeInvoice:
	def __init__(self):
		self.items = []

	def append(self, table_field, values):
		item = _FakeInvoiceItem(values)
		self.items.append(item)
		return item


class TestTransportDelivery(FrappeTestCase):
	def test_delivery_requires_valid_truck_class(self):
		delivery = frappe.new_doc("Transport Delivery")
		delivery.truck_class = "7 MT"
		delivery.actual_weight_kg = 1000

		with self.assertRaises(frappe.ValidationError):
			delivery._validate_delivery_details()

	def test_under_10_delivery_does_not_require_destination_or_km(self):
		delivery = frappe.new_doc("Transport Delivery")
		delivery.rate_category = "Under 10 Tonnes"
		delivery.truck_class = "3 MT"
		delivery.actual_distance_km = 42
		delivery.actual_weight_kg = 1500

		delivery._validate_delivery_details()

		self.assertEqual(delivery.actual_distance_km, 0)

	def test_under_10_quantity_is_prorated_by_total_weight(self):
		delivery = frappe._dict(
			rate_unit="Fixed Trip Amount",
			rate_category="Under 10 Tonnes",
			truck_class="1.5 MT",
			actual_weight_kg=750,
		)

		self.assertEqual(get_invoice_quantity(delivery), 0.5)

		delivery.actual_weight_kg = 1500
		self.assertEqual(get_invoice_quantity(delivery), 1)

	def test_under_10_allows_half_tonne_tolerance(self):
		delivery = frappe.new_doc("Transport Delivery")
		delivery.rate_category = "Under 10 Tonnes"
		delivery.truck_class = "1.5 MT"
		delivery.actual_weight_kg = 2000

		delivery._validate_delivery_details()

		self.assertEqual(get_invoice_quantity(delivery), 1)

		delivery.actual_weight_kg = 2000.01
		with self.assertRaises(frappe.ValidationError):
			delivery._validate_delivery_details()

	def test_under_10_trip_rows_are_copied_to_invoice_items(self):
		delivery = frappe._dict(
			name="TD-TEST-0002",
			delivery_reference="LOAD-22",
			rate_unit="Fixed Trip Amount",
			rate_category="Under 10 Tonnes",
			destination="",
			truck_class="1.5 MT",
			vehicle_registration="KAA 123A",
			actual_distance_km=0,
			actual_weight_kg=1500,
			customer_amount=7800,
			transporter_amount=6100,
			under_10_trips=[
				frappe._dict(
					trip_reference="TRIP-1",
					destination="Thika Town",
					truck_no="KBA 001A",
					weight_kg=500,
				),
				frappe._dict(
					trip_reference="TRIP-2",
					destination="Ruiru",
					truck_no="KBA 002A",
					weight_kg=1000,
				),
			],
		)
		invoice = _FakeInvoice()

		append_transport_invoice_items(invoice, delivery, "Transport services", "Main - TC", True)

		self.assertEqual(len(invoice.items), 2)
		self.assertEqual(invoice.items[0].custom_transport_delivery, "TD-TEST-0002")
		self.assertEqual(invoice.items[0].custom_trip_reference, "TRIP-1")
		self.assertEqual(invoice.items[0].custom_destination, "Thika Town")
		self.assertEqual(invoice.items[0].custom_truck_no, "KBA 001A")
		self.assertEqual(invoice.items[0].custom_truck_type, "1.5 MT")
		self.assertEqual(invoice.items[0].custom_net_weight_kg, 500)
		self.assertAlmostEqual(invoice.items[0].rate, 2600)
		self.assertAlmostEqual(invoice.items[1].rate, 5200)
		self.assertAlmostEqual(sum(item.rate for item in invoice.items), delivery.customer_amount)

	def test_above_10_delivery_uses_weight_for_truck_class_without_km(self):
		delivery = frappe.new_doc("Transport Delivery")
		delivery.rate_category = "10 Tonnes and Above"
		delivery.destination = "Thika Town"
		delivery.actual_weight_kg = 12000

		delivery._validate_delivery_details()

		self.assertEqual(delivery.truck_class, "14 MT")

	def test_above_10_truck_class_from_weight(self):
		self.assertEqual(get_above_10_truck_class(10000), "10 MT")
		self.assertEqual(get_above_10_truck_class(14000), "14 MT")
		self.assertEqual(get_above_10_truck_class(20000), "Trailer")

	def test_above_10_fixed_quantity_is_one(self):
		delivery = frappe._dict(
			rate_unit="Fixed Trip Amount",
			rate_category="10 Tonnes and Above",
			truck_class="10 MT",
			actual_distance_km=80,
		)

		self.assertEqual(get_invoice_quantity(delivery), 1)

	def test_invoice_description_uses_delivery_id_before_external_reference(self):
		delivery = frappe._dict(
			name="TD-TEST-0001",
			delivery_reference="WAYBILL-77",
			rate_unit="Fixed Trip Amount",
			destination="",
			truck_class="3 MT",
			vehicle_registration="KAA 123A",
		)

		description = get_invoice_item_description(delivery, include_reference=True)

		self.assertTrue(description.startswith("TD-TEST-0001: Ref WAYBILL-77:"))
	def test_rate_card_rejects_duplicate_location(self):
		card = frappe.new_doc("Transport Rate Card")
		card.company = "_Test Company"
		card.customer = "_Test Customer"
		card.rate_category = "10 Tonnes and Above"
		card.effective_from = add_days(nowdate(), 1000)
		card.append(
			"rates",
			{
				"distance_band": "0-25 KMs",
				"location": "Thika Town",
				"customer_10mt_rate": 1.05,
				"transporter_10_13mt_rate": 0.84,
			},
		)
		card.append(
			"rates",
			{
				"distance_band": "0-25 KMs",
				"location": "thika town",
				"customer_10mt_rate": 1.05,
				"transporter_10_13mt_rate": 0.84,
			},
		)

		with self.assertRaises(frappe.ValidationError):
			card._validate_rates()

	def test_under_10_rate_card_rejects_duplicate_capacity(self):
		card = frappe.new_doc("Transport Rate Card")
		card.company = "_Test Company"
		card.rate_category = "Under 10 Tonnes"
		card.effective_from = add_days(nowdate(), 1000)
		card.append(
			"rates",
			{
				"truck_capacity": "3 MT",
				"under_10_customer_rate": 8200,
				"under_10_transporter_rate": 6800,
			},
		)
		card.append(
			"rates",
			{
				"truck_capacity": "3 MT",
				"under_10_customer_rate": 8500,
				"under_10_transporter_rate": 7000,
			},
		)

		with self.assertRaises(frappe.ValidationError):
			card._validate_rates()
