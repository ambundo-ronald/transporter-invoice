const UNDER_10_TRUCK_CLASSES = ["1.5 MT", "3 MT", "5 MT", "7 MT"];
const ABOVE_10_TRUCK_CLASSES = ["10 MT", "14 MT", "Trailer", "Mixed"];

frappe.ui.form.on("Transport Delivery", {
	refresh(frm) {
		frm._previous_transporter = frm.doc.transporter;
		frm._previous_delivery_date = frm.doc.delivery_date;
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
		fill_default_above_10_trip_values(frm, null, null, {
			previous_transporter: frm._previous_transporter,
		});
		frm._previous_transporter = frm.doc.transporter;
		clear_applied_rate(frm);
	},
	delivery_date(frm) {
		load_route_location_options(frm);
		fill_default_above_10_trip_values(frm, null, null, {
			previous_delivery_date: frm._previous_delivery_date,
		});
		frm._previous_delivery_date = frm.doc.delivery_date;
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

	above_10_trips_add(frm, cdt, cdn) {
		fill_default_above_10_trip_values(frm, cdt, cdn);
		update_above_10_truck_classes(frm, cdt, cdn);
	},

	above_10_trips_remove(frm) {
		update_above_10_truck_classes(frm);
		clear_applied_rate(frm);
	},
});

frappe.ui.form.on("Transport Delivery Above 10 Trip", {
	trip_date: clear_applied_rate,
	customer_name: clear_applied_rate,
	truck_no: clear_applied_rate,
	destination: clear_applied_rate,
	weight_kg(frm, cdt, cdn) {
		update_above_10_truck_classes(frm, cdt, cdn);
		clear_applied_rate(frm);
	},
	form_render(frm, cdt, cdn) {
		load_route_location_options(frm);
		fill_default_above_10_trip_values(frm, cdt, cdn);
		update_above_10_truck_classes(frm, cdt, cdn);
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
});

function set_category_fields(frm) {
	const is_under_10 = frm.doc.rate_category === "Under 10 Tonnes";
	const options = is_under_10 ? UNDER_10_TRUCK_CLASSES : ABOVE_10_TRUCK_CLASSES;

	frm.set_df_property("truck_class", "options", options.join("\n"));
	if (frm.doc.truck_class && !options.includes(frm.doc.truck_class)) {
		frm.set_value("truck_class", null);
	}

	frm.set_df_property("destination", "reqd", false);
	frm.set_df_property("truck_class", "reqd", is_under_10);
	frm.set_df_property("actual_distance_km", "reqd", false);
	frm.set_df_property("actual_distance_km", "hidden", is_under_10);
	frm.set_df_property("under_10_trips_section", "hidden", !is_under_10);
	frm.set_df_property("under_10_trips", "hidden", !is_under_10);
	frm.set_df_property("above_10_trips_section", "hidden", is_under_10);
	frm.set_df_property("above_10_trips", "hidden", is_under_10);
	frm.set_df_property("truck_class", "read_only", !is_under_10);
	if (!is_under_10) {
		update_above_10_truck_classes(frm);
	}
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
			: __("Auto-filled from above-10 trip rows. Each row uses destination + weight to choose the flat rate.")
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

function fill_default_above_10_trip_values(frm, cdt, cdn, opts = {}) {
	if (frm.doc.rate_category !== "10 Tonnes and Above") {
		return;
	}

	const rows = frm.doc.above_10_trips || [];
	for (const row of rows) {
		if (cdt && cdn && row.name !== cdn) {
			continue;
		}

		const can_update_date = !row.trip_date || row.trip_date === opts.previous_delivery_date;
		if (can_update_date && frm.doc.delivery_date) {
			frappe.model.set_value(row.doctype, row.name, "trip_date", frm.doc.delivery_date);
		}

		const can_update_truck_no = !row.truck_no || row.truck_no === opts.previous_transporter;
		if (can_update_truck_no && frm.doc.transporter) {
			frappe.model.set_value(row.doctype, row.name, "truck_no", frm.doc.transporter);
		}
	}
}

function update_above_10_truck_classes(frm, cdt, cdn) {
	if (frm.doc.rate_category !== "10 Tonnes and Above") {
		return;
	}

	const rows = frm.doc.above_10_trips || [];
	const truck_classes = new Set();
	let total_weight = 0;

	for (const row of rows) {
		const weight = flt(row.weight_kg);
		if (weight <= 0) {
			continue;
		}

		const truck_class = get_above_10_truck_class(weight);
		total_weight += weight;
		truck_classes.add(truck_class);
		if (!cdt || !cdn || row.name === cdn) {
			frappe.model.set_value(row.doctype, row.name, "truck_class", truck_class);
		}
	}

	if (rows.length) {
		frm.set_value("actual_weight_kg", total_weight);
	}

	if (!truck_classes.size) {
		frm.set_value("truck_class", null);
		return;
	}

	frm.set_value("truck_class", truck_classes.size === 1 ? Array.from(truck_classes)[0] : "Mixed");
}

function get_above_10_truck_class(weight_kg) {
	const weight = flt(weight_kg);
	if (weight <= 10000) {
		return "10 MT";
	}
	if (weight <= 14000) {
		return "14 MT";
	}
	return "Trailer";
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
