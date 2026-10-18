from pathlib import Path
p=Path('outputs/s_restructure_20261018/s1_inventory.py')
s=p.read_text(encoding='utf-8')
s=s.replace("if p.is_dir(): cats['directory']+=1\n    elif p.suffix.lower()=='.py': cats['.py']+=1\n    elif p.name.startswith('test_') and p.suffix.lower()=='.py': cats['test_*.py']+=1", "if p.is_dir(): cats['directory']+=1\n    elif p.name.startswith('test_') and p.suffix.lower()=='.py': cats['test_*.py']+=1\n    elif p.suffix.lower()=='.py': cats['.py']+=1")
p.write_text(s,encoding='utf-8')
