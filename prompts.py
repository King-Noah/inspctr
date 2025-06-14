# prompts.py

BASE_PROMPT = """
You are a licensed home inspector trained to follow the Texas Real Estate Commission (TREC) Standards of Practice (SOP).

Your task is to evaluate the provided image for **visible deficiencies only**, focusing on the following systems: {system_name}.

⚠️ IMPORTANT:
- DO NOT identify or describe any people or personal property in the image.
- ONLY report physical issues visible in the photo.
- Format your response exactly as shown in the example below.
- Only include deficiencies you can clearly observe.

📋 FORMAT (repeat for each issue found):
### Deficiency {{number}}: {{Concise Title}}
**Description:** {{Explanation of the deficiency and why it matters}}
**Severity:** {{Cosmetic | Functional | Safety Concern | Major Structural}}
**Recommended Action:** {{Advice for the client}}
**TREC SOP Reference:** {{e.g., 535.228(d)(1)(B)}}
Use only this format. If no deficiencies are observed, respond with:
**No visible deficiencies found based on the image provided.**

Begin your response now:
"""

# Nested hierarchy for organized grouping
SYSTEM_NAME_MAPPING = {
    "STRUCTURAL": {
        "foundations": "structural foundations, footings, piers, or related components",
        "grading_and_drainage": "site grading, water flow, and drainage control elements",
        "roof_covering_materials": "roofing materials including shingles, metal panels, tiles, and associated flashing",
        "roof_structures_and_attics": "roof framing systems, rafters, trusses, and attic structures",
        "walls": "interior and exterior wall construction and finishes",
        "ceilings_and_floors": "interior ceiling and flooring systems",
        "doors": "interior and exterior door installation and function",
        "windows": "window frames, glazing, and functionality",
        "stairways": "interior and exterior stair systems including treads, risers, railings",
        "fireplaces_and_chimneys": "visible and accessible components of fireplaces and chimneys",
        "porches_balconies_decks_carports": "porches, balconies, decks, and carports structure and safety",
        "structural_other": "miscellaneous structural components not otherwise categorized"
    },
    "ELECTRICAL": {
        "service_entrance_and_panels": "electrical service entrance conductors, main panels, breakers, and disconnects",
        "branch_circuits": "branch wiring, connected devices, lighting, and receptacles"
    },
    "HVAC": {
        "heating_equipment": "furnaces, heat pumps, and heating system components",
        "cooling_equipment": "air conditioning units, compressors, and cooling-related parts",
        "ducts_chases_vents": "HVAC ducts, chases, and venting systems"
    },
    "PLUMBING": {
        "supply_distribution_and_fixtures": "water supply lines, distribution plumbing, and fixtures",
        "drains_wastes_vents": "plumbing drains, waste lines, and vent systems",
        "water_heating_equipment": "water heaters, tanks, and associated plumbing",
        "hydro_massage_equipment": "hydro-massage tubs and specialized plumbing equipment",
        "plumbing_other": "other plumbing components and issues"
    },
    "APPLIANCES": {
        "dishwashers": "built-in dishwasher units and installation",
        "food_waste_disposers": "garbage disposals and their connections",
        "range_hoods": "range hood and exhaust systems",
        "ranges_ovens_cooktops": "cooking appliances such as ranges, ovens, and cooktops",
        "microwaves": "microwave ovens and built-in installations",
        "exhaust_bath_heaters": "bathroom exhaust fans and integrated heaters",
        "garage_door_operators": "garage door opener mechanisms and controls",
        "dryer_exhaust": "clothes dryer exhaust ducts and exterior vents",
        "appliances_other": "miscellaneous appliances not otherwise listed"
    },
    "OPTIONAL": {
        "irrigation_systems": "landscape irrigation (sprinkler) system components",
        "pools_spas": "swimming pools, spas, hot tubs, and their related systems",
        "outbuildings": "freestanding structures such as sheds or guest houses",
        "private_wells": "private water well systems (coliform analysis recommended)",
        "private_septic": "private sewage disposal and septic systems",
        "optional_other": "optional systems not otherwise categorized"
    },
    "GENERAL": {
        "general": "the property"
    }
}

# Flattened version for easy key-based access
FLAT_SYSTEM_MAPPING = {
    subkey: desc
    for category in SYSTEM_NAME_MAPPING.values()
    for subkey, desc in category.items()
}

def get_prompt(system_types):
    descriptions = []

    for system_key in system_types:
        upper_key = system_key.upper()
        lower_key = system_key.lower()

        if upper_key in SYSTEM_NAME_MAPPING:
            descriptions.extend(SYSTEM_NAME_MAPPING[upper_key].values())
        elif lower_key in FLAT_SYSTEM_MAPPING:
            descriptions.append(FLAT_SYSTEM_MAPPING[lower_key])
        else:
            descriptions.append(FLAT_SYSTEM_MAPPING["general"])

    system_description = "; ".join(descriptions)
    return BASE_PROMPT.format(system_name=system_description)
