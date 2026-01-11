import json
from uvr import read_data, filter_empty_values
import pprint
cfg = json.load(open('config.json'))
uvr_cfg = cfg.get('uvr',{})
vals, status = read_data(uvr_cfg)
vals = filter_empty_values(vals)
for i, v in enumerate(vals):
    print(f"--- Page {i} keys ---")
    for k in sorted(v.keys()):
        if 'speicher' in k.lower() or 'puffer' in k.lower() or 'speich' in k.lower():
            print(k)
    print('Total keys:', len(v))
    print()
