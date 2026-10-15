frappe.ui.form.on("Transporter Billing Batch", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Get Unpaid Deliveries"), () => {
				frappe.call({
					method: "transporter_invoice.transport_invoicing.doctype.transporter_billing_batch.transporter_billing_batch.get_unpaid_deliveries",
					args: { company: frm.doc.company, transporter: frm.doc.transporter, from_date: frm.doc.from_date, to_date: frm.doc.to_date },
					freeze: true,
					callback(r) {
						frm.clear_table("deliveries");
						(r.message || []).forEach((delivery) => Object.assign(frm.add_child("deliveries"), delivery));
						frm.refresh_field("deliveries");
						frm.trigger("calculate_total");
					},
				});
			});
		}
		if (frm.doc.docstatus === 1 && !frm.doc.purchase_invoice) {
			frm.add_custom_button(__("Create Purchase Invoice"), () => frappe.call({
				method: "transporter_invoice.transport_invoicing.doctype.transporter_billing_batch.transporter_billing_batch.create_purchase_invoice",
				args: { batch_name: frm.doc.name }, freeze: true,
				freeze_message: __("Creating transporter Purchase Invoice..."),
				callback() { frm.reload_doc(); },
			}), __("Create"));
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Cancel Transporter Batch Only"), () => frappe.confirm(
				__("Cancel this batch without cancelling its Transport Deliveries? The deliveries will become available for transporter billing again."),
				() => frappe.call({
					method: "transporter_invoice.transport_invoicing.doctype.transporter_billing_batch.transporter_billing_batch.cancel_transporter_billing_batch_only",
					args: { batch_name: frm.doc.name }, freeze: true,
					freeze_message: __("Cancelling transporter billing batch..."),
					callback() { frm.reload_doc(); },
				})
			), __("Actions"));
		}
	},
	deliveries_add: "calculate_total",
	deliveries_remove: "calculate_total",
	calculate_total(frm) {
		frm.set_value("total_transporter_amount", (frm.doc.deliveries || []).reduce((sum, row) => sum + flt(row.transporter_amount), 0));
	},
});
