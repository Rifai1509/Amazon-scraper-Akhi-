import glob
import json
import os
import re
import pandas as pd

files = sorted(glob.glob('./details/*.json'), key=lambda x: float(re.findall("(\d+)", x)[0]))
datas = []
for f in files:
    with open(f) as json_file:
        data = json.load(json_file)
    datas.append(data)

df = pd.DataFrame(datas)
df.to_excel('results.xlsx', index=False)
