frappe.ui.form.on("Transport Rate Card", {
	refresh(frm) {
		frm.set_query("customer", () => ({
			filters: { disabled: 0 },
		}));
	},
});

frappe.ui.form.on("Transport Rate", {
	customer_rate(frm, cdt, cdn) {
		set_margin(cdt, cdn);
	},
	transporter_rate(frm, cdt, cdn) {
		set_margin(cdt, cdn);
	},
});

function set_margin(cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "margin", flt(row.customer_rate) - flt(row.transporter_rate));
}
