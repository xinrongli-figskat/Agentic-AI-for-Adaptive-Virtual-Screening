from pathlib import Path
p=Path('outputs/s_restructure_20261018/build_index.py')
s=p.read_text(encoding='utf-8')
s=s.replace("rows.append((n,cat,status,purpose,sup))\n# B1 relation", "rows.append((n,cat,status,purpose,sup))\n# The index is itself a top-level item and is represented explicitly.\nrows.append(('INDEX.md','devlog','—','本索引文件；逐项覆盖其余顶层条目',''))\n# B1 relation")
p.write_text(s,encoding='utf-8')
