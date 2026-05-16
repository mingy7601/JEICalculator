from pprint import pprint

#test_input = "item:contenttweaker:mythic_machine_case:0"

def would_cycle(input_id, target_id, recipes, visited, depth=0, max_depth=2):
    """Returns True if expanding input_id would eventually require target_id."""
    if depth > max_depth:
        return False
    if input_id == target_id:
        return True
    if input_id in visited:
        return False

    options = recipes.get(input_id)
    if not options:
        return False

    best = max(options, key=lambda r: sum(o.get("qty", 1) for o in r.get("outputs", [])))
    new_visited = visited | {input_id}

    return any(
        would_cycle(inp["id"], target_id, recipes, new_visited, depth + 1, max_depth)
        for inp in best.get("inputs", [])
    )

def build_tree(item, recipes, step=0, max_steps=3, name=None, id_to_name=None, visited=None):
    if visited is None:
        visited = set()

    if item in visited:
        return {"item": item, "name": name or (id_to_name.get(item) if id_to_name else item), "source": "cycle"}

    if step >= max_steps:
        return {"item": item, "name": name or (id_to_name.get(item) if id_to_name else item), "source": "limit"}

    options = recipes.get(item)
    if not options:
        return {"item": item, "name": name or (id_to_name.get(item) if id_to_name else item), "source": "base"}

    # Sort by highest output qty
    sorted_options = sorted(options, key=lambda r: sum(o.get("qty", 1) for o in r.get("outputs", [])), reverse=True)

    child_visited = visited | {item}

    for recipe in sorted_options:
        input_ids = [inp["id"] for inp in recipe.get("inputs", [])]

        # checks for cycle
        if any(would_cycle(inp_id, item, recipes, child_visited) for inp_id in input_ids):
            continue

        return {
            "item": item,
            "name": name or (id_to_name.get(item) if id_to_name else item),
            "step": step,
            "category": recipe.get("category"),
            "category_name": recipe.get("category_name"),
            "image_path" : recipe.get("image_path",""),
            "inputs": [
                {**build_tree(inp["id"], recipes, step + 1, max_steps, name=inp.get("name"), id_to_name=id_to_name, visited=child_visited), "qty": inp.get("qty", 1)}
                for inp in recipe.get("inputs", [])
            ],
            "outputs": recipe.get("outputs", [])
        }

    # All recipes cause a cycle, treat as base material
    return {"item": item, "name": name or (id_to_name.get(item) if id_to_name else item), "source": "cycle"}

def calculate(recipes):
    #product = test_input
    #(build_tree(product,recipes))
    #pprint(result)

    return True
