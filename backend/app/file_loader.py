import json
from collections import Counter
import re

#categories [{id, uid, title, modName, recipeCount,recipes}]

BLACKLISTED_CATEGORIES = ["tconstruct:harvest_stats",
                          "tconstruct:projectile_stats",
                          "tconstruct:ranged_stats",
                          re.compile(r"tce.*", re.IGNORECASE),
                          "thermaldynamics.covers",
                          "TechReborn.ThermalGenerator",
                          "TechReborn.PlasmaGenerator", "TechReborn.GasTurbine","TechReborn.DieselGenerator",
                          "reim.multiblock","projectex.alchemy_table",
                          re.compile(r"plethora-core.*", re.IGNORECASE),
                          "packagedauto:package_contents", "compressed_cobblestone", "nae2:cell_view",
                          re.compile(r"mysticalagriculture:.*", re.IGNORECASE),
                          "justenoughreactors:turbine", "justenoughreactors:reactor", "jeresources.villager",
                          "if_manual_category", "ie.bottlingMachine", "hatchery.generator.recipe"
                          ]

def write_file(json_file):
    with open("dump.json", "w") as file:
        json.dump(json_file, file, indent=4)

def is_blacklisted(category_name: str) -> bool:
    for entry in BLACKLISTED_CATEGORIES:
        if isinstance(entry, str):
            if entry == category_name:
                return True
        elif isinstance(entry, re.Pattern):
            if entry.search(category_name):
                return True
    return False

def compress_inputs(inputs):
    counts = Counter(item["id"] for item in inputs)
    names = {item["id"]: item.get("name") for item in inputs}

    return [
        {"id": item_id, "qty": qty, "name": names.get(item_id)}
        for item_id, qty in counts.items()
    ]

def prune(recipes):
    # removes squeezer recipes with cans
    pattern = re.compile(r"item:forestry:can.*", re.IGNORECASE)
    prune_recipes(recipes, lambda r:
    r.get("category") == "forestry.squeezer" and
    any(pattern.search(inp["id"]) for inp in r.get("inputs", [])))

    # removes fluid transposer - fills
    pattern = re.compile(r"item:thermalexpansion:reservoir:.*", re.IGNORECASE)
    prune_recipes(recipes, lambda r:
    r.get("category") == "thermalexpansion.transposer_fill" and
    any(pattern.search(inp["id"]) for inp in r.get("inputs", [])))

    # removes fluid transposer - fills
    pattern = re.compile(r"item:thermalexpansion:reservoir:.*", re.IGNORECASE)
    prune_recipes(recipes, lambda r:
    r.get("category") == "thermalexpansion.transposer_extract" and
    any(pattern.search(inp["id"]) for inp in r.get("inputs", [])))

def prune_recipes(recipes, predicate):
    """Remove individual recipes matching predicate. Remove the key entirely if no recipes remain."""
    keys_to_delete = []
    for item_id, options in recipes.items():
        recipes[item_id] = [r for r in options if not predicate(r)]
        if not recipes[item_id]:
            keys_to_delete.append(item_id)
    for key in keys_to_delete:
        del recipes[key]

def apply_emc(recipes, emc_values):
    for recipe_list in recipes.values():
        for recipe in recipe_list:
            for inp in recipe["inputs"]:
                entry = emc_values.get(inp["id"])
                if entry:
                    inp["emc"] = entry["emc"]


def load_file(recipes, file_dir, emc_values=None):
    recipe_id = 0
    with open(file_dir, 'r', encoding="utf-8") as file:
        data = json.load(file)

    for category in data["categories"]:
        if is_blacklisted(category["uid"]):
            continue
        uid = category["uid"]
        for recipe in category["recipes"]:
            recipe_id += 1
            inputs = recipe.get("inputs",[])
            raw_outputs = recipe.get("outputs",[])
            category_name = recipe.get("categoryTitle", "")
            outputs = [{"id": o["id"], "name": o.get("name"), "qty": o.get("qty", 1)} for o in raw_outputs]
            image_path = recipe.get("img","")
            name = raw_outputs[0].get("name", "") if raw_outputs else ""

            if not outputs:
                continue

            if emc_values is not None:
                for slot in recipe.get("slots", []):
                    tooltip = slot.get("tooltip", [])
                    emc = None
                    emc_idx = None
                    for i, line in enumerate(tooltip):
                        match = re.search(r'(?<!stack )emc\s*:\s*([\d,]+)', line, re.IGNORECASE)
                        if match:
                            emc = int(match.group(1).replace(",", ""))
                            emc_idx = i
                    if emc is None or emc_idx is None:
                        continue
                    for line in tooltip:
                        key = line.strip()
                        if ":" in key and not re.match(r'\s*(stack\s+)?emc\s*:', key, re.IGNORECASE):
                            if key not in emc_values:
                                key = "item:" + key
                                emc_values[key] = {
                                    "name": tooltip[0] if tooltip else "",
                                    "emc": emc
                                }

            recipe_data = {
                "id": recipe_id,
                "name" : name,
                "category": uid,
                "category_name": category_name,
                "outputs": outputs,
                "inputs": compress_inputs(inputs),
                "image_path": image_path
            }

            for output in outputs:
                key = output["id"]
                if key in recipes:
                    recipes[key].append(recipe_data)
                else:
                    recipes[key] = [recipe_data]