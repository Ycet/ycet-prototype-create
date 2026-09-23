#!/usr/bin/env python3
"""v4 文档、框架与源代码一致性检查。"""
import ast,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    errors=[]
    required=['scripts/shell_theme.py','assets/shell-theme.css','scripts/prototype_syntax.py','docs/workbench-request.md','docs/workbench-maintenance.md','docs/prototype-validation.md','assets/nonframe.css','VERSION','SKILL.md','agents/openai.yaml','docs/function-1-requirements.md','docs/function-2-ui-direction.md','docs/function-3-prototype-production.md','docs/function-4-existing-prototype-edit.md','docs/function-5-workbench.md','docs/shared-change-policy.md','docs/shared-prototype-standards.md','docs/shared-workbench-protocol.md','docs/prototype-types.md','scripts/build_prototype.py','scripts/prototype_document.py','scripts/prototype_guard.py']
    for name in required:
        if not (ROOT/name).is_file():errors.append('缺少 '+name)
    if (ROOT/'VERSION').read_text().strip()!='4.2.3':errors.append('版本不匹配')
    version=(ROOT/'VERSION').read_text().strip()
    if ('v'+version) not in (ROOT/'SKILL.md').read_text():errors.append('入口版本不匹配')
    if "'skillVersion':'"+version+"'" not in (ROOT/'scripts/build_prototype.py').read_text():errors.append('元数据版本不匹配')
    m=json.loads((ROOT/'assets/frames/manifest.json').read_text())
    if m['schemaVersion']!=2:errors.append('Manifest 版本错误')
    for f in m['frames']:
        text=(ROOT/'assets/frames'/f['file']).read_text()
        if '{{CONTENT}}' not in text or '<iframe' in text or 'postMessage' in text:errors.append('框架契约错误 '+f['id'])
    for p in (ROOT/'scripts').glob('*.py'):ast.parse(p.read_text())
    for p in [ROOT/'SKILL.md',*(ROOT/'docs').glob('*.md')]:
        text=p.read_text()
        for name in re.findall(r'(?:docs/)?(?:function-[\w-]+|shared-[\w-]+|prototype-types|prototype-validation|workbench-request|workbench-maintenance)\.md',text):
            if not (ROOT/'docs'/Path(name).name).is_file():errors.append(f'{p.name} 悬空引用 {name}')
    for name in ['assets/workbench/app.js','assets/workbench/index.html','scripts/prototype_workbench.py']:
        if 'sync-pages' in (ROOT/name).read_text():errors.append('残留同步实现 '+name)
    ev=json.loads((ROOT/'evals/evals.json').read_text())
    if ev.get('version')!=version:errors.append('评估版本不匹配')
    if len(ev['evals'])<20:errors.append('行为场景覆盖不足')
    for name in ['docs/function-3-prototype-production.md','docs/function-5-workbench.md','docs/shared-workbench-protocol.md']:
        text=(ROOT/name).read_text()
        if 'prototype-validation.md' not in text:errors.append('缺少修改结束规则引用 '+name)
        if '修改后运行 prototype_guard.py' in text or '重新运行同一守卫' in text:errors.append('残留无条件修改验收 '+name)
    for error in errors:print('[FAIL]',error)
    if not errors:print('[OK] v4 文档／代码／框架一致性检查')
    return bool(errors)
if __name__=='__main__':sys.exit(main())
