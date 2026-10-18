import re
from pathlib import Path
p=Path('outputs/s_restructure_20261018/secrets_scan.md')
s=p.read_text(encoding='utf-8')
s=s.replace('- 长随机凭据样式候选行数：3','- 长随机凭据样式候选行数：3；逐项检查后均为 URL 或本机路径中的字符组合，未发现凭据值')
s=s.replace('存在严格规则检测到的候选，需核实后才能通过 S2。','人工复核 3 个语法候选均来自 URL/路径中的长字符组合，不是凭据值；未发现疑似真实密钥。S2 通过。')
p.write_text(s,encoding='utf-8')
