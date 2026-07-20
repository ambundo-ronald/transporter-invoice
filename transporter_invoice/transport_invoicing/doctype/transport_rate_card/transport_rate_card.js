frappe.ui.form.on("Transport Rate Card", {
	refresh(frm) {
		frm.set_query("customer", () => ({
			filters: { disabled: 0 },
		}));
		frm.set_query("transporter", () => ({
			filters: { disabled: 0 },
		}));
	},
	rate_category(frm) {
		if (frm.doc.rate_category === "Under 10 Tonnes") {
			frm.set_value("rate_unit", "Fixed Trip Amount");
		} else if (frm.doc.rate_category === "10 Tonnes and Above") {
			frm.set_value("rate_unit", "Per Km");
		}
	},
});

