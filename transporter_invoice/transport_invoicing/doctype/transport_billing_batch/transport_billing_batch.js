frappe.ui.form.on("Transport Billing Batch", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Get Unbilled Deliveries"), () => {
				frappe.call({
					method: "transporter_invoice.transport_invoicing.doctype.transport_billing_batch.transport_billing_batch.get_unbilled_deliveries",
					args: {
						company: frm.doc.company,
						customer: frm.doc.customer,
						from_date: frm.doc.from_date,
						to_date: frm.doc.to_date,
					},
					freeze: true,
					callback(r) {
						frm.clear_table("deliveries");
						(r.message || []).forEach((delivery) => {
							const row = frm.add_child("deliveries");
							Object.assign(row, delivery);
						});
						frm.refresh_field("deliveries");
						frm.trigger("calculate_total");
					},
				});
			});
		}

		if (frm.doc.docstatus === 1 && !frm.doc.sales_invoice) {
			frm.add_custom_button(__("Create Sales Invoice"), () => {
				frappe.call({
					method: "transporter_invoice.transport_invoicing.doctype.transport_billing_batch.transport_billing_batch.create_sales_invoice",
					args: { batch_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Creating monthly Sales Invoice..."),
					callback() {
						frm.reload_doc();
					},
				});
			}, __("Create"));
		}
	},

	deliveries_add: "calculate_total",
	deliveries_remove: "calculate_total",

	calculate_total(frm) {
		const total = (frm.doc.deliveries || []).reduce(
			(sum, row) => sum + flt(row.customer_amount),
			0
		);
		frm.set_value("total_customer_amount", total);
	},
});
