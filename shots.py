import json

SHOT_LIBRARY = json.load(open("rec_shots.json"))["players"]

def generate_preset_options(shot_library):
    options = []
    for player, shot_types in shot_library.items():
        for shot_type, subtypes in shot_types.items():
            for subtype, config in subtypes.items():

                # Create a unique key we will use to look up the preset
                key = f"{player}|{shot_type}|{subtype}"
                
                # User-friendly label
                label = f"{player} – {shot_type} – {subtype}"

                options.append({"label": label, "value": key})
    return options

preset_options = generate_preset_options(SHOT_LIBRARY)

def generate_preset_lookup(shot_library):
    lookup = {}
    for player, shot_types in shot_library.items():
        for shot_type, subtypes in shot_types.items():
            for subtype, config in subtypes.items():

                key = f"{player}|{shot_type}|{subtype}"
                lookup[key] = config
    return lookup

SHOT_PRESETS = generate_preset_lookup(SHOT_LIBRARY)