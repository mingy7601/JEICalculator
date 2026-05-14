import json

from calculate import calculate
from file_loader import load_file
from pprint import pprint

if __name__ == '__main__':
    recipes = {}
    load_file(recipes)
    #pprint(recipes)
    calculate(recipes)
