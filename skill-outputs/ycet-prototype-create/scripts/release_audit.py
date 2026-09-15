#!/usr/bin/env python3
"""审计或导出排除过程文件的 Skill 发布包，不删除开发历史。"""
import argparse,sys,zipfile
from pathlib import Path
from validate_skill import main as validate
ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={'test-artifacts','__pycache__','.ycet-editor','.DS_Store'}
def files(root):
    return [p for p in root.rglob('*') if p.is_file() and not any(x in EXCLUDE for x in p.relative_to(root).parts) and p.suffix!='.pyc']
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args()
    if validate():return 1
    selected=files(ROOT)
    if a.output:
        output=a.output.resolve()
        if ROOT==output or ROOT in output.parents:p.error('发布包必须位于 Skill 目录外')
        output.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
            for f in selected:z.write(f,ROOT.name+'/'+f.relative_to(ROOT).as_posix())
        print('[OK] 发布包',output)
    print('[OK] 发布文件数',len(selected),'；过程目录已排除')
    return 0
if __name__=='__main__':sys.exit(main())
