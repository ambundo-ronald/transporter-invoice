import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

class TestTransportDelivery(FrappeTestCase):
	def test_capacity_at_or_above_ten_is_rejected(self):
		delivery = frappe.new_doc("Transport Delivery")
		delivery.capacity_tonnes = 10

		with self.assertRaises(frappe.ValidationError):
			delivery._validate_capacity()

	def test_rate_card_rejects_duplicate_capacity(self):
		card = frappe.new_doc("Transport Rate Card")
		card.company = "_Test Company"
		card.customer = "_Test Customer"
		card.effective_from = add_days(nowdate(), 1000)
		card.append(
			"rates",
			{"capacity_tonnes": 3, "customer_rate": 8200, "transporter_rate": 6800},
		)
		card.append(
			"rates",
			{"capacity_tonnes": 3, "customer_rate": 8500, "transporter_rate": 7000},
		)

		with self.assertRaises(frappe.ValidationError):
			card._validate_rates()
