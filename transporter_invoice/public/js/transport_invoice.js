function is_generated_transport_invoice(frm) {
	return Boolean(
		frm.doc.custom_transport_delivery ||
		frm.doc.custom_transport_billing_batch ||
		frm.doc.custom_transporter_billing_batch ||
		(frm.doc.items || []).some((row) => row.custom_transport_delivery)
	);
}

function add_transport_cancel_button(frm) {
	if (frm.doc.docstatus !== 1 || !is_generated_transport_invoice(frm)) {
		return;
	}

	const invoice_label = frm.doc.doctype === "Sales Invoice" ? __("Sales Invoice") : __("Purchase Invoice");
	frm.add_custom_button(__("Cancel {0} Only", [invoice_label]), () => {
		frappe.confirm(
			__("Cancel only this {0}? Linked Transport Deliveries and billing batches will remain submitted and become available for correction or rebilling.", [invoice_label]),
			() => frappe.call({
				method: "transporter_invoice.transport_invoicing.invoice_links.cancel_transport_invoice_only",
				args: { doctype: frm.doc.doctype, invoice_name: frm.doc.name },
				freeze: true,
				freeze_message: __("Cancelling {0}...", [invoice_label]),
				callback() { frm.reload_doc(); },
			})
		);
	}, __("Actions"));
}

frappe.ui.form.on("Sales Invoice", { refresh: add_transport_cancel_button });
frappe.ui.form.on("Purchase Invoice", { refresh: add_transport_cancel_button });
