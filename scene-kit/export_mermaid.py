import json, argparse

def main():
    ap = argparse.ArgumentParser(description='Export expanded scene JSON to a Mermaid flowchart for report/debugging')
    ap.add_argument('scene', help='Path to expanded scene JSON')
    ap.add_argument('--out', default='output/scene.mmd')
    args = ap.parse_args()

    with open(args.scene,'r',encoding='utf-8') as f:
        sc = json.load(f)

    nodes = {n['nodeId']: n for n in sc.get('nodes', [])}
    endings = {e['endingId']: e for e in sc.get('endings', [])}

    lines = ['flowchart TD']
    # intro node
    if sc.get('nodes'):
        lines.append(f'  START([START]) --> {sc["nodes"][0]["nodeId"]}')
    for n in sc.get('nodes', []):
        nid = n['nodeId']
        label = nid
        lines.append(f'  {nid}["{label}"]')
        for c in n.get('choices', []):
            to = c.get('to')
            edge_label = c.get('moveType') or c.get('text','').replace('"','\"')
            if to in nodes:
                lines.append(f'  {nid} -->|"{edge_label}"| {to}')
            else:
                end_id = to
                if end_id in endings:
                    lines.append(f'  {end_id}(["END: {end_id}"])')
                lines.append(f'  {nid} -->|"{edge_label}"| {end_id}')
    with open(args.out,'w',encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('Wrote', args.out)

if __name__ == '__main__':
    main()
