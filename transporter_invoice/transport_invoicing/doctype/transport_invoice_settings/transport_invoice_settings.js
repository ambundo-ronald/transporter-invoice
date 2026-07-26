frappe.ui.form.on("Transport Invoice Settings", {
	refresh(frm) {
		for (const fieldname of ["sales_item", "purchase_item"]) {
			frm.set_query(fieldname, () => ({
				filters: {
					disabled: 0,
					is_stock_item: 0,
				},
			}));
		}
	},
});