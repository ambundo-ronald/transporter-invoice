frappe.listview_settings["Transport Delivery"] = {
	add_fields: ["sales_invoice", "purchase_invoice"],
	get_indicator(doc) {
		if (doc.docstatus === 2) {
			return [__("Cancelled"), "red", "docstatus,=,2"];
		}
		if (doc.sales_invoice && doc.purchase_invoice) {
			return [__("Invoiced"), "green"];
		}
		if (doc.docstatus === 1) {
			return [__("Awaiting Invoices"), "orange"];
		}
		return [__("Draft"), "gray", "docstatus,=,0"];
	},
};
