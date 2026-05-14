from pprint import pprint

test_input = "item:minecraft:map"


def get_input():
    print("Enter final product")
    product = input()
    return product

def calculate(recipes):
    product = test_input #get_input()
    result = recipes.get(product)
    pprint(result)
    if result is None:
        return False


    return True
