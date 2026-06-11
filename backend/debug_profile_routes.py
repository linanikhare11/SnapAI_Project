import sys
sys.path.insert(0, '.')
from app import app

print("\n=== DETAILED PROFILE ROUTE ANALYSIS ===\n")

for rule in app.url_map.iter_rules():
    if 'profile' in rule.rule and 'contact' in rule.rule:
        print(f"Route Rule: {rule.rule}")
        print(f"  Endpoint: {rule.endpoint}")
        print(f"  Methods: {rule.methods}")
        print(f"  Strict Slashes: {rule.strict_slashes}")
        print(f"  Converter: {rule._converters}")
        print()

print("\n=== ALL BLUEPRINT ROUTES ===\n")
for rule in app.url_map.iter_rules():
    if 'profile' in rule.rule:
        print(f"{rule.rule:<50} {list(rule.methods - {'HEAD', 'OPTIONS'})}")
