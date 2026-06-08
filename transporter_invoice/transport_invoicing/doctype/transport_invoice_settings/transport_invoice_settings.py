import frappe
from frappe import _
from frappe.model.document import Document


class TransportInvoiceSettings(Document):
	def validate(self):
		self._validate_single_company_configuration()
		self._validate_items()
		self._validate_cost_centers()

	def _validate_single_company_configuration(self):
		existing = frappe.db.get_value(
			"Transport Invoice Settings",
			{"name": ["!=", self.name]},
			"name",
		)
		if existing:
			frappe.throw(
				_(
					"This app is restricted to one company. Settings already exists for {0}."
				).format(frappe.bold(existing))
			)

	def _validate_items(self):
		for fieldname in ("sales_item", "purchase_item"):
			item_code = self.get(fieldname)
			if not item_code:
				continue

			disabled, is_stock_item = frappe.db.get_value(
				"Item", item_code, ["disabled", "is_stock_item"]
			)
			if disabled:
				frappe.throw(
					_("{0} cannot use disabled Item {1}.").format(
						self.meta.get_label(fieldname), frappe.bold(item_code)
					)
				)
			if is_stock_item:
				frappe.throw(
					_("{0} must be a non-stock service Item.").format(
						self.meta.get_label(fieldname)
					)
				)

	def _validate_cost_centers(self):
		for fieldname in ("sales_cost_center", "purchase_cost_center"):
			cost_center = self.get(fieldname)
			if not cost_center:
				continue

			cost_center_company = frappe.db.get_value("Cost Center", cost_center, "company")
			if cost_center_company != self.company:
				frappe.throw(
					_("{0} must belong to company {1}.").format(
						self.meta.get_label(fieldname), frappe.bold(self.company)
					)
				)
