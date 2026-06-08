import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class TransportRateCard(Document):
	def validate(self):
		self.route = (self.route or "").strip()
		self._validate_configured_company()
		self._validate_dates()
		self._validate_rates()
		self._validate_overlapping_card()

	def _validate_configured_company(self):
		configured_company = frappe.db.get_value("Transport Invoice Settings", {}, "company")
		if not configured_company:
			frappe.throw(_("Create Transport Invoice Settings before creating a rate card."))
		if self.company != configured_company:
			frappe.throw(
				_("Transport invoicing is restricted to company {0}.").format(
					frappe.bold(configured_company)
				)
			)

	def _validate_dates(self):
		if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
			frappe.throw(_("Effective To cannot be before Effective From."))

	def _validate_rates(self):
		if not self.rates:
			frappe.throw(_("Add at least one transport rate."))

		seen_capacities = set()
		for row in self.rates:
			capacity = flt(row.capacity_tonnes, 2)
			if capacity <= 0 or capacity >= 10:
				frappe.throw(
					_("Row {0}: capacity must be greater than 0 and less than 10 tonnes.").format(
						row.idx
					)
				)
			if capacity in seen_capacities:
				frappe.throw(_("Capacity {0} tonnes is listed more than once.").format(capacity))
			if flt(row.customer_rate) <= 0 or flt(row.transporter_rate) <= 0:
				frappe.throw(_("Row {0}: both rates must be greater than zero.").format(row.idx))
			if flt(row.customer_rate) < flt(row.transporter_rate):
				frappe.throw(
					_("Row {0}: customer rate cannot be below the transporter rate.").format(row.idx)
				)

			row.margin = flt(row.customer_rate) - flt(row.transporter_rate)
			seen_capacities.add(capacity)

	def _validate_overlapping_card(self):
		filters = {
			"company": self.company,
			"customer": self.customer,
			"route": self.route or "",
			"docstatus": ["<", 2],
			"name": ["!=", self.name],
			"effective_from": ["<=", self.effective_to or "9999-12-31"],
		}
		candidates = frappe.get_all(
			"Transport Rate Card",
			filters=filters,
			fields=["name", "effective_to"],
		)
		for card in candidates:
			if not card.effective_to or getdate(card.effective_to) >= getdate(self.effective_from):
				frappe.throw(
					_("Rate card {0} overlaps this company, customer, route, and date range.").format(
						frappe.bold(card.name)
					)
				)
