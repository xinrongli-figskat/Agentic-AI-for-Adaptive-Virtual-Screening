"""D7 immutable input verification. No GLM, no campaign."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import zipfile

ROOT = Path('/driveA/xinrong/agentic-screening')
BASE = ROOT / 'outputs/d7_20261021'
EXPECTED = {
 'campaign_v0/llm_controller.py': '30c1c75da16636518d947b1eecb7207c922034ce1863adc0417f9fa676dde2b7',
 'campaign_v0/campaign_core.py': '3044fb6b5f61bb435eb50a04dd8dcd23ed89abd314c420799c9dc4079d40f0a1',
 'outputs/d3_tnap_20261019/freeze_tnap_v1/freeze_receipt.json': 'f8801efbe28f73ddbcf9c5a2d493d862cbf124f311b6659e9224f2161b5bf662',
 'outputs/d3_tnap_20261019/freeze_tnap_v1/pool_manifest.json': 'c4206075c51db7c9fc14a9ab910b87c91adb82f5fd468dba74edba244d27feb1',
 'data/curation_private/frozen_dyrk3_v1/manifest.json': '3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235',
 'outputs/d5_20261020/e_menu_code_lock.json': '5cd4edae70c83519a75eb9e90068ad3444128cb0375239479c66d4f860625859',
 'outputs/d5_20261020/d5_report.md': '67529249605a1efceff3f4e90e4a09a3a1907388ba4b6a98acfab3a395c1ec5f',
 'outputs/d5_20261020/e_menu_results.json': '7abdc8ca49fd9944f312be0beeab046ba7a9c4aa1ff8d23686e21696401de319',
 'data/curation_private/d5_backups/d5_e_menu_private_20261020.zip': '2b812fc95cac56d225d5b3034940598ce05df12180bb403d7e17aeb81ce9440a',
 'deliveries_20261018/outputs/r3_ranked_numeric_private_20261018_v2/ranked_numeric_qualified_62.csv': 'dfb3569217454cd73a6c60b69128988aa1f57dc9866b7949728954933add47b9',
 'data/source_dbs/chembl_37/extracted/chembl_37.db': '4be13df3b68e25dcd0bff44bf094033b5aebe98f415acdc8c1cdf380e0c15142',
}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

if __name__ == '__main__':
    rows = []
    for relative, expected in EXPECTED.items():
        p = ROOT / relative
        actual = sha(p) if p.is_file() else None
        rows.append(dict(path=relative, expected=expected, actual=actual, match=expected==actual))
    z = ROOT / 'data/curation_private/d5_backups/d5_e_menu_private_20261020.zip'
    archive = dict(bytes=z.stat().st_size, members=len(zipfile.ZipFile(z).namelist())) if z.exists() else {}
    db_bytes = (ROOT / 'data/source_dbs/chembl_37/extracted/chembl_37.db').stat().st_size
    ok = all(r['match'] for r in rows) and archive==dict(bytes=2455539,members=760) and db_bytes==30480314368
    result = dict(utc=datetime.now(timezone.utc).isoformat(), passed=ok, inputs=rows, archive=archive, db_bytes=db_bytes)
    BASE.mkdir(parents=True, exist_ok=True)
    output = BASE / ('preflight_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2), flush=True)
    if not ok:
        raise SystemExit('Tier C: precondition mismatch')
