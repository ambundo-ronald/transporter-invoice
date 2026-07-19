import frappe


EFFECTIVE_FROM = "2026-06-01"

UNDER_10_RATES = [
	{"truck_capacity": "1.5 MT", "under_10_customer_rate": 7800, "under_10_transporter_rate": 6100},
	{"truck_capacity": "3 MT", "under_10_customer_rate": 8200, "under_10_transporter_rate": 6800},
	{"truck_capacity": "5 MT", "under_10_customer_rate": 11200, "under_10_transporter_rate": 8800},
	{"truck_capacity": "7 MT", "under_10_customer_rate": 12500, "under_10_transporter_rate": 10000},
]

ABOVE_10_RATES = [
	("0-25 KMs", ["Thika Town", "Kamakis", "Ruiru"], 1.05, 1.04, 0.94, 0.84, 0.83, 0.73),
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
		1.23,
		1.21,
		1.13,
		0.98,
		0.96,
		0.88,
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
		1.82,
		1.79,
		1.66,
		1.20,
		1.17,
		1.04,
	),
	("101-150Kms", ["Machakos", "Nyeri", "Kajiado", "Kindaruma", "Naivasha", "Mwingi", "Kitui", "Murungaru", "Chuka"], 2.23, 2.17, 1.95, 1.56, 1.50, 1.28),
	("151-200Kms", ["Tharaka", "Gilgil", "Nanyuki", "Engineer", "Emali", "Narok", "Ikanga", "Wote", "Olkalau", "Lanet-Nakuru", "Nakuru"], 2.77, 2.69, 2.49, 2.09, 2.01, 1.81),
	("201-250Kms", ["Mutomo", "OleKanga, Narok", "Namanga", "Njoro", "Nyahururu", "Elburgon", "Kibwezi", "Mulot Town", "Meru", "Molo", "Isiolo"], 2.99, 2.92, 2.67, 2.27, 2.20, 1.95),
	("251-300Kms", ["Bomet", "Maua", "Laare", "Sotik"], 3.40, 3.35, 3.02, 2.48, 2.43, 2.10),
	("301-350Kms", ["Kericho", "Keroka", "Garissa", "Kabarnet", "Litein"], 3.86, 3.80, 3.61, 2.91, 2.85, 2.66),
	("350-400Kms", ["KapSabet", "Nandi Hills", "Eldoret", "Nyamira", "Kilgoris", "Voi", "Mosoroti via Eldoret", "Kisumu", "Oyugis", "Luanda", "Tana River"], 4.63, 4.57, 4.50, 3.38, 3.32, 3.25),
	("350-400Kms", ["Kisii / Nyangori Kisii"], 4.53, 4.47, 4.21, 3.33, 3.27, 3.01),
	("400-500 KMs", ["Mbale", "Mwate", "Vihiga", "Kakamega", "Kitale", "Awendo", "Mumias", "Mbita", "Kapenguria", "Malaba", "Mariakani", "Ukunda Mombasa", "Mtongwe", "Mtwapa", "Malindi", "Ukunda-Kwale", "Lodwar", "Moyale"], 4.92, 4.79, 4.50, 3.77, 3.64, 3.35),
	("400-500 KMs", ["Mombasa"], 4.57, 4.47, 4.21, 3.57, 3.47, 3.21),
	("500 KMs and Above", ["Homabay", "Bondo", "Bungoma", "Migori", "Busia"], 5.21, 5.12, 4.85, 4.21, 4.12, 3.85),
]


def create_default_rate_cards(*args, **kwargs):
	settings = frappe.db.get_value("Transport Invoice Settings", {}, ["company"], as_dict=True)
	if not settings or not settings.company:
		return

	_create_under_10_card(settings.company)
	_create_above_10_card(settings.company)


def _create_under_10_card(company):
	if _default_card_exists(company, "Under 10 Tonnes"):
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


def _create_above_10_card(company):
	if _default_card_exists(company, "10 Tonnes and Above"):
		return

	card = frappe.new_doc("Transport Rate Card")
	card.company = company
	card.rate_category = "10 Tonnes and Above"
	card.rate_unit = "Per Kg"
	card.effective_from = EFFECTIVE_FROM
	card.notes = "Generic draft above-10-tonne route matrix seeded by Transporter Invoice. Edit or delete, then submit when ready."
	for distance_band, locations, c10, c14, ctrailer, t10, t14, t28 in ABOVE_10_RATES:
		for location in locations:
			card.append(
				"rates",
				{
					"distance_band": distance_band,
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


def _default_card_exists(company, rate_category):
	cards = frappe.get_all(
		"Transport Rate Card",
		filters={
			"company": company,
			"rate_category": rate_category,
			"effective_from": EFFECTIVE_FROM,
			"docstatus": ["<", 2],
		},
		fields=["customer", "transporter"],
	)
	return any(not card.customer and not card.transporter for card in cards)
