frappe.listview_settings["Transport Delivery"] = {
	add_fields: ["workflow_state", "sales_invoice", "purchase_invoice", "billing_batch"],
	get_indicator(doc) {
		if (doc.docstatus === 2) {
			return [__("Cancelled"), "red", "docstatus,=,2"];
		}
		if (doc.sales_invoice && doc.purchase_invoice) {
			return [__("Fully Invoiced"), "green"];
		}
		if (doc.sales_invoice) {
			return [__("Customer Billed"), "blue"];
		}
		if (doc.purchase_invoice) {
			return [__("Transporter PI"), "purple"];
		}
		if (doc.docstatus === 1) {
			return [__("Awaiting Billing"), "orange"];
		}
		if (doc.workflow_state === "Pending Vehicle Approval") {
			return [__("Pending Vehicle Approval"), "orange"];
		}
		if (doc.workflow_state === "Vehicle Approved") {
			return [__("Vehicle Approved"), "blue"];
		}
		return [__(doc.workflow_state || "Vehicle Request"), "gray"];
	},
};
