
export const CITY_PROVINCE_MAP = {
  // Punjab → PB
  Lahore: "PB",
  Faisalabad: "PB",
  Rawalpindi: "PB",
  Gujranwala: "PB",
  Multan: "PB",
  Sialkot: "PB",
  Bahawalpur: "PB",
  Sargodha: "PB",
  Sheikhupura: "PB",
  Gujrat: "PB",
  "Rahim Yar Khan": "PB",
  Jhang: "PB",
  Sahiwal: "PB",
  Okara: "PB",
  Kasur: "PB",
  // Sindh → SD
  Karachi: "SD",
  Hyderabad: "SD",
  Sukkur: "SD",
  Larkana: "SD",
  Nawabshah: "SD",
  "Mirpur Khas": "SD",
  // Khyber Pakhtunkhwa → KP
  Peshawar: "KP",
  Abbottabad: "KP",
  Mardan: "KP",
  Swat: "KP",
  Kohat: "KP",
  Mingora: "KP",
  // Balochistan → BL
  Quetta: "BL",
  Turbat: "BL",
  Khuzdar: "BL",
  // Federal / AJK / GB
  Islamabad: "IC",
  Muzaffarabad: "AK",
  Gilgit: "GB",
};

// ── Postal codes ──────────────────────────────────────────────────────────────

export const CITY_POSTAL_MAP = {
  // Punjab
  Lahore: "54000",
  Faisalabad: "38000",
  Rawalpindi: "46000",
  Gujranwala: "52250",
  Multan: "60000",
  Sialkot: "51310",
  Bahawalpur: "63100",
  Sargodha: "40100",
  Sheikhupura: "39350",
  Gujrat: "50700",
  "Rahim Yar Khan": "64200",
  Jhang: "35200",
  Sahiwal: "57000",
  Okara: "56300",
  Kasur: "55020",
  // Sindh
  Karachi: "75000",
  Hyderabad: "71000",
  Sukkur: "65200",
  Larkana: "77150",
  Nawabshah: "67480",
  "Mirpur Khas": "69000",
  // Khyber Pakhtunkhwa
  Peshawar: "25000",
  Abbottabad: "22010",
  Mardan: "23200",
  Swat: "19130",
  Kohat: "26000",
  Mingora: "19130",
  // Balochistan
  Quetta: "87300",
  Turbat: "92600",
  Khuzdar: "89100",
  // Federal / AJK / GB
  Islamabad: "44000",
  Muzaffarabad: "13100",
  Gilgit: "15100",
};

// ── City list for dropdowns ───────────────────────────────────────────────────

export const CITY_LIST = [
  // Punjab
  "Lahore",
  "Faisalabad",
  "Rawalpindi",
  "Gujranwala",
  "Multan",
  "Sialkot",
  "Bahawalpur",
  "Sargodha",
  "Sheikhupura",
  "Gujrat",
  "Rahim Yar Khan",
  "Jhang",
  "Sahiwal",
  "Okara",
  "Kasur",
  // Sindh
  "Karachi",
  "Hyderabad",
  "Sukkur",
  "Larkana",
  "Nawabshah",
  "Mirpur Khas",
  // Khyber Pakhtunkhwa
  "Peshawar",
  "Abbottabad",
  "Mardan",
  "Swat",
  "Kohat",
  "Mingora",
  // Balochistan
  "Quetta",
  "Turbat",
  "Khuzdar",
  // Federal / AJK / GB
  "Islamabad",
  "Muzaffarabad",
  "Gilgit",
];

// ── Shipping tier ─────────────────────────────────────────────────────────────

const MAJOR_CITIES = new Set(["Lahore", "Karachi", "Islamabad", "Rawalpindi"]);

export const SHIPPING_RATES = {
  MAJOR: 150,
  STANDARD: 200,
};

// ── Helper functions ──────────────────────────────────────────────────────────

/**
 * Get province code for a city.
 * Returns empty string if city not found.
 * @param {string} city
 * @returns {string} province code e.g. "PB" | "SD" | "KP"
 */
export function getProvinceForCity(city) {
  return CITY_PROVINCE_MAP[city] ?? "";
}

/**
 * Get postal code for a city.
 * Returns empty string if city not found.
 * @param {string} city
 * @returns {string} postal code e.g. "54000"
 */
export function getPostalForCity(city) {
  return CITY_POSTAL_MAP[city] ?? "";
}

/**
 * Get shipping fee for a city.
 * Returns null when city is empty — means "not yet selected".
 * null is used by CartSummary to show "Calculated at checkout".
 * Mirrors backend _calculate_shipping_fee() exactly.
 * @param {string|null} city
 * @returns {number|null} 150 | 200 | null
 */
export function getShippingFee(city) {
  if (!city) return null;
  return MAJOR_CITIES.has(city)
    ? SHIPPING_RATES.MAJOR
    : SHIPPING_RATES.STANDARD;
}








