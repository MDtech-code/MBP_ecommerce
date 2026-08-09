




export const LABEL_OPTIONS = [
  { value: "home",   label: "🏠 Home"   },
  { value: "office", label: "🏢 Office" },
  { value: "other",  label: "📍 Other"  },
]


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