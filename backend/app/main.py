import json

from backend.app.file_loader import prune
from backend.app.tree import build_tree
from file_loader import load_file

if __name__ == '__main__':
    recipes = {}
    load_file(recipes, "backend/data/locales/en_us/index.json")
    prune(recipes)
    with open("data.json", "w") as f:
        json.dump(recipes,f, indent=2)

    raw = build_tree("item:nuclearcraft:melter_idle", recipes, 0, 10, name="Melter")
    with open("tree.json", "w") as f:
        json.dump(raw,f, indent=2)