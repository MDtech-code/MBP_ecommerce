"""
Seed data: Products, Categories, Brands, Bike Models.
Pakistan Motorbike Parts Store — production quality data.
"""

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

BRANDS_DATA = [
    "Honda", "Yamaha", "Suzuki", "Ravi", "United",
    "Road Prince", "Dayang", "Superpower", "NGK",
    "Yuasa", "Dunlop", "Innova", "Castrol", "Motigear", "DID",
]

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

USERS_DATA = [
   
    {
        "email":        "virjarock@gmail.com",
        "password":     "Customer@12345",
        "full_name":    "Virja Rock",
        "role":         "CU",
        "is_staff":     False,
        "is_superuser": False,
        "is_verified":  True,
        "is_active":    True,
    },
    {
        "email":        "rockaslam435@gmail.com",
        "password":     "Customer@12345",
        "full_name":    "Rock Aslam",
        "role":         "CU",
        "is_staff":     False,
        "is_superuser": False,
        "is_verified":  True,
        "is_active":    True,
    },
]

CART_DATA = {
    "virjarock@gmail.com": [
        # (sku, quantity)
        ("BAT-YUA-001", 1),
        ("BRK-HND-001", 2),
        ("CHN-DID-002", 1),
        ("TYR-DUN-001", 2),
        ("OIL-CAS-001", 3),
    ],
    "rockaslam435@gmail.com": [
        ("BAT-YUA-002", 1),
        ("CHN-SUZ-003", 1),
        ("TYR-INV-003", 1),
        ("LGT-YAM-002", 1),
        ("OIL-CAS-001", 2),
        ("ENG-NGK-004", 4),
    ],
}

PRODUCTS_DATA = [

    # ── BATTERIES ──────────────────────────────────────────────────────────────
    {
        "name": "Yuasa YB5L-B 12V Motorbike Battery",
        "sku": "BAT-YUA-001",
        "category": "Batteries",
        "brand": "Yuasa",
        "compatible_bikes": ["Honda CG125", "Honda CG125S", "Honda CB125F"],
        "description": (
            "Genuine Yuasa YB5L-B 12V 5Ah lead-acid battery designed for 125cc–150cc "
            "motorcycles. Maintenance-free design with superior cold-cranking amperage "
            "ensures reliable starting in Pakistan's hot summers and cold winters. "
            "Leak-proof construction with AGM technology. Includes electrolyte pack."
        ),
        "price": "2800.00",
        "discount_price": "2499.00",
        "stock": 45,
        "status": "available",
        "is_featured": True,
        "image_key": "battery",
    },
    {
        "name": "Yuasa YTX7A-BS 12V MF Battery for 150cc Bikes",
        "sku": "BAT-YUA-002",
        "category": "Batteries",
        "brand": "Yuasa",
        "compatible_bikes": [
            "Honda CB150F", "Suzuki GS150", "Suzuki GR150", "Yamaha YBR125"
        ],
        "description": (
            "Yuasa YTX7A-BS Maintenance-Free 12V 6Ah battery. Sealed AGM technology "
            "prevents acid spillage. Factory-activated and ready to install. Ideal for "
            "150cc bikes running in city traffic in Lahore, Karachi, and Islamabad. "
            "Provides 200+ cold cranking amps for fast, reliable engine starts."
        ),
        "price": "3500.00",
        "discount_price": "3199.00",
        "stock": 30,
        "status": "available",
        "is_featured": True,
        "image_key": "battery",
    },
    {
        "name": "Standard 6V 4Ah Battery for Honda CD70",
        "sku": "BAT-LOC-003",
        "category": "Batteries",
        "brand": "Honda",
        "compatible_bikes": ["Honda CD70", "Road Prince RP 70", "Superpower SP 70"],
        "description": (
            "OEM-compatible 6 Volt 4Ah conventional lead-acid battery for Honda CD70 "
            "and similar 70cc commuter bikes. Standard wet-cell battery with high "
            "charge retention. Widely used across Pakistan's most popular commuter "
            "motorcycle. Comes pre-filled with electrolyte. Terminal layout matches "
            "factory specification."
        ),
        "price": "1200.00",
        "discount_price": None,
        "stock": 80,
        "status": "available",
        "is_featured": False,
        "image_key": "battery",
    },
    {
        "name": "Osaka 12V 9Ah Heavy Duty Bike Battery",
        "sku": "BAT-OSK-004",
        "category": "Batteries",
        "brand": "Superpower",
        "compatible_bikes": [
            "Suzuki GS150", "Suzuki GS150SE", "Honda CB150F", "Yamaha YZF-R15"
        ],
        "description": (
            "Osaka heavy-duty 12V 9Ah battery engineered for high-performance 150cc+ "
            "motorcycles. Double-lid construction for extra safety. Vibration-resistant "
            "plates extend battery life on rough Pakistani roads. Suitable for electric "
            "start bikes with heavy accessory loads such as USB chargers and LED lights."
        ),
        "price": "4200.00",
        "discount_price": "3800.00",
        "stock": 20,
        "status": "available",
        "is_featured": False,
        "image_key": "battery",
    },
    {
        "name": "AGS 12V 2.5Ah Nano Gel Battery for 70cc–100cc",
        "sku": "BAT-AGS-005",
        "category": "Batteries",
        "brand": "United",
        "compatible_bikes": [
            "Honda CD70", "United US 100", "Road Prince RP 70", "Superpower SP 70"
        ],
        "description": (
            "AGS Nano Gel 12V 2.5Ah ultra-compact maintenance-free battery designed "
            "for 70cc to 100cc motorcycles. Gel electrolyte technology ensures zero "
            "spillage and longer shelf life. Perfect replacement for OEM battery on "
            "Honda CD70, United US 100, and Road Prince RP 70. Arrives charged."
        ),
        "price": "1800.00",
        "discount_price": "1650.00",
        "stock": 60,
        "status": "available",
        "is_featured": False,
        "image_key": "battery",
    },
    {
        "name": "Exide 12V 7Ah MF Battery — Universal 125cc",
        "sku": "BAT-EXD-006",
        "category": "Batteries",
        "brand": "Honda",
        "compatible_bikes": [
            "Honda CG125", "Honda CG125S", "Yamaha YBR125", "Yamaha Saluto 125"
        ],
        "description": (
            "Exide 12V 7Ah maintenance-free battery compatible with most 125cc "
            "motorcycles sold in Pakistan. AGM technology delivers consistent power. "
            "18-month warranty against manufacturing defects. Terminal: positive left, "
            "negative right — matches CG125 and YBR125 trays without modification."
        ),
        "price": "3200.00",
        "discount_price": "2900.00",
        "stock": 35,
        "status": "available",
        "is_featured": True,
        "image_key": "battery",
    },

    # ── BRAKE SYSTEM ───────────────────────────────────────────────────────────
    {
        "name": "Honda CG125 Front Disc Brake Pad Set (OEM Grade)",
        "sku": "BRK-HND-001",
        "category": "Disc Brakes",
        "brand": "Honda",
        "compatible_bikes": ["Honda CG125", "Honda CG125S", "Honda CB125F"],
        "description": (
            "OEM-grade front disc brake pad set for Honda CG125. Semi-metallic compound "
            "provides excellent stopping power in wet and dry conditions. Low dust "
            "formulation keeps wheel rims clean. Includes 2 pads, mounting hardware, "
            "and anti-squeal shims. Replace every 10,000 km or when thickness < 2mm."
        ),
        "price": "850.00",
        "discount_price": "750.00",
        "stock": 100,
        "status": "available",
        "is_featured": True,
        "image_key": "brake",
    },
    {
        "name": "Yamaha YBR125 Rear Drum Brake Shoe Assembly",
        "sku": "BRK-YAM-002",
        "category": "Drum Brakes",
        "brand": "Yamaha",
        "compatible_bikes": ["Yamaha YBR125", "Yamaha YBR125G", "Yamaha Saluto 125"],
        "description": (
            "Genuine-quality rear drum brake shoe set for Yamaha YBR125. High-friction "
            "lining bonded to heavy-gauge steel shoe. Fade-resistant compound rated to "
            "300°C. Direct drop-in replacement. Includes both leading and trailing "
            "shoes. Sold as a complete axle set."
        ),
        "price": "650.00",
        "discount_price": None,
        "stock": 75,
        "status": "available",
        "is_featured": False,
        "image_key": "brake",
    },
    {
        "name": "Suzuki GS150 Front Brake Disc Rotor 260mm",
        "sku": "BRK-SUZ-003",
        "category": "Disc Brakes",
        "brand": "Suzuki",
        "compatible_bikes": ["Suzuki GS150", "Suzuki GS150SE", "Suzuki GR150"],
        "description": (
            "High-carbon steel 260mm front brake disc rotor for Suzuki GS150. "
            "Cross-drilled and slotted design improves heat dissipation and wet-weather "
            "performance. Precision balanced to eliminate brake judder. "
            "Thickness: 4.0mm new, minimum 3.5mm. Fits OEM caliper."
        ),
        "price": "2200.00",
        "discount_price": "1999.00",
        "stock": 40,
        "status": "available",
        "is_featured": False,
        "image_key": "brake",
    },
    {
        "name": "Honda CD70 Complete Drum Brake Assembly — Front & Rear",
        "sku": "BRK-HND-004",
        "category": "Drum Brakes",
        "brand": "Honda",
        "compatible_bikes": ["Honda CD70", "Road Prince RP 70", "Superpower SP 70"],
        "description": (
            "Full front and rear drum brake assembly kit for Honda CD70. Includes "
            "brake drums, brake shoes (4 pieces), return springs, cam shafts, and "
            "brake cables. Ideal for complete brake system restoration. All components "
            "manufactured to Honda specifications."
        ),
        "price": "1800.00",
        "discount_price": "1600.00",
        "stock": 55,
        "status": "available",
        "is_featured": True,
        "image_key": "brake",
    },
    {
        "name": "Universal Hydraulic Brake Lever Set — CNC Aluminium",
        "sku": "BRK-UNI-005",
        "category": "Disc Brakes",
        "brand": "Superpower",
        "compatible_bikes": [
            "Honda CB150F", "Yamaha YZF-R15", "Suzuki GR150", "Ravi Wolf 150"
        ],
        "description": (
            "CNC-machined aluminium hydraulic brake and clutch lever set. Compatible "
            "with 22mm handlebars. 5-position adjustable reach dial. Anodised black "
            "finish. Works on most 150cc+ motorcycles. Bolt-on installation with "
            "standard 8mm pivot bolt. Pair sold together."
        ),
        "price": "1450.00",
        "discount_price": "1299.00",
        "stock": 60,
        "status": "available",
        "is_featured": False,
        "image_key": "brake",
    },
    {
        "name": "Brake Master Cylinder Rebuild Kit — 125cc–150cc",
        "sku": "BRK-MKT-006",
        "category": "Disc Brakes",
        "brand": "Honda",
        "compatible_bikes": [
            "Honda CG125", "Honda CB125F", "Honda CB150F", "Suzuki GS150"
        ],
        "description": (
            "Complete master cylinder rebuild kit: piston cup, dust seal, spring, and "
            "circlip. Restores proper brake fluid pressure and pedal feel. Use every "
            "2 years or when brake fluid becomes discoloured. Compatible with standard "
            "14mm bore master cylinders on Honda and Suzuki 125cc–150cc bikes."
        ),
        "price": "420.00",
        "discount_price": None,
        "stock": 90,
        "status": "available",
        "is_featured": False,
        "image_key": "brake",
    },

    # ── TRANSMISSION — CHAIN & SPROCKET ────────────────────────────────────────
    {
        "name": "DID 420D Standard Drive Chain 116 Links — Honda CD70",
        "sku": "CHN-DID-001",
        "category": "Drive Chain & Sprocket",
        "brand": "DID",
        "compatible_bikes": ["Honda CD70", "Road Prince RP 70", "Superpower SP 70"],
        "description": (
            "DID 420D standard roller chain, 116 links — most popular size for 70cc "
            "bikes in Pakistan. Tensile strength 14.7 kN. Pre-lubricated. Includes "
            "connecting link. Replace every 10,000 km or when slack exceeds 20mm. "
            "Suits standard 17T front / 38T rear sprocket on Honda CD70."
        ),
        "price": "1100.00",
        "discount_price": "980.00",
        "stock": 120,
        "status": "available",
        "is_featured": True,
        "image_key": "chain",
    },
    {
        "name": "DID 428H Heavy-Duty O-Ring Chain 120 Links — 125cc",
        "sku": "CHN-DID-002",
        "category": "Drive Chain & Sprocket",
        "brand": "DID",
        "compatible_bikes": [
            "Honda CG125", "Honda CG125S", "Honda CB125F", "Yamaha YBR125"
        ],
        "description": (
            "DID 428H heavy-duty O-ring drive chain, 120 links. O-ring seals retain "
            "grease, tripling chain life vs standard chains. Tensile strength 18.6 kN. "
            "Gold colour with DID branding. Clip-type master link included. Ideal "
            "for daily commuters on GT Road."
        ),
        "price": "2400.00",
        "discount_price": "2150.00",
        "stock": 85,
        "status": "available",
        "is_featured": True,
        "image_key": "chain",
    },
    {
        "name": "Suzuki GS150 Complete Chain & Sprocket Kit",
        "sku": "CHN-SUZ-003",
        "category": "Drive Chain & Sprocket",
        "brand": "Suzuki",
        "compatible_bikes": ["Suzuki GS150", "Suzuki GS150SE", "Suzuki GR150"],
        "description": (
            "Complete drivetrain kit for Suzuki GS150: DID 428H 120-link O-ring chain, "
            "15T front sprocket, 42T rear sprocket, and all mounting hardware. "
            "Case-hardened steel sprockets. Recommended when bike exceeds 15,000 km "
            "since last replacement."
        ),
        "price": "3800.00",
        "discount_price": "3499.00",
        "stock": 40,
        "status": "available",
        "is_featured": False,
        "image_key": "chain",
    },
    {
        "name": "Honda CB150F Rear Sprocket 38T — Heavy Gauge Steel",
        "sku": "CHN-HND-004",
        "category": "Drive Chain & Sprocket",
        "brand": "Honda",
        "compatible_bikes": ["Honda CB150F", "Honda CB125F"],
        "description": (
            "OEM-specification 38-tooth rear sprocket for Honda CB150F. CNC-machined "
            "tooth profile. Centre bore 130mm, 5 × 10.5mm bolt holes on 145mm PCD. "
            "Surface hardened HRC 50–55. Sold individually."
        ),
        "price": "1200.00",
        "discount_price": None,
        "stock": 65,
        "status": "available",
        "is_featured": False,
        "image_key": "chain",
    },
    {
        "name": "Yamaha YBR125 Chain Tensioner & Guide Roller Set",
        "sku": "CHN-YAM-005",
        "category": "Drive Chain & Sprocket",
        "brand": "Yamaha",
        "compatible_bikes": ["Yamaha YBR125", "Yamaha YBR125G", "Yamaha Saluto 125"],
        "description": (
            "OEM-compatible chain tensioner block and guide roller set for Yamaha "
            "YBR125. Hard-wearing nylon slider resists heat and oil. Prevents chain "
            "whip and reduces noise. Includes tensioner bolt, lock nut, and replacement "
            "guide rubber."
        ),
        "price": "650.00",
        "discount_price": "580.00",
        "stock": 70,
        "status": "available",
        "is_featured": False,
        "image_key": "chain",
    },
    {
        "name": "Universal 420 Chain Master Link Clip Type — Pack of 10",
        "sku": "CHN-UNI-006",
        "category": "Drive Chain & Sprocket",
        "brand": "DID",
        "compatible_bikes": [
            "Honda CD70", "United US 100", "Road Prince RP 70",
            "Dayang DY 125", "Superpower SP 70"
        ],
        "description": (
            "Pack of 10 DID 420-size clip-type master links for fast chain joining. "
            "Hardened steel side plates and spring clip. Essential spare for long-distance "
            "riders. Clip direction must face opposite to chain travel for safety."
        ),
        "price": "350.00",
        "discount_price": None,
        "stock": 200,
        "status": "available",
        "is_featured": False,
        "image_key": "chain",
    },

    # ── TYRES & TUBES ──────────────────────────────────────────────────────────
    {
        "name": "Dunlop D102 2.50-17 Front Tyre — CD70 / CG125",
        "sku": "TYR-DUN-001",
        "category": "Tyres & Tubes",
        "brand": "Dunlop",
        "compatible_bikes": ["Honda CD70", "Honda CG125", "Road Prince RP 70"],
        "description": (
            "Dunlop D102 2.50-17 4-ply front tyre. Ribbed centre groove for straight-line "
            "stability. Compound for hot Asian climates. Load index 38 (170 kg). "
            "Speed rating P (150 km/h). TT type — requires inner tube."
        ),
        "price": "2200.00",
        "discount_price": "1999.00",
        "stock": 60,
        "status": "available",
        "is_featured": True,
        "image_key": "tyre",
    },
    {
        "name": "Dunlop D102 3.00-17 Rear Tyre — CG125 / YBR125",
        "sku": "TYR-DUN-002",
        "category": "Tyres & Tubes",
        "brand": "Dunlop",
        "compatible_bikes": ["Honda CG125", "Honda CG125S", "Yamaha YBR125"],
        "description": (
            "Dunlop D102 3.00-17 6-ply rear tyre. Block pattern for grip on wet roads "
            "and gravel. Reinforced sidewall resists cuts. Load index 50 (190 kg). "
            "Speed rating P (150 km/h). TT type."
        ),
        "price": "2800.00",
        "discount_price": "2600.00",
        "stock": 50,
        "status": "available",
        "is_featured": True,
        "image_key": "tyre",
    },
    {
        "name": "Innova IA-2606 100/80-17 Tubeless Tyre — CB150F / GS150",
        "sku": "TYR-INV-003",
        "category": "Tyres & Tubes",
        "brand": "Innova",
        "compatible_bikes": [
            "Honda CB150F", "Suzuki GS150", "Suzuki GR150", "Ravi Wolf 150"
        ],
        "description": (
            "Innova IA-2606 100/80-17 tubeless rear tyre. Asymmetric tread for mixed "
            "urban/highway riding. Silica-enhanced compound for wet traction. TL — fits "
            "alloy wheels. Load index 52 (200 kg). Speed rating H (210 km/h). "
            "Recommended inflation: 28 PSI rear."
        ),
        "price": "4500.00",
        "discount_price": "4200.00",
        "stock": 35,
        "status": "available",
        "is_featured": False,
        "image_key": "tyre",
    },
    {
        "name": "IRC NR73 2.75-17 Rear Tyre — Universal 100cc–125cc",
        "sku": "TYR-IRC-004",
        "category": "Tyres & Tubes",
        "brand": "United",
        "compatible_bikes": [
            "United US 100", "United US 125", "Dayang DY 125",
            "Road Prince RP 125", "Honda CG125"
        ],
        "description": (
            "IRC NR73 2.75-17 4-ply tube-type rear tyre. Rib-and-block pattern balances "
            "straight-line stability with corner grip. ISO 4223 standard. Popular factory "
            "fitment on many Pakistani 100cc–125cc motorcycles."
        ),
        "price": "2100.00",
        "discount_price": None,
        "stock": 90,
        "status": "available",
        "is_featured": False,
        "image_key": "tyre",
    },
    {
        "name": "Butyl Inner Tube 2.50/2.75-17 — Pack of 2",
        "sku": "TYR-TUB-005",
        "category": "Tyres & Tubes",
        "brand": "Honda",
        "compatible_bikes": [
            "Honda CD70", "Honda CG125", "Yamaha YBR125",
            "United US 100", "Road Prince RP 70"
        ],
        "description": (
            "Premium butyl rubber inner tubes size 2.50/2.75-17. Dual-size fitment "
            "covers both 70cc and 125cc tyre widths. Straight TR4 valve stem. Uniform "
            "wall thickness prevents blow-outs. Pack of 2 for front and rear."
        ),
        "price": "700.00",
        "discount_price": "620.00",
        "stock": 150,
        "status": "available",
        "is_featured": False,
        "image_key": "tyre",
    },
    {
        "name": "Yamaha YZF-R15 110/70-17 Front Tubeless Tyre",
        "sku": "TYR-YAM-006",
        "category": "Tyres & Tubes",
        "brand": "Yamaha",
        "compatible_bikes": ["Yamaha YZF-R15"],
        "description": (
            "High-performance 110/70-17 front tubeless tyre for YZF-R15. Sporty tread "
            "with large shoulder blocks for lean-angle grip. Load index 54 (212 kg). "
            "Speed rating V (240 km/h). TL — fits 17-inch alloy rim. "
            "Recommended front pressure: 26 PSI."
        ),
        "price": "6500.00",
        "discount_price": "5999.00",
        "stock": 20,
        "status": "available",
        "is_featured": True,
        "image_key": "tyre",
    },

    # ── ENGINE PARTS ───────────────────────────────────────────────────────────
    {
        "name": "Honda CG125 Complete Engine Gasket Set",
        "sku": "ENG-HND-001",
        "category": "Engine Parts",
        "brand": "Honda",
        "compatible_bikes": ["Honda CG125", "Honda CG125S"],
        "description": (
            "Full engine gasket kit for Honda CG125: cylinder head gasket, cylinder "
            "base gasket, crankcase gasket, rocker cover gasket, exhaust gasket, and "
            "all O-rings. OEM-equivalent ratings. Covers complete engine teardown — "
            "no additional gaskets needed."
        ),
        "price": "1800.00",
        "discount_price": "1650.00",
        "stock": 55,
        "status": "available",
        "is_featured": False,
        "image_key": "engine",
    },
    {
        "name": "Yamaha YBR125 Piston Kit — Standard Bore 54mm",
        "sku": "ENG-YAM-002",
        "category": "Pistons & Rings",
        "brand": "Yamaha",
        "compatible_bikes": ["Yamaha YBR125", "Yamaha YBR125G", "Yamaha Saluto 125"],
        "description": (
            "Standard bore 54.00mm piston kit for Yamaha YBR125. Includes forged "
            "aluminium piston, 2× compression rings, 1× oil control ring, wrist pin, "
            "and circlips. Flat-top design maintains stock 9.5:1 compression ratio. "
            "Install with new cylinder base gasket."
        ),
        "price": "2500.00",
        "discount_price": "2300.00",
        "stock": 40,
        "status": "available",
        "is_featured": True,
        "image_key": "engine",
    },
    {
        "name": "Honda CD70 Carburettor Assembly PD18J",
        "sku": "ENG-HND-003",
        "category": "Carburettors",
        "brand": "Honda",
        "compatible_bikes": ["Honda CD70"],
        "description": (
            "OEM-grade PD18J slide-type carburettor for Honda CD70. Includes carburettor "
            "body, float bowl, main jet (72), pilot jet (38), needle valve, throttle "
            "slide, choke plate, and air-fuel screw. Improves fuel economy vs worn "
            "originals. Standard 18mm inlet manifold fitment."
        ),
        "price": "1600.00",
        "discount_price": "1450.00",
        "stock": 70,
        "status": "available",
        "is_featured": True,
        "image_key": "engine",
    },
    {
        "name": "NGK CR7HSA Spark Plug — Universal 125cc–150cc",
        "sku": "ENG-NGK-004",
        "category": "Engine Parts",
        "brand": "NGK",
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
        "price": "380.00",
        "discount_price": None,
        "stock": 300,
        "status": "available",
        "is_featured": False,
        "image_key": "engine",
    },
    {
        "name": "Suzuki GS150 Air Filter Element — OEM Replacement",
        "sku": "ENG-SUZ-005",
        "category": "Filters",
        "brand": "Suzuki",
        "compatible_bikes": ["Suzuki GS150", "Suzuki GS150SE"],
        "description": (
            "OEM-equivalent paper air filter for Suzuki GS150. Multi-layer filtration "
            "removes 99.5% of dust particles >= 10 microns — critical for dusty Punjab "
            "and Sindh conditions. Replace every 6,000 km in dust, 12,000 km on clean "
            "roads. Direct fit into original air box."
        ),
        "price": "550.00",
        "discount_price": "499.00",
        "stock": 110,
        "status": "available",
        "is_featured": False,
        "image_key": "engine",
    },
    {
        "name": "Honda CB150F Clutch Plate Set — Full Kit",
        "sku": "ENG-HND-006",
        "category": "Clutch Parts",
        "brand": "Honda",
        "compatible_bikes": ["Honda CB150F", "Honda CB125F"],
        "description": (
            "Complete wet clutch plate set for Honda CB150F: 4x friction plates, "
            "4x steel drive plates, 1x pressure plate. Friction material rated to "
            "200°C. Eliminates clutch slip under acceleration and drag in traffic. "
            "Soak friction plates in 10W-40 oil 24 hours before installation."
        ),
        "price": "3200.00",
        "discount_price": "2899.00",
        "stock": 30,
        "status": "available",
        "is_featured": False,
        "image_key": "engine",
    },

    # ── ELECTRICAL & LIGHTS ────────────────────────────────────────────────────
    {
        "name": "Honda CD70 / CG125 12V 35W Halogen Headlight Bulb",
        "sku": "LGT-HND-001",
        "category": "Headlights",
        "brand": "Honda",
        "compatible_bikes": ["Honda CD70", "Honda CG125", "Honda CG125S"],
        "description": (
            "12V 35/35W H4 halogen headlight bulb for Honda CD70 and CG125. "
            "3-pin P15D-25-3 base. 450 lumens for safe night-time visibility. "
            "500-hour rated life. Pair sold — one for the bike, one spare. "
            "Fits OEM housing without modification."
        ),
        "price": "220.00",
        "discount_price": None,
        "stock": 200,
        "status": "available",
        "is_featured": False,
        "image_key": "light",
    },
    {
        "name": "Yamaha YBR125 LED Headlight Assembly 12V 18W",
        "sku": "LGT-YAM-002",
        "category": "Headlights",
        "brand": "Yamaha",
        "compatible_bikes": ["Yamaha YBR125", "Yamaha YBR125G", "Yamaha Saluto 125"],
        "description": (
            "Plug-and-play LED headlight assembly for Yamaha YBR125. 18W producing "
            "1800 lumens — 4x brighter than stock halogen at half the power draw. "
            "6000K cool white. IP67 waterproof. Direct connector match — no wiring "
            "modification. Includes DRL daytime running strip."
        ),
        "price": "2800.00",
        "discount_price": "2499.00",
        "stock": 45,
        "status": "available",
        "is_featured": True,
        "image_key": "light",
    },
    {
        "name": "Universal 12V LED Indicator Set — Amber 4 pcs",
        "sku": "LGT-UNI-003",
        "category": "Indicators & Bulbs",
        "brand": "Superpower",
        "compatible_bikes": [
            "Honda CG125", "Honda CB150F", "Yamaha YBR125",
            "Suzuki GS150", "United US 125"
        ],
        "description": (
            "4x LED turn-signal lights. 12V 2W each (replaces 10W bulbs). "
            "Amber lens, chrome housing. 10mm stem fits most indicator bosses. "
            "Compatible with standard flasher relays. IP54 splash proof."
        ),
        "price": "850.00",
        "discount_price": "750.00",
        "stock": 80,
        "status": "available",
        "is_featured": False,
        "image_key": "light",
    },
    {
        "name": "Suzuki GR150 Full LED Tail Light Assembly",
        "sku": "LGT-SUZ-004",
        "category": "Indicators & Bulbs",
        "brand": "Suzuki",
        "compatible_bikes": ["Suzuki GR150", "Suzuki GS150SE"],
        "description": (
            "OEM-style full LED tail and brake light for Suzuki GR150. Brake light "
            "40cd; tail light 4cd — meets ECE R50. Direct bolt-on, same 3-pin connector. "
            "Smoked lens. Operating voltage 10-16V. Life 50,000 hours."
        ),
        "price": "1800.00",
        "discount_price": "1650.00",
        "stock": 35,
        "status": "available",
        "is_featured": False,
        "image_key": "light",
    },
    {
        "name": "Honda CB150F Speedometer Cluster Assembly",
        "sku": "LGT-HND-005",
        "category": "Electrical & Lights",
        "brand": "Honda",
        "compatible_bikes": ["Honda CB150F", "Honda CB125F"],
        "description": (
            "OEM-grade speedometer cluster for Honda CB150F. Includes analogue "
            "speedometer (0-160 km/h), fuel gauge, gear position indicator, and "
            "all tell-tales. Backlit for night reading. Cable-driven. Direct plug-in "
            "connector. Replace when face is cracked or needle is sticking."
        ),
        "price": "4500.00",
        "discount_price": "4100.00",
        "stock": 20,
        "status": "available",
        "is_featured": True,
        "image_key": "light",
    },
    {
        "name": "Universal T10 W5W 12V 5W Parking Bulb — Pack of 10",
        "sku": "LGT-UNI-006",
        "category": "Indicators & Bulbs",
        "brand": "NGK",
        "compatible_bikes": [
            "Honda CD70", "Honda CG125", "Yamaha YBR125",
            "Suzuki GS150", "United US 100", "Road Prince RP 125"
        ],
        "description": (
            "Pack of 10 T10 W5W 12V 5W halogen bulbs for instrument panel and "
            "position indicators. W2.1x9.5d wedge socket — fits most Pakistani "
            "motorcycles. Bulk pack for workshops. Push-in fitment."
        ),
        "price": "180.00",
        "discount_price": None,
        "stock": 500,
        "status": "available",
        "is_featured": False,
        "image_key": "light",
    },

    # ── LUBRICATION & OILS ─────────────────────────────────────────────────────
    {
        "name": "Castrol Power1 4T 10W-40 Engine Oil — 1 Litre",
        "sku": "OIL-CAS-001",
        "category": "Lubrication & Oils",
        "brand": "Castrol",
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
        "price": "1200.00",
        "discount_price": "1099.00",
        "stock": 200,
        "status": "available",
        "is_featured": True,
        "image_key": "oil",
    },
    {
        "name": "Castrol Power1 4T 20W-50 Engine Oil — 1 Litre",
        "sku": "OIL-CAS-002",
        "category": "Lubrication & Oils",
        "brand": "Castrol",
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
        "price": "950.00",
        "discount_price": None,
        "stock": 180,
        "status": "available",
        "is_featured": False,
        "image_key": "oil",
    },
    {
        "name": "Motigear Gear Oil 80W-90 GL-4 — 500ml",
        "sku": "OIL-MTG-003",
        "category": "Lubrication & Oils",
        "brand": "Motigear",
        "compatible_bikes": [
            "Honda CG125", "Honda CB150F", "Yamaha YBR125",
            "Suzuki GS150", "Ravi Wolf 150"
        ],
        "description": (
            "Motigear 80W-90 GL-4 gear oil for separate-sump gearboxes. Extreme "
            "pressure additive protects gear teeth under high load. Anti-wear, anti-foam, "
            "oxidation inhibitors. 500ml — one gearbox oil change. Change every 10,000 km."
        ),
        "price": "480.00",
        "discount_price": "420.00",
        "stock": 150,
        "status": "available",
        "is_featured": False,
        "image_key": "oil",
    },
    {
        "name": "Honda OEM Chain Lubricant Spray — 150ml",
        "sku": "OIL-HND-004",
        "category": "Lubrication & Oils",
        "brand": "Honda",
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
        "price": "650.00",
        "discount_price": None,
        "stock": 120,
        "status": "available",
        "is_featured": False,
        "image_key": "oil",
    },
    {
        "name": "Castrol Fork Oil 10W — 500ml",
        "sku": "OIL-CAS-005",
        "category": "Lubrication & Oils",
        "brand": "Castrol",
        "compatible_bikes": [
            "Honda CB150F", "Yamaha YZF-R15", "Suzuki GR150", "Yamaha YBR125G"
        ],
        "description": (
            "Castrol 10W fork oil for telescopic front suspension. Shear-stable viscosity "
            "ensures consistent damping. Anti-foam additive prevents cavitation on speed "
            "bumps. Replace every 20,000 km or 2 years. 500ml bottle."
        ),
        "price": "750.00",
        "discount_price": "699.00",
        "stock": 90,
        "status": "available",
        "is_featured": False,
        "image_key": "oil",
    },
    {
        "name": "Castrol DOT 4 Hydraulic Brake Fluid — 100ml",
        "sku": "OIL-BRK-006",
        "category": "Lubrication & Oils",
        "brand": "Castrol",
        "compatible_bikes": [
            "Honda CB150F", "Honda CB125F", "Suzuki GS150",
            "Suzuki GR150", "Yamaha YZF-R15", "Ravi Wolf 150"
        ],
        "description": (
            "Castrol DOT 4 brake fluid. Dry boiling point 230°C. Wet boiling point 155°C. "
            "Compatible with all rubber seals. Do NOT mix with DOT 5. Change every "
            "2 years. 100ml sufficient for one full system flush."
        ),
        "price": "320.00",
        "discount_price": None,
        "stock": 160,
        "status": "available",
        "is_featured": False,
        "image_key": "oil",
    },
]