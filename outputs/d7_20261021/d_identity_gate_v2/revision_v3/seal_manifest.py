"""Create this revision's manifest without rewriting any historical manifest."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
root=Path(__file__).resolve().parent
p=root/'MANIFEST.json'
assert not p.exists()
members=[{'path':f.relative_to(root).as_posix(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size} for f in sorted(root.rglob('*')) if f.is_file() and f.name!='MANIFEST.json']
manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'post_exposure':True,'status':'S1_VERIFIED_NO_GLM_AWAITING_ROOT_RELEASE','glm_calls':0,'files':members}
p.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'members':len(members),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2))
