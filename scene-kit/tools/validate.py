import json, sys, argparse
from jsonschema import validate, Draft7Validator
from jsonschema.exceptions import ValidationError

def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    ap = argparse.ArgumentParser(description='Validate expanded VN JSON against schema')
    ap.add_argument('--schema', default='schemas/expanded.scene.schema.json')
    ap.add_argument('--file', required=True, help='Path to expanded.scene.json')
    args = ap.parse_args()

    data = load(args.file)
    schema = load(args.schema)

    v = Draft7Validator(schema)
    errors = sorted(v.iter_errors(data), key=lambda e: e.path)
    if errors:
        print('INVALID JSON:')
        for e in errors:
            path = ''.join(['/' + str(p) for p in e.path])
            print(f' - {path}: {e.message}')
        sys.exit(1)
    else:
        print('OK: file matches schema.')

if __name__ == '__main__':
    main()
