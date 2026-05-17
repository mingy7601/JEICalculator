import json
from collections import Counter

#categories [{id, uid, title, modName, recipeCount,recipes}]

def write_file(json_file):
    with open("dump.json", "w") as file:
        json.dump(json_file, file, indent=4)

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