import sys
sys.path.insert(0, '.')
from app import app

with open('debug_routes_output.txt', 'w') as f:
    f.write("===== PROFILE ROUTES =====\n")
    for rule in app.url_map.iter_rules():
        if 'profile' in rule.rule:
            methods = list(rule.methods - {'HEAD', 'OPTIONS'})
            f.write(f"{rule.rule:<50} -> {methods}\n")

    f.write("\n===== ALL CONTACT ROUTES =====\n")
    for rule in app.url_map.iter_rules():
        if 'contact' in rule.rule:
            methods = list(rule.methods - {'HEAD', 'OPTIONS'})
            f.write(f"{rule.rule:<50} -> {methods}\n")

print("Output written to debug_routes_output.txt")
