frappe.ui.form.on("Transport Rate Card", {
	refresh(frm) {
		frm.set_query("customer", () => ({
			filters: { disabled: 0 },
		}));
		frm.set_query("transporter", () => ({
			filters: { disabled: 0 },
		}));
	},
});
