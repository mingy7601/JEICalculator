#test_input = "item:contenttweaker:mythic_machine_case:0"

# Lower index = higher priority. Categories not in the list are deprioritized.
MACHINE_PRIORITY = [
    "nuclearcraft_manufactory",
    "thermalexpansion.furnace",
    "minecraft.crafting",
]

def machine_priority(recipe):
    category = recipe.get("category", "")
    try:
        return MACHINE_PRIORITY.index(category)
    except ValueError:
        return len(MACHINE_PRIORITY)

def output_qty(recipe, item_id):
    for o in recipe.get("outputs", []):
        if o["id"] == item_id:
            return o.get("qty", 1)
    return 0

def would_cycle(input_id, target_id, recipes, depth=0, max_depth=2):
    """Returns True if no non-cyclic recipe exists for input_id."""
    if input_id == target_id:
        return True
    if depth >= max_depth:
        return False

    options = recipes.get(input_id)
    if not options:
        return False

    viable = [
        r for r in options
        if not any(
            would_cycle(inp["id"], target_id, recipes, depth + 1, max_depth)
            for inp in r.get("inputs", [])
        )
    ]

    return len(viable) == 0

def build_tree(item, recipes, step=0, max_steps=3, name=None, id_to_name=None, visited=None, overrides=None, emc_values=None):
    if overrides is None:
        overrides = {}
    if visited is None:
        visited = set()
    if emc_values is None:
        emc_values = {}

    def resolve_name():
        return name or (id_to_name.get(item) if id_to_name else item)

    if item in visited:
        return {"item": item, "name": resolve_name(), "source": "cycle"}
    if step >= max_steps:
        return {"item": item, "name": resolve_name(), "source": "limit"}

    options = recipes.get(item)
    if not options:
        return {"item": item, "name": resolve_name(), "source": "base"}

    child_visited = visited | {item}

    # Step 1: filter to only non-cyclic recipes
    viable = [
        r for r in options
        if not any(would_cycle(inp["id"], item, recipes) for inp in r.get("inputs", []))
    ]

    if not viable:
        return {"item": item, "name": resolve_name(), "source": "cycle"}

    # Step 2: sort viable by output qty descending
    viable = sorted(
        viable,
        key=lambda r: (
            -output_qty(r, item),
            machine_priority(r),
        )
    )

    # Step 3: apply override — if valid and viable, promote to front
    override_id = overrides.get(item)
    if override_id is not None:
        preferred = next((r for r in viable if r["id"] == override_id), None)
        if preferred:
            viable = [preferred] + [r for r in viable if r["id"] != override_id]

    # Step 4: pick best (first after sorting/override)
    recipe = viable[0]

    return {
        "item": item,
        "name": resolve_name(),
        "step": step,
        "category": recipe.get("category"),
        "category_name": recipe.get("category_name"),
        "image_path": recipe.get("image_path", ""),
        "inputs": [
            {
                **(
                    build_tree(
                        inp["id"], recipes, step + 1, max_steps,
                        name=inp.get("name"),
                        id_to_name=id_to_name,
                        visited=child_visited,
                        overrides=overrides,
                        emc_values=emc_values,
                    )
                    if not emc_values.get(inp["id"])
                    else {
                        "item": inp["id"],
                        "name": inp.get("name", inp["id"]),
                        "source": "emc",
                    }
                ),
                "qty": inp.get("qty", 1),
            }
            for inp in recipe.get("inputs", [])
        ],
        "outputs": recipe.get("outputs", []),
    }
def calculate(recipes):
    #product = test_input
    #(build_tree(product,recipes))
    #pprint(result)

    return True
