import json
from collections import Counter
import re

#categories [{id, uid, title, modName, recipeCount,recipes}]

BLACKLISTED_CATEGORIES = ["tconstruct:harvest_stats",
                          "tconstruct:projectile_stats",
                          "tconstruct:ranged_stats",
                          re.compile(r"tce_*", re.IGNORECASE),
                          "thermaldynamics.covers",
                          "TechReborn.ThermalGenerator",
                          "TechReborn.PlasmaGenerator", "TechReborn.GasTurbine","TechReborn.DieselGenerator",
                          "reim.multiblock","projectex.alchemy_table",
                          re.compile(r"plethora-core:*", re.IGNORECASE),
                          "packagedauto:package_contents", "compressed_cobblestone", "nae2:cell_view",
                          re.compile(r"mysticalagriculture:*", re.IGNORECASE),
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

def load_file(recipes, file_dir):
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