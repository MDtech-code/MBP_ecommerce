# City name → postal code mapping
# Postal codes sourced from Pakistan Post official codes
# DB value of City choices must match keys exactly

CITY_POSTAL_MAP: dict[str, str] = {
    # Punjab
    "Lahore":        "54000",
    "Faisalabad":    "38000",
    "Rawalpindi":    "46000",
    "Gujranwala":    "52250",
    "Multan":        "60000",
    "Sialkot":       "51310",
    "Bahawalpur":    "63100",
    "Sargodha":      "40100",
    "Sheikhupura":   "39350",
    "Gujrat":        "50700",
    "Rahim Yar Khan":"64200",
    "Jhang":         "35200",
    "Sahiwal":       "57000",
    "Okara":         "56300",
    "Kasur":         "55020",
    # Sindh
    "Karachi":       "75000",
    "Hyderabad":     "71000",
    "Sukkur":        "65200",
    "Larkana":       "77150",
    "Nawabshah":     "67480",
    "Mirpur Khas":   "69000",
    # Khyber Pakhtunkhwa
    "Peshawar":      "25000",
    "Abbottabad":    "22010",
    "Mardan":        "23200",
    "Swat":          "19130",
    "Kohat":         "26000",
    "Mingora":       "19130",
    # Balochistan
    "Quetta":        "87300",
    "Turbat":        "92600",
    "Khuzdar":       "89100",
    # Federal / AJK / GB
    "Islamabad":     "44000",
    "Muzaffarabad":  "13100",
    "Gilgit":        "15100",
}


# City name → province code mapping
# Province codes match Province TextChoices in accounts/choices/province.py
# Used in UserAddress.save() to auto-derive province from city selection

CITY_PROVINCE_MAP: dict[str, str] = {
    # Punjab → PB
    "Lahore": "PB",       "Faisalabad": "PB",   "Rawalpindi": "PB",
    "Gujranwala": "PB",   "Multan": "PB",        "Sialkot": "PB",
    "Bahawalpur": "PB",   "Sargodha": "PB",      "Sheikhupura": "PB",
    "Gujrat": "PB",       "Rahim Yar Khan": "PB","Jhang": "PB",
    "Sahiwal": "PB",      "Okara": "PB",          "Kasur": "PB",
    # Sindh → SD
    "Karachi": "SD",      "Hyderabad": "SD",     "Sukkur": "SD",
    "Larkana": "SD",      "Nawabshah": "SD",     "Mirpur Khas": "SD",
    # Khyber Pakhtunkhwa → KP
    "Peshawar": "KP",     "Abbottabad": "KP",    "Mardan": "KP",
    "Swat": "KP",         "Kohat": "KP",         "Mingora": "KP",
    # Balochistan → BL
    "Quetta": "BL",       "Turbat": "BL",        "Khuzdar": "BL",
    # Federal / AJK / GB
    "Islamabad": "IC",    "Muzaffarabad": "AK",  "Gilgit": "GB",
}