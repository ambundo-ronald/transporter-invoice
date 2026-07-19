import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


RATE_FIELDS = (
	"customer_10mt_rate",
	"customer_14mt_rate",
	"customer_trailer_rate",
	"transporter_10_13mt_rate",
	"transporter_14_17mt_rate",
	"transporter_28mt_rate",
)


class TransportRateCard(Document):
	def validate(self):
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
			frappe.throw(_("Add at least one location and its rates."))

		seen_locations = set()
		for row in self.rates:
			row.distance_band = (row.distance_band or "").strip()
			row.location = (row.location or "").strip()
			if not row.distance_band or not row.location:
				frappe.throw(_("Row {0}: distance and location are required.").format(row.idx))

			location_key = row.location.casefold()
			if location_key in seen_locations:
				frappe.throw(
					_("Location {0} is listed more than once.").format(frappe.bold(row.location))
				)
			seen_locations.add(location_key)

			for fieldname in RATE_FIELDS:
				value = flt(row.get(fieldname))
				if value < 0:
					frappe.throw(
						_("Row {0}: {1} cannot be negative.").format(
							row.idx, row.meta.get_label(fieldname)
						)
					)

			for customer_field, transporter_field in (
				("customer_10mt_rate", "transporter_10_13mt_rate"),
				("customer_14mt_rate", "transporter_14_17mt_rate"),
				("customer_trailer_rate", "transporter_28mt_rate"),
			):
				customer_rate = flt(row.get(customer_field))
				transporter_rate = flt(row.get(transporter_field))
				if bool(customer_rate) != bool(transporter_rate):
					frappe.throw(
						_("Row {0}: customer and transporter rates must both be entered for {1}.").format(
							row.idx, row.meta.get_label(customer_field)
						)
					)
				if customer_rate and customer_rate < transporter_rate:
					frappe.throw(
						_("Row {0}: customer rate cannot be below transporter rate for {1}.").format(
							row.idx, row.meta.get_label(customer_field)
						)
					)

	def _validate_overlapping_card(self):
		candidates = frappe.get_all(
			"Transport Rate Card",
			filters={
				"company": self.company,
				"docstatus": ["<", 2],
				"name": ["!=", self.name],
				"effective_from": ["<=", self.effective_to or "9999-12-31"],
			},
			fields=["name", "customer", "transporter", "effective_to"],
		)
		for card in candidates:
			if (card.customer or "") != (self.customer or ""):
				continue
			if (card.transporter or "") != (self.transporter or ""):
				continue
			if not card.effective_to or getdate(card.effective_to) >= getdate(self.effective_from):
				frappe.throw(
					_("Rate card {0} overlaps this customer/transporter specificity and date range.").format(
						frappe.bold(card.name)
					)
				)
