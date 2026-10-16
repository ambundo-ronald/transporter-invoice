frappe.listview_settings["Transport Delivery"] = {
	add_fields: ["workflow_state", "sales_invoice", "purchase_invoice", "billing_batch", "transporter_billing_batch"],
	get_indicator(doc) {
		if (doc.docstatus === 2) {
			return [__("Cancelled"), "red", "docstatus,=,2"];
		}
		if (doc.sales_invoice && doc.purchase_invoice) {
			return [__("Fully Invoiced"), "green", "workflow_state,=,Fully Invoiced"];
		}
		if (doc.sales_invoice) {
			return [__("Customer Invoiced"), "cyan", "workflow_state,=,Customer Invoiced"];
		}
		if (doc.purchase_invoice) {
			return [__("Transporter Invoiced"), "purple", "workflow_state,=,Transporter Invoiced"];
		}
		if (doc.docstatus === 1) {
			return [__("Ready for Invoicing"), "yellow", "workflow_state,=,Ready for Invoicing"];
		}
		if (doc.workflow_state === "Pending Vehicle Approval") {
			return [__("Pending Vehicle Approval"), "orange", "workflow_state,=,Pending Vehicle Approval"];
		}
		if (doc.workflow_state === "Vehicle Approved") {
			return [__("Vehicle Approved"), "blue", "workflow_state,=,Vehicle Approved"];
		}
		return [__("Vehicle Request"), "gray", "workflow_state,=,Vehicle Request"];
	},
};
