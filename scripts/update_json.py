import json
import yaml
import os

# Ensure the static directories exist
os.makedirs("static/.well-known", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Update .well-known files
with open('static/.well-known/openapi.yaml', 'r') as f:
    well_known_data = yaml.safe_load(f)

with open('static/.well-known/openapi.json', 'w') as f:
    json.dump(well_known_data, f, indent=2)

# Update root-level files
with open('static/openapi.yaml', 'r') as f:
    root_data = yaml.safe_load(f)

with open('static/openapi.json', 'w') as f:
    json.dump(root_data, f, indent=2)

print("JSON files updated successfully in both locations!")