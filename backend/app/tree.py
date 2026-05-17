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

def build_tree(item, recipes, step=0, max_steps=3, name=None, id_to_name=None, visited=None, multiplier=1):
    if visited is None:
        visited = set()

    if item in visited:
        return {"item": item, "name": name or (id_to_name.get(item) if id_to_name else item), "source": "cycle", "qty": multiplier}

    if step >= max_steps:
        return {"item": item, "name": name or (id_to_name.get(item) if id_to_name else item), "source": "limit", "qty": multiplier}

    options = recipes.get(item)
    if not options:
        return {"item": item, "name": name or (id_to_name.get(item) if id_to_name else item), "source": "base", "qty": multiplier}

    sorted_options = sorted(options, key=lambda r: sum(o.get("qty", 1) for o in r.get("outputs", [])), reverse=True)

    child_visited = visited | {item}

    for recipe in sorted_options:
        input_ids = [inp["id"] for inp in recipe.get("inputs", [])]

        if any(would_cycle(inp_id, item, recipes, child_visited) for inp_id in input_ids):
            continue

        # How many of `item` does this recipe produce?
        output_qty = next(
            (o.get("qty", 1) for o in recipe.get("outputs", []) if o.get("id") == item),
            1
        )
        # How many times must we run this recipe to satisfy `multiplier` units?
        import math
        runs = math.ceil(multiplier / output_qty)

        return {
            "item": item,
            "name": name or (id_to_name.get(item) if id_to_name else item),
            "qty": multiplier,          # how many are actually needed by the parent
            "runs": runs,               # how many recipe executions that requires
            "step": step,
            "category": recipe.get("category"),
            "category_name": recipe.get("category_name"),
            "image_path": recipe.get("image_path", ""),
            "inputs": [
                build_tree(
                    inp["id"], recipes, step + 1, max_steps,
                    name=inp.get("name"), id_to_name=id_to_name,
                    visited=child_visited,
                    multiplier=runs * inp.get("qty", 1)   # ← scaled quantity
                )
                for inp in recipe.get("inputs", [])
            ],
            "outputs": recipe.get("outputs", [])
        }

    return {"item": item, "name": name or (id_to_name.get(item) if id_to_name else item), "source": "cycle", "qty": multiplier}

def calculate(recipes):
    #product = test_input
    #(build_tree(product,recipes))
    #pprint(result)

    return True
