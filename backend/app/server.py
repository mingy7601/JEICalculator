import json
import os
import time
from flask import Flask, jsonify, request
from flask_cors import CORS
from tree import build_tree, would_cycle
from file_loader import load_file, prune
from summarize_ingredients import sum_leaf_ingredients

MAX_STEPS = 5

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data/locales/en_us", "index.json")

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "data"), static_url_path="/static/data")
CORS(app)

def build_name_to_id(dictionary):
    result = {}
    for item_id, options in dictionary.items():
        for recipe in options:
            for output in recipe.get("outputs", []):
                if output.get("id") == item_id and output.get("name"):
                    result[output["name"].lower()] = item_id
    return result

recipes = {}
emc_values = {}
start = time.perf_counter()
load_file(recipes, DATA_PATH, emc_values)
print(f"[loader] load_file: {time.perf_counter() - start:.2f}s")

start = time.perf_counter()
name_to_id = build_name_to_id(recipes)
print(f"[loader] name_to_id: {time.perf_counter() - start:.2f}s")

start = time.perf_counter()
prune(recipes)
print(f"[loader] prune: {time.perf_counter() - start:.2f}s")

def tree_to_tsx(node, is_root=False):
    item_id = node.get("item", "unknown")
    source = node.get("source")
    inputs = node.get("inputs", [])

    if is_root:
        node_type = "root"
    elif source == "emc":
        node_type = "emc"
    elif source in ("base", "Unknown"):
        node_type = "resource"
    elif not inputs:
        node_type = "component"
    else:
        node_type = "module"

    label = node.get("name", "unknown")
    for output in node.get("outputs", []):
        if output.get("id") == item_id:
            label = output.get("name")
            break

    qty = node.get("qty", 1)
    qty_str = str(int(qty) if isinstance(qty, float) and qty.is_integer() else qty)
    label = label + " ×" + qty_str

    if node_type == "emc":
        meta = "emc"
    else:
        meta = node.get("category_name", "N/A")
    image_url = "http://localhost:5000/static/" + node.get("image_path", "")

    result = {
        "id": item_id,
        "label": label,
        "type": node_type,
        "meta": meta,
        "imageUrl": image_url,
    }

    if inputs:
        result["children"] = [tree_to_tsx(child) for child in inputs]

    return result

def handle_input(item):
    item_id = name_to_id.get(item.lower(), item)

    options = recipes.get(item_id, [])
    root_name = item
    if options:
        best = max(options, key=lambda r: sum(o.get("qty", 1) for o in r.get("outputs", [])))
        for output in best.get("outputs", []):
            if output.get("id") == item_id:
                root_name = output.get("name", item)
                break
    return item_id, root_name

@app.get("/tree")
def tree():
    item = request.args.get("item")
    if not item:
        return jsonify({"error": "missing item param"}), 400

    overrides_raw = request.args.get("overrides", "{}")
    try:
        overrides = {k: int(v) for k, v in json.loads(overrides_raw).items()}
    except (ValueError, TypeError):
        overrides = {}

    item_id, root_name = handle_input(item)
    start = time.perf_counter()
    raw = build_tree(item_id, recipes, 0, MAX_STEPS, name=root_name, overrides=overrides, emc_values=emc_values)
    print(f"[tree]   build_tree({item_id}): {time.perf_counter() - start:.3f}s")
    return jsonify(tree_to_tsx(raw, is_root=True))

@app.get("/ingredients")
def ingredients():
    item = request.args.get("item")
    if not item:
        return jsonify({"error": "missing item param"}), 400
    item_id, _ = handle_input(item)
    raw = build_tree(item_id, recipes, 0, MAX_STEPS, emc_values=emc_values)
    totals = sum_leaf_ingredients(raw)
    return jsonify(totals)

@app.get("/alternatives")
def alternatives():
    item_id = request.args.get("item_id")
    if not item_id:
        return jsonify({"error": "missing item_id param"}), 400

    options = recipes.get(item_id, [])
    if not options:
        return jsonify([])

    result = []
    for recipe in options:
        input_ids = [inp["id"] for inp in recipe.get("inputs", [])]
        if any(would_cycle(inp_id, item_id, recipes) for inp_id in input_ids):
            continue
        result.append({
            "recipe_id": recipe["id"],
            "category_name": recipe.get("category_name", "N/A"),
            "image_url": "http://localhost:5000/static/" + recipe.get("image_path", ""),
            "inputs": [
                {"name": inp.get("name", inp["id"]), "qty": inp.get("qty", 1)}
                for inp in recipe.get("inputs", [])
            ],
            "outputs": recipe.get("outputs", []),
        })

    return jsonify(result)

if __name__ == "__main__":
    app.run(port=5000, debug=True)