from flask import Flask, jsonify, request
from flask_cors import CORS
from tree import build_tree
from file_loader import load_file
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data/locales/en_us", "index.json")

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "data"), static_url_path="/static/data")
CORS(app)

def tree_to_tsx(node, is_root=False):
    #print(node)
    item_id = node.get("item", "unknown")
    source = node.get("source")
    inputs = node.get("inputs", [])

    # Map depth/source to a NodeType
    if is_root:
        node_type = "root"
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

    qty = node.get("qty", "1")
    label = label + " x " + str(qty)

    meta = node.get("category_name", "N/A")

    image_url = "http://localhost:5000/static/" + node.get("image_path", "")
    #print ("path", node.get("image_path", "NOTHING"))
    result = {
        "id": item_id,
        "label": label,
        "type": node_type,
        "meta": meta,
        "imageUrl" : image_url,
    }

    if inputs:
        result["children"] = [tree_to_tsx(child) for child in inputs]

    return result

@app.get("/tree")
def tree():
    recipes = {}
    load_file(recipes, DATA_PATH)
    # Build this once when the server starts, outside the route
    name_to_id = {}
    for item_id, options in recipes.items():
        for recipe in options:
            for output in recipe.get("outputs", []):
                if output.get("id") == item_id and output.get("name"):
                    name_to_id[output["name"].lower()] = item_id
    item = request.args.get("item")
    if not item:
        return jsonify({"error": "missing item param"}), 400

    # Try to resolve name to id, fall back to treating it as a raw id
    item_id = name_to_id.get(item.lower(), item)

    options = recipes.get(item_id, [])
    root_name = item  # use the name the user typed as fallback
    if options:
        best = max(options, key=lambda r: sum(o.get("qty", 1) for o in r.get("outputs", [])))
        for output in best.get("outputs", []):
            if output.get("id") == item_id:
                root_name = output.get("name", item)
                break

    raw = build_tree(item_id, recipes, 0, 5, name=root_name)
    return jsonify(tree_to_tsx(raw, is_root=True))

if __name__ == "__main__":
    app.run(port=5000, debug=True)