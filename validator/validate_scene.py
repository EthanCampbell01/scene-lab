
import json, sys, os, argparse
from jsonschema import Draft202012Validator

def main():
    ap = argparse.ArgumentParser(description="Validate expanded scene JSON against schema")
    ap.add_argument("path", help="Path to expanded scene JSON")
    ap.add_argument("--schema", default="validator/schema/expanded_scene.schema.json")
    args = ap.parse_args()

    with open(args.schema, "r", encoding="utf-8") as f:
        schema = json.load(f)
    with open(args.path, "r", encoding="utf-8") as f:
        data = json.load(f)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        print("❌ Validation failed with errors:\n")
        for e in errors:
            loc = "/".join([str(x) for x in e.path])
            print(f"- At {loc or 'root'}: {e.message}")
        sys.exit(1)
    print("✅ JSON is valid!")
    sys.exit(0)

if __name__ == "__main__":
    main()
