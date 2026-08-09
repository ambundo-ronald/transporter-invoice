import frappe


EFFECTIVE_FROM = "2026-06-01"
JULY_2026_EFFECTIVE_FROM = "2026-07-01"

UNDER_10_RATES = [
	{"truck_capacity": "1.5 MT", "under_10_customer_rate": 7800, "under_10_transporter_rate": 6100},
	{"truck_capacity": "3 MT", "under_10_customer_rate": 8200, "under_10_transporter_rate": 6800},
	{"truck_capacity": "5 MT", "under_10_customer_rate": 11200, "under_10_transporter_rate": 8800},
	{"truck_capacity": "7 MT", "under_10_customer_rate": 12500, "under_10_transporter_rate": 10000},
]

ABOVE_10_LOCATIONS = [
	("0-25 KMs", ["Thika Town", "Kamakis", "Ruiru"]),
	(
		"26-50 KMs",
		[
			"Gatanga",
			"Makuyu",
			"Donyo Sabuk",
			"Githurai",
			"Ruai, Nairobi",
			"Kahawa - Nairobi",
			"Zimmerman",
			"Sabasaba",
			"Kariobangi South",
			"Baba Dogo, Nairobi",
			"Kasarani",
			"Utawala - Nairobi",
			"Nairobi - Local",
			"Ruaraka, Nairobi",
			"Kinari",
			"Kayole, Nairobi",
			"Magumu",
			"Kiambu",
			"Eastleigh",
			"Githunguri",
			"Ruaka",
		],
	),
	(
		"51-100Kms",
		[
			"Makutano",
			"Kibera, Nairobi",
			"Nairobi, Industrial Area",
			"Muranga",
			"Kithimani",
			"Kangemi",
			"Kawangware, Nairobi",
			"Embakasi, Nairobi",
			"Wangige",
			"Langata, Nairobi",
			"Kikuyu",
			"Molongo - Nairobi",
			"Karen, Nairobi",
			"Matuu",
			"Uplands",
			"Sagana",
			"Limuru",
			"Rongai",
			"Ngong",
			"Athi River",
			"Mbiuni",
			"Kitengela",
			"Kinale",
			"Gikambura",
			"Kerugoya",
			"Karatina",
			"Embu",
			"Kangundo road",
		],
	),
	("101-150Kms", ["Machakos", "Nyeri", "Kajiado", "Kindaruma", "Naivasha", "Mwingi", "Kitui", "Murungaru", "Chuka"]),
	("151-200Kms", ["Tharaka", "Gilgil", "Nanyuki", "Engineer", "Emali", "Narok", "Ikanga", "Wote", "Olkalau", "Lanet-Nakuru", "Nakuru"]),
	("201-250Kms", ["Mutomo", "OleKanga, Narok", "Namanga", "Njoro", "Nyahururu", "Elburgon", "Kibwezi", "Mulot Town", "Meru", "Molo", "Isiolo"]),
	("251-300Kms", ["Bomet", "Maua", "Laare", "Sotik"]),
	("301-350Kms", ["Kericho", "Keroka", "Garissa", "Kabarnet", "Litein"]),
	("350-400Kms", ["KapSabet", "Nandi Hills", "Eldoret", "Nyamira", "Kilgoris", "Voi", "Mosoroti via Eldoret", "Kisumu", "Oyugis", "Luanda", "Tana River"]),
	("350-400Kms", ["Kisii / Nyangori Kisii"]),
	("400-500 KMs", ["Mbale", "Mwate", "Vihiga", "Kakamega", "Kitale", "Awendo", "Mumias", "Mbita", "Kapenguria", "Malaba", "Mariakani", "Ukunda Mombasa", "Mtongwe", "Mtwapa", "Malindi", "Ukunda-Kwale", "Lodwar", "Moyale"]),
	("400-500 KMs", ["Mombasa"]),
	("500 KMs and Above", ["Homabay", "Bondo", "Bungoma", "Migori", "Busia"]),
]

JUNE_2026_ABOVE_10_RATES = [
	(1.05, 1.04, 0.94, 0.84, 0.83, 0.73),
	(1.23, 1.21, 1.13, 0.98, 0.96, 0.88),
	(1.82, 1.79, 1.66, 1.20, 1.17, 1.04),
	(2.23, 2.17, 1.95, 1.56, 1.50, 1.28),
	(2.77, 2.69, 2.49, 2.09, 2.01, 1.81),
	(2.99, 2.92, 2.67, 2.27, 2.20, 1.95),
	(3.40, 3.35, 3.02, 2.48, 2.43, 2.10),
	(3.86, 3.80, 3.61, 2.91, 2.85, 2.66),
	(4.63, 4.57, 4.50, 3.38, 3.32, 3.25),
	(4.53, 4.47, 4.21, 3.33, 3.27, 3.01),
	(4.92, 4.79, 4.50, 3.77, 3.64, 3.35),
	(4.57, 4.47, 4.21, 3.57, 3.47, 3.21),
	(5.21, 5.12, 4.85, 4.21, 4.12, 3.85),
]

JULY_2026_ABOVE_10_RATES = [
	(0.99, 0.98, 0.89, 0.71, 0.75, 0.61),
	(1.16, 1.13, 1.06, 0.82, 0.86, 0.72),
	(1.71, 1.68, 1.56, 0.95, 0.99, 0.80),
	(2.09, 2.04, 1.84, 1.25, 1.28, 1.00),
	(2.60, 2.53, 2.34, 1.70, 1.74, 1.45),
	(2.81, 2.74, 2.51, 1.85, 1.92, 1.55),
	(3.20, 3.15, 2.84, 2.00, 2.06, 1.65),
	(3.63, 3.57, 3.39, 2.40, 2.49, 2.15),
	(4.35, 4.29, 4.23, 2.75, 2.92, 2.60),
	(4.26, 4.20, 3.96, 2.95, 3.03, 2.70),
	(4.63, 4.51, 4.23, 3.35, 3.41, 2.95),
	(4.63, 4.51, 4.23, 3.07, 3.14, 2.72),
	(4.89, 4.81, 4.56, 3.55, 3.66, 3.20),
]



def create_default_rate_cards(*args, **kwargs):
	settings = frappe.db.get_value("Transport Invoice Settings", {}, ["company"], as_dict=True)
	if not settings or not settings.company:
		return

	_create_under_10_card(settings.company)
	_create_above_10_card(
		settings.company,
		EFFECTIVE_FROM,
		_build_above_10_rates(JUNE_2026_ABOVE_10_RATES),
		"Generic draft above-10-tonne route matrix seeded by Transporter Invoice. Edit or delete, then submit when ready.",
	)
	create_july_2026_above_10_rate_card(settings.company)


def create_july_2026_above_10_rate_card(company=None):
	company = company or frappe.db.get_value("Transport Invoice Settings", {}, "company")
	if not company:
		return

	_create_above_10_card(
		company,
		JULY_2026_EFFECTIVE_FROM,
		_build_above_10_rates(JULY_2026_ABOVE_10_RATES),
		"Generic draft above-10-tonne July 2026 rates seeded by Transporter Invoice. Customer rates and transporter rates are both from the July tables. Review, edit, then submit when ready.",
	)


def _create_under_10_card(company):
	if _default_card_exists(company, "Under 10 Tonnes", EFFECTIVE_FROM):
		return

	card = frappe.new_doc("Transport Rate Card")
	card.company = company
	card.rate_category = "Under 10 Tonnes"
	card.rate_unit = "Fixed Trip Amount"
	card.effective_from = EFFECTIVE_FROM
	card.notes = "Generic draft under-10-tonne rates seeded by Transporter Invoice. Edit or delete, then submit when ready."
	for row in UNDER_10_RATES:
		card.append("rates", row)
	card.insert(ignore_permissions=True)


def _create_above_10_card(company, effective_from, rates, notes):
	if _default_card_exists(company, "10 Tonnes and Above", effective_from):
		return

	card = frappe.new_doc("Transport Rate Card")
	card.company = company
	card.rate_category = "10 Tonnes and Above"
	card.rate_unit = "Fixed Trip Amount"
	card.effective_from = effective_from
	card.notes = notes
	for distance_band, locations, c10, c14, ctrailer, t10, t14, t28 in rates:
		for location in locations:
			card.append(
				"rates",
				{
					"distance_band": distance_band,
					"from_km": _distance_range(distance_band)[0],
					"to_km": _distance_range(distance_band)[1],
					"location": location,
					"customer_10mt_rate": c10,
					"customer_14mt_rate": c14,
					"customer_trailer_rate": ctrailer,
					"transporter_10_13mt_rate": t10,
					"transporter_14_17mt_rate": t14,
					"transporter_28mt_rate": t28,
				},
			)
	card.insert(ignore_permissions=True)


def _default_card_exists(company, rate_category, effective_from):
	cards = frappe.get_all(
		"Transport Rate Card",
		filters={
			"company": company,
			"rate_category": rate_category,
			"effective_from": effective_from,
			"docstatus": ["<", 2],
		},
		fields=["customer", "transporter"],
	)
	return any(not card.customer and not card.transporter for card in cards)


def _build_above_10_rates(rate_rows):
	if len(rate_rows) != len(ABOVE_10_LOCATIONS):
		raise ValueError("Above-10 rate rows must match the location band rows.")
	return [(*location_row, *rates) for location_row, rates in zip(ABOVE_10_LOCATIONS, rate_rows)]


def _distance_range(distance_band):
	mapping = {
		"0-25 KMs": (0, 25),
		"26-50 KMs": (26, 50),
		"51-100Kms": (51, 100),
		"101-150Kms": (101, 150),
		"151-200Kms": (151, 200),
		"201-250Kms": (201, 250),
		"251-300Kms": (251, 300),
		"301-350Kms": (301, 350),
		"350-400Kms": (350, 400),
		"400-500 KMs": (400, 500),
		"500 KMs and Above": (500, None),
	}
	return mapping[distance_band]
