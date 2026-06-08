frappe.ui.form.on("Transport Delivery", {
	refresh(frm) {
		set_rate_card_query(frm);

		if (frm.doc.docstatus !== 1) {
			return;
		}

		if (!frm.doc.sales_invoice && !frm.doc.purchase_invoice) {
			frm.add_custom_button(__("Create Both Invoices"), () => {
				call_invoice_method(frm, "create_both_invoices");
			}, __("Create"));
		}
		if (!frm.doc.sales_invoice) {
			frm.add_custom_button(__("Sales Invoice"), () => {
				call_invoice_method(frm, "create_sales_invoice");
			}, __("Create"));
		}
		if (!frm.doc.purchase_invoice) {
			frm.add_custom_button(__("Purchase Invoice"), () => {
				call_invoice_method(frm, "create_purchase_invoice");
			}, __("Create"));
		}
	},

	company(frm) {
		clear_applied_rate(frm);
	},
	customer(frm) {
		clear_applied_rate(frm);
	},
	delivery_date(frm) {
		clear_applied_rate(frm);
	},
	route(frm) {
		clear_applied_rate(frm);
	},
	capacity_tonnes(frm) {
		clear_applied_rate(frm);
	},
});

function set_rate_card_query(frm) {
	frm.set_query("rate_card", () => ({
		filters: {
			company: frm.doc.company,
			customer: frm.doc.customer,
			docstatus: 1,
		},
	}));
}

function clear_applied_rate(frm) {
	frm.set_value({
		rate_card: null,
		rate_row: null,
		customer_rate: 0,
		transporter_rate: 0,
		margin: 0,
	});
}

function call_invoice_method(frm, method) {
	frappe.call({
		method: `transporter_invoice.transport_invoicing.doctype.transport_delivery.transport_delivery.${method}`,
		args: { delivery_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Creating invoice documents..."),
		callback() {
			frm.reload_doc();
		},
	});
}
