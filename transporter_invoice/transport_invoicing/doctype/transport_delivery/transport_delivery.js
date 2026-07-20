frappe.ui.form.on("Transport Delivery", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) {
			return;
		}

		if (!frm.doc.purchase_invoice) {
			frm.add_custom_button(__("Purchase Invoice"), () => {
				call_invoice_method(frm, "create_purchase_invoice");
			}, __("Create"));
		}
	},

	company: clear_applied_rate,
	customer: clear_applied_rate,
	delivery_date: clear_applied_rate,
	destination: clear_applied_rate,
	rate_category: clear_applied_rate,
	truck_class: clear_applied_rate,
	actual_distance_km: clear_applied_rate,
	actual_weight_kg: clear_applied_rate,
});

function clear_applied_rate(frm) {
	frm.set_value({
		rate_card: null,
		rate_row: null,
		distance_band: null,
		rate_unit: null,
		customer_rate: 0,
		transporter_rate: 0,
		customer_amount: 0,
		transporter_amount: 0,
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

