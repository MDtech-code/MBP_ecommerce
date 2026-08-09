/**
 * locationData.js — shared city/province/postal data
 *
 * Single source of truth for all Pakistani city data on the frontend.
 * Mirrors backend CITY_PROVINCE_MAP and CITY_POSTAL_MAP exactly.
 * Mirrors backend _calculate_shipping_fee() logic exactly.
 *
 * Any backend change to city data or shipping tiers
 * MUST be reflected here simultaneously.
 *
 * Consumers:
 *   - useAddressForm     (address create/edit)
 *   - checkoutStore      (city → province/postal/shipping auto-derive)
 *   - CheckoutAddressPage (city dropdown)
 *   - CartSummary        (shipping fee preview — not yet, placeholder)
 */


// ── Province codes ────────────────────────────────────────────────────────────
// Matches Province TextChoices in apps/accounts/choices/province.py
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
// Sourced from Pakistan Post official codes
// Matches CITY_POSTAL_MAP in apps/accounts/constants.py
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
// Ordered to match City TextChoices in apps/accounts/choices/city.py
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
// Mirrors _calculate_shipping_fee() in apps/orders/services/order_service.py
// MUST stay in sync — if backend changes tiers, update here too
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








export const CITY_OPTIONS = [
  { value: "",               label: "Select your city",   group: null         },
  { value: "Lahore",         label: "Lahore",             group: "Punjab"     },
  { value: "Faisalabad",     label: "Faisalabad",         group: "Punjab"     },
  { value: "Rawalpindi",     label: "Rawalpindi",         group: "Punjab"     },
  { value: "Gujranwala",     label: "Gujranwala",         group: "Punjab"     },
  { value: "Multan",         label: "Multan",             group: "Punjab"     },
  { value: "Sialkot",        label: "Sialkot",            group: "Punjab"     },
  { value: "Bahawalpur",     label: "Bahawalpur",         group: "Punjab"     },
  { value: "Sargodha",       label: "Sargodha",           group: "Punjab"     },
  { value: "Sheikhupura",    label: "Sheikhupura",        group: "Punjab"     },
  { value: "Gujrat",         label: "Gujrat",             group: "Punjab"     },
  { value: "Rahim Yar Khan", label: "Rahim Yar Khan",    group: "Punjab"     },
  { value: "Jhang",          label: "Jhang",              group: "Punjab"     },
  { value: "Sahiwal",        label: "Sahiwal",            group: "Punjab"     },
  { value: "Okara",          label: "Okara",              group: "Punjab"     },
  { value: "Kasur",          label: "Kasur",              group: "Punjab"     },
  { value: "Karachi",        label: "Karachi",            group: "Sindh"      },
  { value: "Hyderabad",      label: "Hyderabad",          group: "Sindh"      },
  { value: "Sukkur",         label: "Sukkur",             group: "Sindh"      },
  { value: "Larkana",        label: "Larkana",            group: "Sindh"      },
  { value: "Nawabshah",      label: "Nawabshah",          group: "Sindh"      },
  { value: "Mirpur Khas",    label: "Mirpur Khas",        group: "Sindh"      },
  { value: "Peshawar",       label: "Peshawar",           group: "KPK"        },
  { value: "Abbottabad",     label: "Abbottabad",         group: "KPK"        },
  { value: "Mardan",         label: "Mardan",             group: "KPK"        },
  { value: "Swat",           label: "Swat",               group: "KPK"        },
  { value: "Kohat",          label: "Kohat",              group: "KPK"        },
  { value: "Mingora",        label: "Mingora",            group: "KPK"        },
  { value: "Quetta",         label: "Quetta",             group: "Balochistan"},
  { value: "Turbat",         label: "Turbat",             group: "Balochistan"},
  { value: "Khuzdar",        label: "Khuzdar",            group: "Balochistan"},
  { value: "Islamabad",      label: "Islamabad",          group: "Federal"    },
  { value: "Muzaffarabad",   label: "Muzaffarabad",       group: "AJK"        },
  { value: "Gilgit",         label: "Gilgit",             group: "GB"         },
]
export const  CITY_GROUPS = [
  { label: "Punjab",              values: CITY_OPTIONS.filter(c => c.group === "Punjab")                          },
  { label: "Sindh",               values: CITY_OPTIONS.filter(c => c.group === "Sindh")                           },
  { label: "KPK",                 values: CITY_OPTIONS.filter(c => c.group === "KPK")                             },
  { label: "Balochistan",         values: CITY_OPTIONS.filter(c => c.group === "Balochistan")                     },
  { label: "Federal / AJK / GB",  values: CITY_OPTIONS.filter(c => ["Federal","AJK","GB"].includes(c.group))      },
]