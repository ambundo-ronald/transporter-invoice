const UNDER_10_TRUCK_CLASSES = ["1.5 MT", "3 MT", "5 MT", "7 MT"];
const ABOVE_10_TRUCK_CLASSES = ["10 MT", "14 MT", "Trailer", "Mixed"];

frappe.ui.form.on("Transport Delivery", {
	refresh(frm) {
		set_category_fields(frm);
		load_route_location_options(frm);

		if (frm.doc.docstatus !== 1) {
			return;
		}

		if (!frm.doc.sales_invoice && !frm.doc.billing_batch) {
			frm.add_custom_button(__("Sales Invoice"), () => {
				call_invoice_method(frm, "create_sales_invoice");
			}, __("Create"));
		}

		if (!frm.doc.purchase_invoice) {
			frm.add_custom_button(__("Purchase Invoice"), () => {
				call_invoice_method(frm, "create_purchase_invoice");
			}, __("Create"));
		}

		if (!frm.doc.sales_invoice && !frm.doc.billing_batch && !frm.doc.purchase_invoice) {
			frm.add_custom_button(__("Sales + Purchase Invoices"), () => {
				call_invoice_method(frm, "create_both_invoices");
			}, __("Create"));
		}
	},

	company(frm) {
		load_route_location_options(frm);
		clear_applied_rate(frm);
	},
	customer(frm) {
		load_route_location_options(frm);
		clear_applied_rate(frm);
	},
	transporter(frm) {
		load_route_location_options(frm);
		clear_applied_rate(frm);
	},
	delivery_date(frm) {
		load_route_location_options(frm);
		clear_applied_rate(frm);
	},
	destination: clear_applied_rate,

	rate_category(frm) {
		set_category_fields(frm);
		load_route_location_options(frm);
		clear_applied_rate(frm);
	},

	truck_class: clear_applied_rate,
	actual_distance_km: clear_applied_rate,
	actual_weight_kg: clear_applied_rate,

	under_10_trips_remove(frm) {
		update_under_10_total_weight(frm);
		clear_applied_rate(frm);
	},

	above_10_trips_remove(frm) {
		clear_applied_rate(frm);
	},
});

frappe.ui.form.on("Transport Delivery Above 10 Trip", {
	destination: clear_applied_rate,
	weight_kg: clear_applied_rate,
	form_render(frm) {
		load_route_location_options(frm);
	},
});

frappe.ui.form.on("Transport Delivery Trip", {
	destination: clear_applied_rate,
	form_render(frm) {
		load_route_location_options(frm);
	},

	weight_kg(frm) {
		update_under_10_total_weight(frm);
		clear_applied_rate(frm);
	},

	under_10_trips_remove(frm) {
		update_under_10_total_weight(frm);
		clear_applied_rate(frm);
	},

	above_10_trips_remove(frm) {
		clear_applied_rate(frm);
	},
});

function set_category_fields(frm) {
	const is_under_10 = frm.doc.rate_category === "Under 10 Tonnes";
	const options = is_under_10 ? UNDER_10_TRUCK_CLASSES : ABOVE_10_TRUCK_CLASSES;

	frm.set_df_property("truck_class", "options", options.join("\n"));
	if (frm.doc.truck_class && !options.includes(frm.doc.truck_class)) {
		frm.set_value("truck_class", null);
	}

	frm.set_df_property("destination", "reqd", !is_under_10 && !(frm.doc.above_10_trips || []).length);
	frm.set_df_property("actual_distance_km", "reqd", false);
	frm.set_df_property("actual_distance_km", "hidden", is_under_10);
	frm.set_df_property("under_10_trips_section", "hidden", !is_under_10);
	frm.set_df_property("under_10_trips", "hidden", !is_under_10);
	frm.set_df_property("above_10_trips_section", "hidden", is_under_10);
	frm.set_df_property("above_10_trips", "hidden", is_under_10);
	frm.set_df_property("truck_class", "read_only", !is_under_10);
	frm.set_df_property(
		"destination",
		"description",
		is_under_10
			? __("Optional route note for this fixed small-truck trip.")
			: __("Start typing and select a submitted rate-card location, for example Thika Town or Mombasa.")
	);
	frm.set_df_property(
		"actual_distance_km",
		"description",
		__("Optional audit distance. Over-10 rates are flat by selected location, not multiplied by KM.")
	);
	frm.set_df_property(
		"actual_weight_kg",
		"description",
		is_under_10
			? __("Total trip weight used to prorate the fixed under-10 tonne rate. Auto-filled from trip rows when rows are added.")
			: __("Optional supporting delivery information. Above-10 rates use actual KM, not weight.")
	);
}

function load_route_location_options(frm) {
	if (!frm.doc.company) {
		return;
	}

	frappe.call({
		method: "transporter_invoice.transport_invoicing.doctype.transport_delivery.transport_delivery.get_route_location_options",
		args: {
			company: frm.doc.company,
			delivery_date: frm.doc.delivery_date,
			customer: frm.doc.customer,
			transporter: frm.doc.transporter,
			rate_category: "10 Tonnes and Above",
		},
		callback(response) {
			const options = (response.message || []).join("\n");
			frm.set_df_property("destination", "options", options);
			for (const table_field of ["above_10_trips", "under_10_trips"]) {
				if (frm.fields_dict[table_field]) {
					frm.fields_dict[table_field].grid.update_docfield_property("destination", "options", options);
				}
			}
		},
	});
}

function update_under_10_total_weight(frm) {
	if (frm.doc.rate_category !== "Under 10 Tonnes") {
		return;
	}

	const rows = frm.doc.under_10_trips || [];
	const total_weight = rows.reduce((total, row) => total + flt(row.weight_kg), 0);
	if (rows.length) {
		frm.set_value("actual_weight_kg", total_weight);
	}
}

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
