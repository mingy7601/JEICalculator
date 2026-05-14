import json
from pprint import pprint
from collections import Counter

#categories [{id, uid, title, modName, recipeCount,recipes}]

FILE_DIR = 'index.slim.json'

def write_file(json_file):
    with open("dump.json", "w") as file:
        json.dump(json_file, file, indent=4)

def compress_inputs(inputs):
    counts = Counter(item["id"] for item in inputs)

    return [
        {"id": item_id, "qty": qty}
        for item_id, qty in counts.items()
    ]

def load_file(recipes):
    with open(FILE_DIR, 'r', encoding="utf-8") as file:
        data = json.load(file)
        # print(data["categories"])
        # new_json = json.dumps(data["categories"],indent=1)
        #categories = json.dumps(data["categories"], indent=1)

    for category in data["categories"]:
        uid = category["uid"]
        for recipe in category["recipes"]:
            inputs = recipe.get("inputs",[])
            outputs = recipe.get("outputs",[])

            if not outputs:
                continue

            recipe_data = {
                "category": uid,
                "inputs": compress_inputs(inputs),
                "outputs": outputs
            }

            for output in outputs:
                key = output["id"]
                if key in recipes:
                    recipes[key].append(recipe_data)
                else:
                    recipes[key] = [recipe_data]