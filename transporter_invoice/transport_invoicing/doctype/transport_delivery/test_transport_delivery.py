import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from transporter_invoice.transport_invoicing.doctype.transport_delivery.transport_delivery import get_invoice_item_description


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

		delivery._validate_delivery_details()

		self.assertEqual(delivery.actual_distance_km, 0)

	def test_above_10_delivery_requires_destination_and_km(self):
		delivery = frappe.new_doc("Transport Delivery")
		delivery.rate_category = "10 Tonnes and Above"
		delivery.truck_class = "10 MT"

		with self.assertRaises(frappe.ValidationError):
			delivery._validate_delivery_details()

		delivery.destination = "Thika Town"
		with self.assertRaises(frappe.ValidationError):
			delivery._validate_delivery_details()

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
