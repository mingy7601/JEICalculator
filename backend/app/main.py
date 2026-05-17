import json

from backend.app.file_loader import prune, apply_emc
from backend.app.tree import build_tree
from file_loader import load_file

if __name__ == '__main__':
    recipes = {}
    emc_values = {}
    load_file(recipes, "backend/data/locales/en_us/index.json", emc_values)
    prune(recipes)
    apply_emc(recipes, emc_values)
    with open("data.json", "w") as f:
        json.dump(recipes,f, indent=2)

    raw = build_tree("item:nuclearcraft:melter_idle", recipes, 0, 10, name="Melter")
    with open("tree.json", "w") as f:
        json.dump(raw, f, indent=2)
    with open("emc.json", "w") as f:
        json.dump(emc_values,f, indent=2)