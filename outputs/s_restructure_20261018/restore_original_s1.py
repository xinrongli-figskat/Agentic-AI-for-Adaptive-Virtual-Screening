import subprocess
from pathlib import Path
base=Path('.')
paths=['outputs/s_restructure_20261018/inventory_before.csv','outputs/s_restructure_20261018/inventory_summary.md','outputs/s_restructure_20261018/s1_digest_check.json','outputs/s_restructure_20261018/duplicates.csv','outputs/s_restructure_20261018/hardcoded_paths.csv','outputs/s_restructure_20261018/recorded_paths.csv']
for rel in paths:
 data=subprocess.check_output(['git','show',':'+rel])
 (base/rel).write_bytes(data)
print('restored_original_s1_artifacts',len(paths))
