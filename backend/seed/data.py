"""
Seed data: Products, Categories, Brands, Bike Models, Coupons, Users, Cart.
Pakistan Motorbike Parts Store — production quality data.

Changes from previous version:
    - Added weight_grams to every product (used for shipping cost calculation)
    - Added low_stock_threshold to every product (admin alert trigger)
    - Added specifications list to every product (ProductSpecification rows)
    - Added COUPONS_DATA — 5 Pakistan festival coupons
"""

from datetime import datetime, timezone as tz

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIES_DATA = [
    # (name, parent_name_or_None)
    ("Engine Parts",           None),
    ("Brake System",           None),
    ("Electrical & Lights",    None),
    ("Tyres & Tubes",          None),
    ("Transmission",           None),
    ("Lubrication & Oils",     None),
    ("Body & Frame",           None),
    # Sub-categories
    ("Pistons & Rings",        "Engine Parts"),
    ("Filters",                "Engine Parts"),
    ("Carburettors",           "Engine Parts"),
    ("Disc Brakes",            "Brake System"),
    ("Drum Brakes",            "Brake System"),
    ("Headlights",             "Electrical & Lights"),
    ("Indicators & Bulbs",     "Electrical & Lights"),
    ("Batteries",              "Electrical & Lights"),
    ("Drive Chain & Sprocket", "Transmission"),
    ("Clutch Parts",           "Transmission"),
]

# ─────────────────────────────────────────────────────────────────────────────
# BRANDS
# ─────────────────────────────────────────────────────────────────────────────

BRANDS_DATA = [
    "Honda", "Yamaha", "Suzuki", "Ravi", "United",
    "Road Prince", "Dayang", "Superpower", "NGK",
    "Yuasa", "Dunlop", "Innova", "Castrol", "Motigear", "DID",
]

# ─────────────────────────────────────────────────────────────────────────────
# BIKE MODELS
# ─────────────────────────────────────────────────────────────────────────────

BIKE_MODELS_DATA = [
    # (brand_name, model_name, year_start, year_end_or_None)
    ("Honda",       "CD70",       1981, None),
    ("Honda",       "CG125",      1976, None),
    ("Honda",       "CB150F",     2015, None),
    ("Honda",       "CB125F",     2019, None),
    ("Honda",       "CG125S",     2010, None),
    ("Yamaha",      "YBR125",     2005, None),
    ("Yamaha",      "YBR125G",    2010, None),
    ("Yamaha",      "Saluto 125", 2016, None),
    ("Yamaha",      "YZF-R15",    2018, None),
    ("Suzuki",      "GS150",      2009, None),
    ("Suzuki",      "GR150",      2016, None),
    ("Suzuki",      "GS150SE",    2014, None),
    ("Ravi",        "Wolf 150",   2015, None),
    ("Ravi",        "Piaggio",    2012, 2020),
    ("United",      "US 100",     2016, None),
    ("United",      "US 125",     2017, None),
    ("Road Prince", "RP 70",      2015, None),
    ("Road Prince", "RP 125",     2016, None),
    ("Dayang",      "DY 125",     2014, None),
    ("Superpower",  "SP 70",      2013, None),
]

# ─────────────────────────────────────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────────────────────────────────────

USERS_DATA = [
    {
        "email":        "customer1@gmail.com",
        "password":     "Customer@12345",
        "full_name":    "Virja Rock",
        "role":         "CU",
        "is_staff":     False,
        "is_superuser": False,
        "is_verified":  True,
        "is_active":    True,
    },
    {
        "email":        "customer2@gmail.com",
        "password":     "Customer@12345",
        "full_name":    "Rock Aslam",
        "role":         "CU",
        "is_staff":     False,
        "is_superuser": False,
        "is_verified":  True,
        "is_active":    True,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# CART
# ─────────────────────────────────────────────────────────────────────────────

CART_DATA = {
    "customer1@gmail.com": [
        # (sku, quantity)
        ("BAT-YUA-001", 1),
        ("BRK-HND-001", 2),
        ("CHN-DID-002", 1),
        ("TYR-DUN-001", 2),
        ("OIL-CAS-001", 3),
    ],
    "customer2@gmail.com": [
        ("BAT-YUA-002", 1),
        ("CHN-SUZ-003", 1),
        ("TYR-INV-003", 1),
        ("LGT-YAM-002", 1),
        ("OIL-CAS-001", 2),
        ("ENG-NGK-004", 4),
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# COUPONS  (Pakistan festival coupons)
#
# valid_from / valid_until: UTC datetime objects.
# Mix of expired (for history), active, and upcoming (for testing).
# Coupon.save() normalises code to uppercase automatically.
# ─────────────────────────────────────────────────────────────────────────────

COUPONS_DATA = [
    # 1 ── Eid ul Fitr 2026 (expired — March/April 2026)
    {
        "code":                 "EIDMUBARAK26",
        "discount_type":        "percentage",
        "discount_value":       "20.00",
        "min_order_amount":     "1500.00",
        "max_discount_amount":  "800.00",
        "usage_limit_total":    200,
        "usage_limit_per_user": 1,
        "valid_from":           datetime(2026, 3, 29, 0,  0,  tzinfo=tz.utc),
        "valid_until":          datetime(2026, 4, 12, 23, 59, tzinfo=tz.utc),
        "is_active":            True,
    },

    # 2 ── Eid ul Adha / Bakra Eid 2026 (expired — June 2026)
    {
        "code":                 "BAKRAEID26",
        "discount_type":        "percentage",
        "discount_value":       "15.00",
        "min_order_amount":     "2000.00",
        "max_discount_amount":  "600.00",
        "usage_limit_total":    300,
        "usage_limit_per_user": 1,
        "valid_from":           datetime(2026, 6, 5,  0,  0,  tzinfo=tz.utc),
        "valid_until":          datetime(2026, 6, 20, 23, 59, tzinfo=tz.utc),
        "is_active":            True,
    },

    # 3 ── Pakistan Independence Day 2026 (upcoming — August 14)
    {
        "code":                 "AZAADI2026",
        "discount_type":        "fixed_pkr",
        "discount_value":       "500.00",
        "min_order_amount":     "2500.00",
        "max_discount_amount":  None,
        "usage_limit_total":    500,
        "usage_limit_per_user": 1,
        "valid_from":           datetime(2026, 8, 11, 0,  0,  tzinfo=tz.utc),
        "valid_until":          datetime(2026, 8, 16, 23, 59, tzinfo=tz.utc),
        "is_active":            True,
    },

    # 4 ── Pakistan Day — March 23 (expired)
    {
        "code":                 "MARCH232026",
        "discount_type":        "free_shipping",
        "discount_value":       "0.00",
        "min_order_amount":     "1000.00",
        "max_discount_amount":  None,
        "usage_limit_total":    150,
        "usage_limit_per_user": 1,
        "valid_from":           datetime(2026, 3, 21, 0,  0,  tzinfo=tz.utc),
        "valid_until":          datetime(2026, 3, 24, 23, 59, tzinfo=tz.utc),
        "is_active":            True,
    },

    # 5 ── Defence Day — September 6 (upcoming)
    {
        "code":                 "DEFENCE2026",
        "discount_type":        "percentage",
        "discount_value":       "10.00",
        "min_order_amount":     "1200.00",
        "max_discount_amount":  "400.00",
        "usage_limit_total":    250,
        "usage_limit_per_user": 2,
        "valid_from":           datetime(2026, 9, 4,  0,  0,  tzinfo=tz.utc),
        "valid_until":          datetime(2026, 9, 8,  23, 59, tzinfo=tz.utc),
        "is_active":            True,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTS
#
# New fields added to every product:
#   weight_grams        → used by shipping cost calculation (None = unknown)
#   low_stock_threshold → admin alert when stock ≤ this value (0 = disabled)
#   specifications      → list of dicts for ProductSpecification rows
#       each dict: {name, value, unit (optional), display_order (optional)}
# ─────────────────────────────────────────────────────────────────────────────

PRODUCTS_DATA = [

    # ── BATTERIES ──────────────────────────────────────────────────────────────
    {
        "name":        "Yuasa YB5L-B 12V Motorbike Battery",
        "sku":         "BAT-YUA-001",
        "category":    "Batteries",
        "brand":       "Yuasa",
        "compatible_bikes": ["Honda CG125", "Honda CG125S", "Honda CB125F"],
        "description": (
            "Genuine Yuasa YB5L-B 12V 5Ah lead-acid battery designed for 125cc–150cc "
            "motorcycles. Maintenance-free design with superior cold-cranking amperage "
            "ensures reliable starting in Pakistan's hot summers and cold winters. "
            "Leak-proof construction with AGM technology. Includes electrolyte pack."
        ),
        "price":          "2800.00",
        "discount_price": "2499.00",
        "stock":          45,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "battery",
        "weight_grams":        1800,
        "low_stock_threshold": 10,
        "specifications": [
            {"name": "Voltage",      "value": "12",               "unit": "V",   "display_order": 0},
            {"name": "Capacity",     "value": "5",                "unit": "Ah",  "display_order": 1},
            {"name": "Technology",   "value": "AGM Maintenance-Free",            "display_order": 2},
            {"name": "CCA",          "value": "80",               "unit": "A",   "display_order": 3},
            {"name": "Dimensions",   "value": "120×60×130",       "unit": "mm",  "display_order": 4},
        ],
    },
    {
        "name":        "Yuasa YTX7A-BS 12V MF Battery for 150cc Bikes",
        "sku":         "BAT-YUA-002",
        "category":    "Batteries",
        "brand":       "Yuasa",
        "compatible_bikes": [
            "Honda CB150F", "Suzuki GS150", "Suzuki GR150", "Yamaha YBR125"
        ],
        "description": (
            "Yuasa YTX7A-BS Maintenance-Free 12V 6Ah battery. Sealed AGM technology "
            "prevents acid spillage. Factory-activated and ready to install. Ideal for "
            "150cc bikes running in city traffic in Lahore, Karachi, and Islamabad. "
            "Provides 200+ cold cranking amps for fast, reliable engine starts."
        ),
        "price":          "3500.00",
        "discount_price": "3199.00",
        "stock":          30,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "battery",
        "weight_grams":        2200,
        "low_stock_threshold": 8,
        "specifications": [
            {"name": "Voltage",    "value": "12",               "unit": "V",  "display_order": 0},
            {"name": "Capacity",   "value": "6",                "unit": "Ah", "display_order": 1},
            {"name": "Technology", "value": "AGM Maintenance-Free",           "display_order": 2},
            {"name": "CCA",        "value": "200",              "unit": "A",  "display_order": 3},
            {"name": "Dimensions", "value": "150×87×93",        "unit": "mm", "display_order": 4},
        ],
    },
    {
        "name":        "Standard 6V 4Ah Battery for Honda CD70",
        "sku":         "BAT-LOC-003",
        "category":    "Batteries",
        "brand":       "Honda",
        "compatible_bikes": ["Honda CD70", "Road Prince RP 70", "Superpower SP 70"],
        "description": (
            "OEM-compatible 6 Volt 4Ah conventional lead-acid battery for Honda CD70 "
            "and similar 70cc commuter bikes. Standard wet-cell battery with high "
            "charge retention. Widely used across Pakistan's most popular commuter "
            "motorcycle. Comes pre-filled with electrolyte. Terminal layout matches "
            "factory specification."
        ),
        "price":          "1200.00",
        "discount_price": None,
        "stock":          80,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "battery",
        "weight_grams":        1500,
        "low_stock_threshold": 15,
        "specifications": [
            {"name": "Voltage",         "value": "6",                "unit": "V",  "display_order": 0},
            {"name": "Capacity",        "value": "4",                "unit": "Ah", "display_order": 1},
            {"name": "Technology",      "value": "Conventional Wet Cell",         "display_order": 2},
            {"name": "Terminal Layout", "value": "Positive Left",                 "display_order": 3},
            {"name": "Dimensions",      "value": "100×57×113",       "unit": "mm", "display_order": 4},
        ],
    },
    {
        "name":        "Osaka 12V 9Ah Heavy Duty Bike Battery",
        "sku":         "BAT-OSK-004",
        "category":    "Batteries",
        "brand":       "Superpower",
        "compatible_bikes": [
            "Suzuki GS150", "Suzuki GS150SE", "Honda CB150F", "Yamaha YZF-R15"
        ],
        "description": (
            "Osaka heavy-duty 12V 9Ah battery engineered for high-performance 150cc+ "
            "motorcycles. Double-lid construction for extra safety. Vibration-resistant "
            "plates extend battery life on rough Pakistani roads. Suitable for electric "
            "start bikes with heavy accessory loads such as USB chargers and LED lights."
        ),
        "price":          "4200.00",
        "discount_price": "3800.00",
        "stock":          20,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "battery",
        "weight_grams":        3200,
        "low_stock_threshold": 5,
        "specifications": [
            {"name": "Voltage",              "value": "12",             "unit": "V",  "display_order": 0},
            {"name": "Capacity",             "value": "9",              "unit": "Ah", "display_order": 1},
            {"name": "Technology",           "value": "AGM Double-Lid",              "display_order": 2},
            {"name": "Vibration Resistance", "value": "High",                        "display_order": 3},
            {"name": "Dimensions",           "value": "152×88×107",     "unit": "mm", "display_order": 4},
        ],
    },
    {
        "name":        "AGS 12V 2.5Ah Nano Gel Battery for 70cc–100cc",
        "sku":         "BAT-AGS-005",
        "category":    "Batteries",
        "brand":       "United",
        "compatible_bikes": [
            "Honda CD70", "United US 100", "Road Prince RP 70", "Superpower SP 70"
        ],
        "description": (
            "AGS Nano Gel 12V 2.5Ah ultra-compact maintenance-free battery designed "
            "for 70cc to 100cc motorcycles. Gel electrolyte technology ensures zero "
            "spillage and longer shelf life. Perfect replacement for OEM battery on "
            "Honda CD70, United US 100, and Road Prince RP 70. Arrives charged."
        ),
        "price":          "1800.00",
        "discount_price": "1650.00",
        "stock":          60,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "battery",
        "weight_grams":        1200,
        "low_stock_threshold": 12,
        "specifications": [
            {"name": "Voltage",    "value": "12",           "unit": "V",  "display_order": 0},
            {"name": "Capacity",   "value": "2.5",          "unit": "Ah", "display_order": 1},
            {"name": "Technology", "value": "Nano Gel (Maintenance-Free)",  "display_order": 2},
            {"name": "Dimensions", "value": "113×70×85",   "unit": "mm", "display_order": 3},
        ],
    },
    {
        "name":        "Exide 12V 7Ah MF Battery — Universal 125cc",
        "sku":         "BAT-EXD-006",
        "category":    "Batteries",
        "brand":       "Honda",
        "compatible_bikes": [
            "Honda CG125", "Honda CG125S", "Yamaha YBR125", "Yamaha Saluto 125"
        ],
        "description": (
            "Exide 12V 7Ah maintenance-free battery compatible with most 125cc "
            "motorcycles sold in Pakistan. AGM technology delivers consistent power. "
            "18-month warranty against manufacturing defects. Terminal: positive left, "
            "negative right — matches CG125 and YBR125 trays without modification."
        ),
        "price":          "3200.00",
        "discount_price": "2900.00",
        "stock":          35,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "battery",
        "weight_grams":        2500,
        "low_stock_threshold": 8,
        "specifications": [
            {"name": "Voltage",         "value": "12",               "unit": "V",  "display_order": 0},
            {"name": "Capacity",        "value": "7",                "unit": "Ah", "display_order": 1},
            {"name": "Technology",      "value": "AGM Maintenance-Free",           "display_order": 2},
            {"name": "Terminal",        "value": "Positive Left",                  "display_order": 3},
            {"name": "Warranty",        "value": "18 months",                      "display_order": 4},
        ],
    },

    # ── BRAKE SYSTEM ───────────────────────────────────────────────────────────
    {
        "name":        "Honda CG125 Front Disc Brake Pad Set (OEM Grade)",
        "sku":         "BRK-HND-001",
        "category":    "Disc Brakes",
        "brand":       "Honda",
        "compatible_bikes": ["Honda CG125", "Honda CG125S", "Honda CB125F"],
        "description": (
            "OEM-grade front disc brake pad set for Honda CG125. Semi-metallic compound "
            "provides excellent stopping power in wet and dry conditions. Low dust "
            "formulation keeps wheel rims clean. Includes 2 pads, mounting hardware, "
            "and anti-squeal shims. Replace every 10,000 km or when thickness < 2mm."
        ),
        "price":          "850.00",
        "discount_price": "750.00",
        "stock":          100,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "brake",
        "weight_grams":        250,
        "low_stock_threshold": 20,
        "specifications": [
            {"name": "Material",       "value": "Semi-Metallic",             "display_order": 0},
            {"name": "Pad Thickness",  "value": "12",        "unit": "mm",   "display_order": 1},
            {"name": "Min Thickness",  "value": "2",         "unit": "mm",   "display_order": 2},
            {"name": "Position",       "value": "Front",                     "display_order": 3},
            {"name": "Contents",       "value": "2 pads + hardware + shims", "display_order": 4},
        ],
    },
    {
        "name":        "Yamaha YBR125 Rear Drum Brake Shoe Assembly",
        "sku":         "BRK-YAM-002",
        "category":    "Drum Brakes",
        "brand":       "Yamaha",
        "compatible_bikes": ["Yamaha YBR125", "Yamaha YBR125G", "Yamaha Saluto 125"],
        "description": (
            "Genuine-quality rear drum brake shoe set for Yamaha YBR125. High-friction "
            "lining bonded to heavy-gauge steel shoe. Fade-resistant compound rated to "
            "300°C. Direct drop-in replacement. Includes both leading and trailing "
            "shoes. Sold as a complete axle set."
        ),
        "price":          "650.00",
        "discount_price": None,
        "stock":          75,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "brake",
        "weight_grams":        300,
        "low_stock_threshold": 15,
        "specifications": [
            {"name": "Material",  "value": "High-Friction Bonded Lining",        "display_order": 0},
            {"name": "Max Temp",  "value": "300",          "unit": "°C",         "display_order": 1},
            {"name": "Position",  "value": "Rear",                               "display_order": 2},
            {"name": "Contents",  "value": "Leading + Trailing shoes (full set)", "display_order": 3},
        ],
    },
    {
        "name":        "Suzuki GS150 Front Brake Disc Rotor 260mm",
        "sku":         "BRK-SUZ-003",
        "category":    "Disc Brakes",
        "brand":       "Suzuki",
        "compatible_bikes": ["Suzuki GS150", "Suzuki GS150SE", "Suzuki GR150"],
        "description": (
            "High-carbon steel 260mm front brake disc rotor for Suzuki GS150. "
            "Cross-drilled and slotted design improves heat dissipation and wet-weather "
            "performance. Precision balanced to eliminate brake judder. "
            "Thickness: 4.0mm new, minimum 3.5mm. Fits OEM caliper."
        ),
        "price":          "2200.00",
        "discount_price": "1999.00",
        "stock":          40,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "brake",
        "weight_grams":        800,
        "low_stock_threshold": 8,
        "specifications": [
            {"name": "Material",          "value": "High-Carbon Steel",          "display_order": 0},
            {"name": "Diameter",          "value": "260",     "unit": "mm",      "display_order": 1},
            {"name": "Thickness (New)",   "value": "4.0",     "unit": "mm",      "display_order": 2},
            {"name": "Min Thickness",     "value": "3.5",     "unit": "mm",      "display_order": 3},
            {"name": "Design",            "value": "Cross-Drilled & Slotted",    "display_order": 4},
        ],
    },
    {
        "name":        "Honda CD70 Complete Drum Brake Assembly — Front & Rear",
        "sku":         "BRK-HND-004",
        "category":    "Drum Brakes",
        "brand":       "Honda",
        "compatible_bikes": ["Honda CD70", "Road Prince RP 70", "Superpower SP 70"],
        "description": (
            "Full front and rear drum brake assembly kit for Honda CD70. Includes "
            "brake drums, brake shoes (4 pieces), return springs, cam shafts, and "
            "brake cables. Ideal for complete brake system restoration. All components "
            "manufactured to Honda specifications."
        ),
        "price":          "1800.00",
        "discount_price": "1600.00",
        "stock":          55,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "brake",
        "weight_grams":        2000,
        "low_stock_threshold": 10,
        "specifications": [
            {"name": "Position", "value": "Front & Rear",                                         "display_order": 0},
            {"name": "Contents", "value": "2 drums + 4 shoes + springs + cam shafts + cables",    "display_order": 1},
            {"name": "Standard", "value": "Honda OEM specification",                              "display_order": 2},
        ],
    },
    {
        "name":        "Universal Hydraulic Brake Lever Set — CNC Aluminium",
        "sku":         "BRK-UNI-005",
        "category":    "Disc Brakes",
        "brand":       "Superpower",
        "compatible_bikes": [
            "Honda CB150F", "Yamaha YZF-R15", "Suzuki GR150", "Ravi Wolf 150"
        ],
        "description": (
            "CNC-machined aluminium hydraulic brake and clutch lever set. Compatible "
            "with 22mm handlebars. 5-position adjustable reach dial. Anodised black "
            "finish. Works on most 150cc+ motorcycles. Bolt-on installation with "
            "standard 8mm pivot bolt. Pair sold together."
        ),
        "price":          "1450.00",
        "discount_price": "1299.00",
        "stock":          60,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "brake",
        "weight_grams":        350,
        "low_stock_threshold": 12,
        "specifications": [
            {"name": "Material",           "value": "CNC Aluminium (Anodised Black)", "display_order": 0},
            {"name": "Handlebar Diameter", "value": "22",    "unit": "mm",            "display_order": 1},
            {"name": "Reach Adjustment",   "value": "5-position dial",                "display_order": 2},
            {"name": "Pivot Bolt",         "value": "8",     "unit": "mm",            "display_order": 3},
            {"name": "Contents",           "value": "Brake + clutch lever (pair)",    "display_order": 4},
        ],
    },
    {
        "name":        "Brake Master Cylinder Rebuild Kit — 125cc–150cc",
        "sku":         "BRK-MKT-006",
        "category":    "Disc Brakes",
        "brand":       "Honda",
        "compatible_bikes": [
            "Honda CG125", "Honda CB125F", "Honda CB150F", "Suzuki GS150"
        ],
        "description": (
            "Complete master cylinder rebuild kit: piston cup, dust seal, spring, and "
            "circlip. Restores proper brake fluid pressure and pedal feel. Use every "
            "2 years or when brake fluid becomes discoloured. Compatible with standard "
            "14mm bore master cylinders on Honda and Suzuki 125cc–150cc bikes."
        ),
        "price":          "420.00",
        "discount_price": None,
        "stock":          90,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "brake",
        "weight_grams":        80,
        "low_stock_threshold": 15,
        "specifications": [
            {"name": "Bore",          "value": "14",   "unit": "mm",                          "display_order": 0},
            {"name": "Contents",      "value": "Piston cup + dust seal + spring + circlip",   "display_order": 1},
            {"name": "Compatibility", "value": "Honda & Suzuki 125cc–150cc",                   "display_order": 2},
        ],
    },

    # ── TRANSMISSION — CHAIN & SPROCKET ────────────────────────────────────────
    {
        "name":        "DID 420D Standard Drive Chain 116 Links — Honda CD70",
        "sku":         "CHN-DID-001",
        "category":    "Drive Chain & Sprocket",
        "brand":       "DID",
        "compatible_bikes": ["Honda CD70", "Road Prince RP 70", "Superpower SP 70"],
        "description": (
            "DID 420D standard roller chain, 116 links — most popular size for 70cc "
            "bikes in Pakistan. Tensile strength 14.7 kN. Pre-lubricated. Includes "
            "connecting link. Replace every 10,000 km or when slack exceeds 20mm. "
            "Suits standard 17T front / 38T rear sprocket on Honda CD70."
        ),
        "price":          "1100.00",
        "discount_price": "980.00",
        "stock":          120,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "chain",
        "weight_grams":        600,
        "low_stock_threshold": 20,
        "specifications": [
            {"name": "Pitch",            "value": "420",          "display_order": 0},
            {"name": "Links",            "value": "116",          "display_order": 1},
            {"name": "Tensile Strength", "value": "14.7", "unit": "kN", "display_order": 2},
            {"name": "Type",             "value": "Standard Roller (Pre-lubricated)", "display_order": 3},
            {"name": "Includes",         "value": "Connecting link", "display_order": 4},
        ],
    },
    {
        "name":        "DID 428H Heavy-Duty O-Ring Chain 120 Links — 125cc",
        "sku":         "CHN-DID-002",
        "category":    "Drive Chain & Sprocket",
        "brand":       "DID",
        "compatible_bikes": [
            "Honda CG125", "Honda CG125S", "Honda CB125F", "Yamaha YBR125"
        ],
        "description": (
            "DID 428H heavy-duty O-ring drive chain, 120 links. O-ring seals retain "
            "grease, tripling chain life vs standard chains. Tensile strength 18.6 kN. "
            "Gold colour with DID branding. Clip-type master link included. Ideal "
            "for daily commuters on GT Road."
        ),
        "price":          "2400.00",
        "discount_price": "2150.00",
        "stock":          85,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "chain",
        "weight_grams":        750,
        "low_stock_threshold": 15,
        "specifications": [
            {"name": "Pitch",            "value": "428H",         "display_order": 0},
            {"name": "Links",            "value": "120",          "display_order": 1},
            {"name": "Tensile Strength", "value": "18.6", "unit": "kN", "display_order": 2},
            {"name": "Type",             "value": "O-Ring",       "display_order": 3},
            {"name": "Colour",           "value": "Gold",         "display_order": 4},
            {"name": "Includes",         "value": "Clip-type master link", "display_order": 5},
        ],
    },
    {
        "name":        "Suzuki GS150 Complete Chain & Sprocket Kit",
        "sku":         "CHN-SUZ-003",
        "category":    "Drive Chain & Sprocket",
        "brand":       "Suzuki",
        "compatible_bikes": ["Suzuki GS150", "Suzuki GS150SE", "Suzuki GR150"],
        "description": (
            "Complete drivetrain kit for Suzuki GS150: DID 428H 120-link O-ring chain, "
            "15T front sprocket, 42T rear sprocket, and all mounting hardware. "
            "Case-hardened steel sprockets. Recommended when bike exceeds 15,000 km "
            "since last replacement."
        ),
        "price":          "3800.00",
        "discount_price": "3499.00",
        "stock":          40,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "chain",
        "weight_grams":        1800,
        "low_stock_threshold": 8,
        "specifications": [
            {"name": "Chain Pitch",      "value": "428H",         "display_order": 0},
            {"name": "Chain Links",      "value": "120",          "display_order": 1},
            {"name": "Front Sprocket",   "value": "15T",          "display_order": 2},
            {"name": "Rear Sprocket",    "value": "42T",          "display_order": 3},
            {"name": "Chain Type",       "value": "O-Ring",       "display_order": 4},
        ],
    },
    {
        "name":        "Honda CB150F Rear Sprocket 38T — Heavy Gauge Steel",
        "sku":         "CHN-HND-004",
        "category":    "Drive Chain & Sprocket",
        "brand":       "Honda",
        "compatible_bikes": ["Honda CB150F", "Honda CB125F"],
        "description": (
            "OEM-specification 38-tooth rear sprocket for Honda CB150F. CNC-machined "
            "tooth profile. Centre bore 130mm, 5 × 10.5mm bolt holes on 145mm PCD. "
            "Surface hardened HRC 50–55. Sold individually."
        ),
        "price":          "1200.00",
        "discount_price": None,
        "stock":          65,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "chain",
        "weight_grams":        900,
        "low_stock_threshold": 10,
        "specifications": [
            {"name": "Teeth",        "value": "38T",          "display_order": 0},
            {"name": "Centre Bore",  "value": "130", "unit": "mm", "display_order": 1},
            {"name": "PCD",          "value": "145", "unit": "mm", "display_order": 2},
            {"name": "Bolt Holes",   "value": "5×10.5mm",     "display_order": 3},
            {"name": "Hardness",     "value": "HRC 50–55",    "display_order": 4},
        ],
    },
    {
        "name":        "Yamaha YBR125 Chain Tensioner & Guide Roller Set",
        "sku":         "CHN-YAM-005",
        "category":    "Drive Chain & Sprocket",
        "brand":       "Yamaha",
        "compatible_bikes": ["Yamaha YBR125", "Yamaha YBR125G", "Yamaha Saluto 125"],
        "description": (
            "OEM-compatible chain tensioner block and guide roller set for Yamaha "
            "YBR125. Hard-wearing nylon slider resists heat and oil. Prevents chain "
            "whip and reduces noise. Includes tensioner bolt, lock nut, and replacement "
            "guide rubber."
        ),
        "price":          "650.00",
        "discount_price": "580.00",
        "stock":          70,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "chain",
        "weight_grams":        200,
        "low_stock_threshold": 12,
        "specifications": [
            {"name": "Material",  "value": "Hard-Wearing Nylon Slider",                     "display_order": 0},
            {"name": "Contents",  "value": "Tensioner block + guide roller + bolt + lock nut", "display_order": 1},
        ],
    },
    {
        "name":        "Universal 420 Chain Master Link Clip Type — Pack of 10",
        "sku":         "CHN-UNI-006",
        "category":    "Drive Chain & Sprocket",
        "brand":       "DID",
        "compatible_bikes": [
            "Honda CD70", "United US 100", "Road Prince RP 70",
            "Dayang DY 125", "Superpower SP 70"
        ],
        "description": (
            "Pack of 10 DID 420-size clip-type master links for fast chain joining. "
            "Hardened steel side plates and spring clip. Essential spare for long-distance "
            "riders. Clip direction must face opposite to chain travel for safety."
        ),
        "price":          "350.00",
        "discount_price": None,
        "stock":          200,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "chain",
        "weight_grams":        150,
        "low_stock_threshold": 30,
        "specifications": [
            {"name": "Chain Size", "value": "420",              "display_order": 0},
            {"name": "Type",       "value": "Clip-type Master Link", "display_order": 1},
            {"name": "Material",   "value": "Hardened Steel",   "display_order": 2},
            {"name": "Pack",       "value": "10 pieces",        "display_order": 3},
        ],
    },

    # ── TYRES & TUBES ──────────────────────────────────────────────────────────
    {
        "name":        "Dunlop D102 2.50-17 Front Tyre — CD70 / CG125",
        "sku":         "TYR-DUN-001",
        "category":    "Tyres & Tubes",
        "brand":       "Dunlop",
        "compatible_bikes": ["Honda CD70", "Honda CG125", "Road Prince RP 70"],
        "description": (
            "Dunlop D102 2.50-17 4-ply front tyre. Ribbed centre groove for straight-line "
            "stability. Compound for hot Asian climates. Load index 38 (170 kg). "
            "Speed rating P (150 km/h). TT type — requires inner tube."
        ),
        "price":          "2200.00",
        "discount_price": "1999.00",
        "stock":          60,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "tyre",
        "weight_grams":        3000,
        "low_stock_threshold": 10,
        "specifications": [
            {"name": "Size",         "value": "2.50-17",          "display_order": 0},
            {"name": "Ply",          "value": "4PR",              "display_order": 1},
            {"name": "Type",         "value": "Tube-Type (TT)",   "display_order": 2},
            {"name": "Load Index",   "value": "38 (170 kg)",      "display_order": 3},
            {"name": "Speed Rating", "value": "P (150 km/h)",     "display_order": 4},
        ],
    },
    {
        "name":        "Dunlop D102 3.00-17 Rear Tyre — CG125 / YBR125",
        "sku":         "TYR-DUN-002",
        "category":    "Tyres & Tubes",
        "brand":       "Dunlop",
        "compatible_bikes": ["Honda CG125", "Honda CG125S", "Yamaha YBR125"],
        "description": (
            "Dunlop D102 3.00-17 6-ply rear tyre. Block pattern for grip on wet roads "
            "and gravel. Reinforced sidewall resists cuts. Load index 50 (190 kg). "
            "Speed rating P (150 km/h). TT type."
        ),
        "price":          "2800.00",
        "discount_price": "2600.00",
        "stock":          50,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "tyre",
        "weight_grams":        4000,
        "low_stock_threshold": 10,
        "specifications": [
            {"name": "Size",         "value": "3.00-17",          "display_order": 0},
            {"name": "Ply",          "value": "6PR",              "display_order": 1},
            {"name": "Type",         "value": "Tube-Type (TT)",   "display_order": 2},
            {"name": "Load Index",   "value": "50 (190 kg)",      "display_order": 3},
            {"name": "Speed Rating", "value": "P (150 km/h)",     "display_order": 4},
        ],
    },
    {
        "name":        "Innova IA-2606 100/80-17 Tubeless Tyre — CB150F / GS150",
        "sku":         "TYR-INV-003",
        "category":    "Tyres & Tubes",
        "brand":       "Innova",
        "compatible_bikes": [
            "Honda CB150F", "Suzuki GS150", "Suzuki GR150", "Ravi Wolf 150"
        ],
        "description": (
            "Innova IA-2606 100/80-17 tubeless rear tyre. Asymmetric tread for mixed "
            "urban/highway riding. Silica-enhanced compound for wet traction. TL — fits "
            "alloy wheels. Load index 52 (200 kg). Speed rating H (210 km/h). "
            "Recommended inflation: 28 PSI rear."
        ),
        "price":          "4500.00",
        "discount_price": "4200.00",
        "stock":          35,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "tyre",
        "weight_grams":        4500,
        "low_stock_threshold": 7,
        "specifications": [
            {"name": "Size",                 "value": "100/80-17",      "display_order": 0},
            {"name": "Type",                 "value": "Tubeless (TL)",  "display_order": 1},
            {"name": "Load Index",           "value": "52 (200 kg)",    "display_order": 2},
            {"name": "Speed Rating",         "value": "H (210 km/h)",   "display_order": 3},
            {"name": "Recommended Pressure", "value": "28", "unit": "PSI", "display_order": 4},
        ],
    },
    {
        "name":        "IRC NR73 2.75-17 Rear Tyre — Universal 100cc–125cc",
        "sku":         "TYR-IRC-004",
        "category":    "Tyres & Tubes",
        "brand":       "United",
        "compatible_bikes": [
            "United US 100", "United US 125", "Dayang DY 125",
            "Road Prince RP 125", "Honda CG125"
        ],
        "description": (
            "IRC NR73 2.75-17 4-ply tube-type rear tyre. Rib-and-block pattern balances "
            "straight-line stability with corner grip. ISO 4223 standard. Popular factory "
            "fitment on many Pakistani 100cc–125cc motorcycles."
        ),
        "price":          "2100.00",
        "discount_price": None,
        "stock":          90,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "tyre",
        "weight_grams":        3500,
        "low_stock_threshold": 15,
        "specifications": [
            {"name": "Size",    "value": "2.75-17",             "display_order": 0},
            {"name": "Ply",     "value": "4PR",                 "display_order": 1},
            {"name": "Type",    "value": "Tube-Type (TT)",      "display_order": 2},
            {"name": "Pattern", "value": "Rib-and-Block",       "display_order": 3},
            {"name": "Standard","value": "ISO 4223",            "display_order": 4},
        ],
    },
    {
        "name":        "Butyl Inner Tube 2.50/2.75-17 — Pack of 2",
        "sku":         "TYR-TUB-005",
        "category":    "Tyres & Tubes",
        "brand":       "Honda",
        "compatible_bikes": [
            "Honda CD70", "Honda CG125", "Yamaha YBR125",
            "United US 100", "Road Prince RP 70"
        ],
        "description": (
            "Premium butyl rubber inner tubes size 2.50/2.75-17. Dual-size fitment "
            "covers both 70cc and 125cc tyre widths. Straight TR4 valve stem. Uniform "
            "wall thickness prevents blow-outs. Pack of 2 for front and rear."
        ),
        "price":          "700.00",
        "discount_price": "620.00",
        "stock":          150,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "tyre",
        "weight_grams":        600,
        "low_stock_threshold": 25,
        "specifications": [
            {"name": "Size",     "value": "2.50/2.75-17",       "display_order": 0},
            {"name": "Material", "value": "Butyl Rubber",       "display_order": 1},
            {"name": "Valve",    "value": "TR4 (Straight)",     "display_order": 2},
            {"name": "Pack",     "value": "2 tubes",            "display_order": 3},
        ],
    },
    {
        "name":        "Yamaha YZF-R15 110/70-17 Front Tubeless Tyre",
        "sku":         "TYR-YAM-006",
        "category":    "Tyres & Tubes",
        "brand":       "Yamaha",
        "compatible_bikes": ["Yamaha YZF-R15"],
        "description": (
            "High-performance 110/70-17 front tubeless tyre for YZF-R15. Sporty tread "
            "with large shoulder blocks for lean-angle grip. Load index 54 (212 kg). "
            "Speed rating V (240 km/h). TL — fits 17-inch alloy rim. "
            "Recommended front pressure: 26 PSI."
        ),
        "price":          "6500.00",
        "discount_price": "5999.00",
        "stock":          20,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "tyre",
        "weight_grams":        4000,
        "low_stock_threshold": 5,
        "specifications": [
            {"name": "Size",                 "value": "110/70-17",       "display_order": 0},
            {"name": "Type",                 "value": "Tubeless (TL)",   "display_order": 1},
            {"name": "Load Index",           "value": "54 (212 kg)",     "display_order": 2},
            {"name": "Speed Rating",         "value": "V (240 km/h)",    "display_order": 3},
            {"name": "Recommended Pressure", "value": "26", "unit": "PSI", "display_order": 4},
        ],
    },

    # ── ENGINE PARTS ───────────────────────────────────────────────────────────
    {
        "name":        "Honda CG125 Complete Engine Gasket Set",
        "sku":         "ENG-HND-001",
        "category":    "Engine Parts",
        "brand":       "Honda",
        "compatible_bikes": ["Honda CG125", "Honda CG125S"],
        "description": (
            "Full engine gasket kit for Honda CG125: cylinder head gasket, cylinder "
            "base gasket, crankcase gasket, rocker cover gasket, exhaust gasket, and "
            "all O-rings. OEM-equivalent ratings. Covers complete engine teardown — "
            "no additional gaskets needed."
        ),
        "price":          "1800.00",
        "discount_price": "1650.00",
        "stock":          55,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "engine",
        "weight_grams":        400,
        "low_stock_threshold": 10,
        "specifications": [
            {"name": "Standard",  "value": "OEM-equivalent",                                                      "display_order": 0},
            {"name": "Contents",  "value": "Head + base + crankcase + rocker + exhaust gaskets + all O-rings",    "display_order": 1},
            {"name": "Coverage",  "value": "Complete engine teardown",                                            "display_order": 2},
        ],
    },
    {
        "name":        "Yamaha YBR125 Piston Kit — Standard Bore 54mm",
        "sku":         "ENG-YAM-002",
        "category":    "Pistons & Rings",
        "brand":       "Yamaha",
        "compatible_bikes": ["Yamaha YBR125", "Yamaha YBR125G", "Yamaha Saluto 125"],
        "description": (
            "Standard bore 54.00mm piston kit for Yamaha YBR125. Includes forged "
            "aluminium piston, 2× compression rings, 1× oil control ring, wrist pin, "
            "and circlips. Flat-top design maintains stock 9.5:1 compression ratio. "
            "Install with new cylinder base gasket."
        ),
        "price":          "2500.00",
        "discount_price": "2300.00",
        "stock":          40,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "engine",
        "weight_grams":        450,
        "low_stock_threshold": 8,
        "specifications": [
            {"name": "Bore",               "value": "54.00", "unit": "mm",                                       "display_order": 0},
            {"name": "Compression Ratio",  "value": "9.5:1",                                                     "display_order": 1},
            {"name": "Material",           "value": "Forged Aluminium",                                          "display_order": 2},
            {"name": "Contents",           "value": "Piston + 2× comp rings + 1× oil ring + wrist pin + clips", "display_order": 3},
        ],
    },
    {
        "name":        "Honda CD70 Carburettor Assembly PD18J",
        "sku":         "ENG-HND-003",
        "category":    "Carburettors",
        "brand":       "Honda",
        "compatible_bikes": ["Honda CD70"],
        "description": (
            "OEM-grade PD18J slide-type carburettor for Honda CD70. Includes carburettor "
            "body, float bowl, main jet (72), pilot jet (38), needle valve, throttle "
            "slide, choke plate, and air-fuel screw. Improves fuel economy vs worn "
            "originals. Standard 18mm inlet manifold fitment."
        ),
        "price":          "1600.00",
        "discount_price": "1450.00",
        "stock":          70,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "engine",
        "weight_grams":        800,
        "low_stock_threshold": 12,
        "specifications": [
            {"name": "Type",       "value": "Slide-type (PD18J)",  "display_order": 0},
            {"name": "Inlet",      "value": "18", "unit": "mm",    "display_order": 1},
            {"name": "Main Jet",   "value": "72",                  "display_order": 2},
            {"name": "Pilot Jet",  "value": "38",                  "display_order": 3},
        ],
    },
    {
        "name":        "NGK CR7HSA Spark Plug — Universal 125cc–150cc",
        "sku":         "ENG-NGK-004",
        "category":    "Engine Parts",
        "brand":       "NGK",
        "compatible_bikes": [
            "Honda CG125", "Honda CB125F", "Honda CB150F",
            "Yamaha YBR125", "Suzuki GS150"
        ],
        "description": (
            "NGK CR7HSA copper core spark plug. Most widely used plug across Pakistan's "
            "125cc–150cc fleet. Thread M10 × 1.0, reach 19mm, hex 16mm. Pre-gapped "
            "0.6–0.7mm. Trivalent metal plating prevents seizing in aluminium heads. "
            "Replace every 6,000 km."
        ),
        "price":          "380.00",
        "discount_price": None,
        "stock":          300,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "engine",
        "weight_grams":        50,
        "low_stock_threshold": 50,
        "specifications": [
            {"name": "Thread", "value": "M10×1.0",        "display_order": 0},
            {"name": "Reach",  "value": "19", "unit": "mm", "display_order": 1},
            {"name": "Hex",    "value": "16", "unit": "mm", "display_order": 2},
            {"name": "Gap",    "value": "0.6–0.7", "unit": "mm", "display_order": 3},
            {"name": "Core",   "value": "Copper",          "display_order": 4},
        ],
    },
    {
        "name":        "Suzuki GS150 Air Filter Element — OEM Replacement",
        "sku":         "ENG-SUZ-005",
        "category":    "Filters",
        "brand":       "Suzuki",
        "compatible_bikes": ["Suzuki GS150", "Suzuki GS150SE"],
        "description": (
            "OEM-equivalent paper air filter for Suzuki GS150. Multi-layer filtration "
            "removes 99.5% of dust particles >= 10 microns — critical for dusty Punjab "
            "and Sindh conditions. Replace every 6,000 km in dust, 12,000 km on clean "
            "roads. Direct fit into original air box."
        ),
        "price":          "550.00",
        "discount_price": "499.00",
        "stock":          110,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "engine",
        "weight_grams":        300,
        "low_stock_threshold": 20,
        "specifications": [
            {"name": "Filtration",            "value": "99.5% (≥10 micron)",          "display_order": 0},
            {"name": "Layers",                "value": "Multi-layer paper",            "display_order": 1},
            {"name": "Interval (dusty)",      "value": "6,000", "unit": "km",         "display_order": 2},
            {"name": "Interval (clean road)", "value": "12,000", "unit": "km",        "display_order": 3},
        ],
    },
    {
        "name":        "Honda CB150F Clutch Plate Set — Full Kit",
        "sku":         "ENG-HND-006",
        "category":    "Clutch Parts",
        "brand":       "Honda",
        "compatible_bikes": ["Honda CB150F", "Honda CB125F"],
        "description": (
            "Complete wet clutch plate set for Honda CB150F: 4x friction plates, "
            "4x steel drive plates, 1x pressure plate. Friction material rated to "
            "200°C. Eliminates clutch slip under acceleration and drag in traffic. "
            "Soak friction plates in 10W-40 oil 24 hours before installation."
        ),
        "price":          "3200.00",
        "discount_price": "2899.00",
        "stock":          30,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "engine",
        "weight_grams":        600,
        "low_stock_threshold": 6,
        "specifications": [
            {"name": "Type",             "value": "Wet Clutch",                              "display_order": 0},
            {"name": "Friction Plates",  "value": "4×",                                      "display_order": 1},
            {"name": "Steel Plates",     "value": "4×",                                      "display_order": 2},
            {"name": "Pressure Plate",   "value": "1×",                                      "display_order": 3},
            {"name": "Max Temp",         "value": "200", "unit": "°C",                       "display_order": 4},
        ],
    },

    # ── ELECTRICAL & LIGHTS ────────────────────────────────────────────────────
    {
        "name":        "Honda CD70 / CG125 12V 35W Halogen Headlight Bulb",
        "sku":         "LGT-HND-001",
        "category":    "Headlights",
        "brand":       "Honda",
        "compatible_bikes": ["Honda CD70", "Honda CG125", "Honda CG125S"],
        "description": (
            "12V 35/35W H4 halogen headlight bulb for Honda CD70 and CG125. "
            "3-pin P15D-25-3 base. 450 lumens for safe night-time visibility. "
            "500-hour rated life. Pair sold — one for the bike, one spare. "
            "Fits OEM housing without modification."
        ),
        "price":          "220.00",
        "discount_price": None,
        "stock":          200,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "light",
        "weight_grams":        80,
        "low_stock_threshold": 30,
        "specifications": [
            {"name": "Voltage",      "value": "12",           "unit": "V",    "display_order": 0},
            {"name": "Wattage",      "value": "35/35",        "unit": "W",    "display_order": 1},
            {"name": "Base",         "value": "P15D-25-3 (3-pin H4)",         "display_order": 2},
            {"name": "Lumens",       "value": "450",          "unit": "lm",   "display_order": 3},
            {"name": "Rated Life",   "value": "500",          "unit": "hours","display_order": 4},
            {"name": "Pack",         "value": "Pair (2 bulbs)",               "display_order": 5},
        ],
    },
    {
        "name":        "Yamaha YBR125 LED Headlight Assembly 12V 18W",
        "sku":         "LGT-YAM-002",
        "category":    "Headlights",
        "brand":       "Yamaha",
        "compatible_bikes": ["Yamaha YBR125", "Yamaha YBR125G", "Yamaha Saluto 125"],
        "description": (
            "Plug-and-play LED headlight assembly for Yamaha YBR125. 18W producing "
            "1800 lumens — 4x brighter than stock halogen at half the power draw. "
            "6000K cool white. IP67 waterproof. Direct connector match — no wiring "
            "modification. Includes DRL daytime running strip."
        ),
        "price":          "2800.00",
        "discount_price": "2499.00",
        "stock":          45,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "light",
        "weight_grams":        600,
        "low_stock_threshold": 8,
        "specifications": [
            {"name": "Voltage",            "value": "12",    "unit": "V",  "display_order": 0},
            {"name": "Wattage",            "value": "18",    "unit": "W",  "display_order": 1},
            {"name": "Lumens",             "value": "1800",  "unit": "lm", "display_order": 2},
            {"name": "Colour Temperature", "value": "6000",  "unit": "K",  "display_order": 3},
            {"name": "IP Rating",          "value": "IP67",               "display_order": 4},
            {"name": "Includes",           "value": "DRL daytime running strip", "display_order": 5},
        ],
    },
    {
        "name":        "Universal 12V LED Indicator Set — Amber 4 pcs",
        "sku":         "LGT-UNI-003",
        "category":    "Indicators & Bulbs",
        "brand":       "Superpower",
        "compatible_bikes": [
            "Honda CG125", "Honda CB150F", "Yamaha YBR125",
            "Suzuki GS150", "United US 125"
        ],
        "description": (
            "4x LED turn-signal lights. 12V 2W each (replaces 10W bulbs). "
            "Amber lens, chrome housing. 10mm stem fits most indicator bosses. "
            "Compatible with standard flasher relays. IP54 splash proof."
        ),
        "price":          "850.00",
        "discount_price": "750.00",
        "stock":          80,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "light",
        "weight_grams":        400,
        "low_stock_threshold": 15,
        "specifications": [
            {"name": "Voltage",   "value": "12",     "unit": "V", "display_order": 0},
            {"name": "Wattage",   "value": "2 each", "unit": "W", "display_order": 1},
            {"name": "Lens",      "value": "Amber",               "display_order": 2},
            {"name": "Housing",   "value": "Chrome",              "display_order": 3},
            {"name": "Stem",      "value": "10",     "unit": "mm","display_order": 4},
            {"name": "IP Rating", "value": "IP54",               "display_order": 5},
            {"name": "Pack",      "value": "4 indicators",        "display_order": 6},
        ],
    },
    {
        "name":        "Suzuki GR150 Full LED Tail Light Assembly",
        "sku":         "LGT-SUZ-004",
        "category":    "Indicators & Bulbs",
        "brand":       "Suzuki",
        "compatible_bikes": ["Suzuki GR150", "Suzuki GS150SE"],
        "description": (
            "OEM-style full LED tail and brake light for Suzuki GR150. Brake light "
            "40cd; tail light 4cd — meets ECE R50. Direct bolt-on, same 3-pin connector. "
            "Smoked lens. Operating voltage 10-16V. Life 50,000 hours."
        ),
        "price":          "1800.00",
        "discount_price": "1650.00",
        "stock":          35,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "light",
        "weight_grams":        350,
        "low_stock_threshold": 7,
        "specifications": [
            {"name": "Voltage",       "value": "10–16",   "unit": "V",       "display_order": 0},
            {"name": "Brake Light",   "value": "40",      "unit": "cd",      "display_order": 1},
            {"name": "Tail Light",    "value": "4",       "unit": "cd",      "display_order": 2},
            {"name": "Connector",     "value": "3-pin (direct fit)",         "display_order": 3},
            {"name": "Standard",      "value": "ECE R50",                    "display_order": 4},
            {"name": "Rated Life",    "value": "50,000",  "unit": "hours",   "display_order": 5},
        ],
    },
    {
        "name":        "Honda CB150F Speedometer Cluster Assembly",
        "sku":         "LGT-HND-005",
        "category":    "Electrical & Lights",
        "brand":       "Honda",
        "compatible_bikes": ["Honda CB150F", "Honda CB125F"],
        "description": (
            "OEM-grade speedometer cluster for Honda CB150F. Includes analogue "
            "speedometer (0-160 km/h), fuel gauge, gear position indicator, and "
            "all tell-tales. Backlit for night reading. Cable-driven. Direct plug-in "
            "connector. Replace when face is cracked or needle is sticking."
        ),
        "price":          "4500.00",
        "discount_price": "4100.00",
        "stock":          20,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "light",
        "weight_grams":        1200,
        "low_stock_threshold": 4,
        "specifications": [
            {"name": "Speedometer Range", "value": "0–160", "unit": "km/h",                       "display_order": 0},
            {"name": "Drive",             "value": "Cable-driven",                                 "display_order": 1},
            {"name": "Includes",          "value": "Fuel gauge + gear indicator + all tell-tales", "display_order": 2},
            {"name": "Backlit",           "value": "Yes",                                          "display_order": 3},
        ],
    },
    {
        "name":        "Universal T10 W5W 12V 5W Parking Bulb — Pack of 10",
        "sku":         "LGT-UNI-006",
        "category":    "Indicators & Bulbs",
        "brand":       "NGK",
        "compatible_bikes": [
            "Honda CD70", "Honda CG125", "Yamaha YBR125",
            "Suzuki GS150", "United US 100", "Road Prince RP 125"
        ],
        "description": (
            "Pack of 10 T10 W5W 12V 5W halogen bulbs for instrument panel and "
            "position indicators. W2.1x9.5d wedge socket — fits most Pakistani "
            "motorcycles. Bulk pack for workshops. Push-in fitment."
        ),
        "price":          "180.00",
        "discount_price": None,
        "stock":          500,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "light",
        "weight_grams":        100,
        "low_stock_threshold": 50,
        "specifications": [
            {"name": "Voltage",  "value": "12",    "unit": "V", "display_order": 0},
            {"name": "Wattage",  "value": "5",     "unit": "W", "display_order": 1},
            {"name": "Type",     "value": "T10 W5W Halogen",    "display_order": 2},
            {"name": "Socket",   "value": "W2.1×9.5d (wedge)",  "display_order": 3},
            {"name": "Pack",     "value": "10 bulbs",           "display_order": 4},
        ],
    },

    # ── LUBRICATION & OILS ─────────────────────────────────────────────────────
    {
        "name":        "Castrol Power1 4T 10W-40 Engine Oil — 1 Litre",
        "sku":         "OIL-CAS-001",
        "category":    "Lubrication & Oils",
        "brand":       "Castrol",
        "compatible_bikes": [
            "Honda CG125", "Honda CB150F", "Yamaha YBR125",
            "Suzuki GS150", "Ravi Wolf 150"
        ],
        "description": (
            "Castrol Power1 4T 10W-40 fully synthetic engine oil. JASO MA2 certified. "
            "Covers Pakistan's full temperature range (-5C north to +48C Sindh). "
            "API SN. Trizone Technology protects engine, clutch, and gearbox. "
            "Change every 3,000 km or 3 months. 1-litre bottle."
        ),
        "price":          "1200.00",
        "discount_price": "1099.00",
        "stock":          200,
        "status":         "available",
        "is_featured":    True,
        "image_key":      "oil",
        "weight_grams":        1050,
        "low_stock_threshold": 30,
        "specifications": [
            {"name": "Viscosity",         "value": "10W-40",                     "display_order": 0},
            {"name": "Type",              "value": "Fully Synthetic",            "display_order": 1},
            {"name": "Standard",          "value": "JASO MA2 / API SN",         "display_order": 2},
            {"name": "Volume",            "value": "1", "unit": "litre",        "display_order": 3},
            {"name": "Change Interval",   "value": "3,000 km / 3 months",       "display_order": 4},
        ],
    },
    {
        "name":        "Castrol Power1 4T 20W-50 Engine Oil — 1 Litre",
        "sku":         "OIL-CAS-002",
        "category":    "Lubrication & Oils",
        "brand":       "Castrol",
        "compatible_bikes": [
            "Honda CD70", "Honda CG125", "United US 100",
            "Road Prince RP 70", "Dayang DY 125"
        ],
        "description": (
            "Castrol Power1 4T 20W-50 semi-synthetic. Higher viscosity preferred for "
            "older engines in Karachi and Multan summer heat. JASO MA spec. Excellent "
            "thermal stability in slow city traffic. Recommended for CD70 engines above "
            "30,000 km. 1-litre bottle with tamper-evident seal."
        ),
        "price":          "950.00",
        "discount_price": None,
        "stock":          180,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "oil",
        "weight_grams":        1020,
        "low_stock_threshold": 25,
        "specifications": [
            {"name": "Viscosity",       "value": "20W-50",              "display_order": 0},
            {"name": "Type",            "value": "Semi-Synthetic",      "display_order": 1},
            {"name": "Standard",        "value": "JASO MA",             "display_order": 2},
            {"name": "Volume",          "value": "1", "unit": "litre",  "display_order": 3},
        ],
    },
    {
        "name":        "Motigear Gear Oil 80W-90 GL-4 — 500ml",
        "sku":         "OIL-MTG-003",
        "category":    "Lubrication & Oils",
        "brand":       "Motigear",
        "compatible_bikes": [
            "Honda CG125", "Honda CB150F", "Yamaha YBR125",
            "Suzuki GS150", "Ravi Wolf 150"
        ],
        "description": (
            "Motigear 80W-90 GL-4 gear oil for separate-sump gearboxes. Extreme "
            "pressure additive protects gear teeth under high load. Anti-wear, anti-foam, "
            "oxidation inhibitors. 500ml — one gearbox oil change. Change every 10,000 km."
        ),
        "price":          "480.00",
        "discount_price": "420.00",
        "stock":          150,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "oil",
        "weight_grams":        550,
        "low_stock_threshold": 20,
        "specifications": [
            {"name": "Viscosity",       "value": "80W-90",               "display_order": 0},
            {"name": "Grade",           "value": "GL-4",                 "display_order": 1},
            {"name": "Type",            "value": "Gear Oil",             "display_order": 2},
            {"name": "Volume",          "value": "500", "unit": "ml",    "display_order": 3},
            {"name": "Change Interval", "value": "10,000", "unit": "km", "display_order": 4},
        ],
    },
    {
        "name":        "Honda OEM Chain Lubricant Spray — 150ml",
        "sku":         "OIL-HND-004",
        "category":    "Lubrication & Oils",
        "brand":       "Honda",
        "compatible_bikes": [
            "Honda CD70", "Honda CG125", "Honda CB150F",
            "Honda CB125F", "Honda CG125S"
        ],
        "description": (
            "Honda genuine chain lubricant aerosol. White semi-dry formula clings to "
            "chain links and resists fling-off at speed. Does not attract dust — ideal "
            "for sandy areas of DG Khan and Bahawalpur. Apply every 500-800 km or "
            "after washing. 150ml — approx. 10-12 applications."
        ),
        "price":          "650.00",
        "discount_price": None,
        "stock":          120,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "oil",
        "weight_grams":        250,
        "low_stock_threshold": 20,
        "specifications": [
            {"name": "Type",         "value": "Semi-Dry Chain Lubricant (Aerosol)", "display_order": 0},
            {"name": "Formula",      "value": "White (non-fling)",                  "display_order": 1},
            {"name": "Volume",       "value": "150", "unit": "ml",                  "display_order": 2},
            {"name": "Applications", "value": "10–12 per can",                      "display_order": 3},
            {"name": "Interval",     "value": "Every 500–800 km",                   "display_order": 4},
        ],
    },
    {
        "name":        "Castrol Fork Oil 10W — 500ml",
        "sku":         "OIL-CAS-005",
        "category":    "Lubrication & Oils",
        "brand":       "Castrol",
        "compatible_bikes": [
            "Honda CB150F", "Yamaha YZF-R15", "Suzuki GR150", "Yamaha YBR125G"
        ],
        "description": (
            "Castrol 10W fork oil for telescopic front suspension. Shear-stable viscosity "
            "ensures consistent damping. Anti-foam additive prevents cavitation on speed "
            "bumps. Replace every 20,000 km or 2 years. 500ml bottle."
        ),
        "price":          "750.00",
        "discount_price": "699.00",
        "stock":          90,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "oil",
        "weight_grams":        580,
        "low_stock_threshold": 15,
        "specifications": [
            {"name": "Viscosity",       "value": "10W",                              "display_order": 0},
            {"name": "Type",            "value": "Fork Oil",                         "display_order": 1},
            {"name": "Volume",          "value": "500", "unit": "ml",               "display_order": 2},
            {"name": "Change Interval", "value": "20,000 km / 2 years",             "display_order": 3},
        ],
    },
    {
        "name":        "Castrol DOT 4 Hydraulic Brake Fluid — 100ml",
        "sku":         "OIL-BRK-006",
        "category":    "Lubrication & Oils",
        "brand":       "Castrol",
        "compatible_bikes": [
            "Honda CB150F", "Honda CB125F", "Suzuki GS150",
            "Suzuki GR150", "Yamaha YZF-R15", "Ravi Wolf 150"
        ],
        "description": (
            "Castrol DOT 4 brake fluid. Dry boiling point 230°C. Wet boiling point 155°C. "
            "Compatible with all rubber seals. Do NOT mix with DOT 5. Change every "
            "2 years. 100ml sufficient for one full system flush."
        ),
        "price":          "320.00",
        "discount_price": None,
        "stock":          160,
        "status":         "available",
        "is_featured":    False,
        "image_key":      "oil",
        "weight_grams":        130,
        "low_stock_threshold": 25,
        "specifications": [
            {"name": "Standard",           "value": "DOT 4",                    "display_order": 0},
            {"name": "Dry Boiling Point",  "value": "230", "unit": "°C",       "display_order": 1},
            {"name": "Wet Boiling Point",  "value": "155", "unit": "°C",       "display_order": 2},
            {"name": "Volume",             "value": "100", "unit": "ml",       "display_order": 3},
            {"name": "Compatibility",      "value": "All rubber seals (not DOT 5)", "display_order": 4},
        ],
    },
]
