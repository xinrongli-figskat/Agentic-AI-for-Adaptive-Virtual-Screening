import csv
from pathlib import Path
s=list(csv.DictReader(Path('outputs/s_restructure_20261018/script_classification.csv').open(encoding='utf-8-sig')))
t=list(csv.DictReader(Path('outputs/s_restructure_20261018/test_movement_assessment.csv').open(encoding='utf-8-sig')))
lines=['# S5 延后移动清单','','这些文件先留在原路径，避免在本卡中修改代码和测试。恢复移动前需单独改造并验证引用。','', '## 脚本','']
for r in s:
 if r['move_decision']=='defer': lines.append(f'- `{r["source"]}`：{r["reason"]}')
lines+=['','## 测试','']
for r in t: lines.append(f'- `outputs/{r["test"]}`：{r["reason"]}')
Path('outputs/deferred_moves.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
# Explanatory documents before moving files, so the dedicated rename commits remain pure.
Path('outputs/brief').mkdir(exist_ok=True); Path('outputs/protocols').mkdir(exist_ok=True); Path('outputs/scripts').mkdir(exist_ok=True); Path('outputs/tests').mkdir(exist_ok=True); Path('outputs/src').mkdir(exist_ok=True); Path('outputs/env').mkdir(exist_ok=True)
Path('outputs/brief/README.md').write_text('# Brief materials\n\n原始 brief、与 brief 的进度对照及相关复核材料。旧位置见 `../PATH_MIGRATION_20261018.csv`。\n',encoding='utf-8')
Path('outputs/protocols/README.md').write_text('# Protocols\n\n`frozen/` 保存已经固定的规则与协议；`drafts/` 保存尚未冻结的指导与草案。移动不改变协议内容。\n',encoding='utf-8')
Path('outputs/scripts/README.md').write_text('# One-time scripts\n\n脚本按用途分类。因外部路径引用或 `__file__` 目录假设而暂缓的脚本见 `../deferred_moves.md`。\n',encoding='utf-8')
Path('outputs/tests/README.md').write_text('# Tests\n\n测试暂留在原路径；当前测试导入顶层脚本/包或依赖 `__file__` 相对路径。逐项理由见 `../s_restructure_20261018/test_movement_assessment.csv`。\n',encoding='utf-8')
Path('outputs/src/README.md').write_text('# Reusable code packages\n\n代码包仍在 `outputs/` 顶层，保持现有 import 和运行记录路径。迁移需先改引用，见 `../deferred_moves.md`。\n',encoding='utf-8')
Path('outputs/env/README.md').write_text('# Local environment files\n\n本机 SSH 配置存放于此目录且由 `.gitignore` 排除，不纳入版本控制。\n',encoding='utf-8')
