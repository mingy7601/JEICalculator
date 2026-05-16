import json
import os

from calculate import calculate
from file_loader import load_file
from pprint import pprint

if __name__ == '__main__':
    recipes = {}
    print(os.path.abspath("data.json"))
    load_file(recipes, "backend/data/locales/en_us/index.json")
    #pprint(recipes)
    with open("data.json", "w") as f:
        json.dump(recipes,f, indent=2)