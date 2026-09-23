"""展板、排版与局部交互契约回归；同时生成可查看的两套设计样本。"""
import argparse, copy, tempfile, unittest
from pathlib import Path
from build_prototype import render, build
from prototype_document import BuildError
from prototype_guard import audit
from test_shell_theme_v423 import THEMES


def fixture(kind='direction', style='journal'):
    theme = dict(THEMES['light' if style=='journal' else 'dark'])
    journal=style=='journal'
    theme.update(dict(background='#faf7ed',surface='#fffdf6',text='#302a25',muted='#7b7569',border='#e6decc',accent='#92400e',onAccent='#ffffff',activeBackground='#92400e',activeText='#ffffff',fontFamily='Georgia, "Songti SC", serif',headingFontFamily='Georgia, "Songti SC", serif',radius='12px',shadow='0px 3px 0px #e6decc66',lineStyle='dashed',motion='180ms') if journal else dict(radius='6px',headingWeight='700',motion='100ms'))
    title='拾光手记' if journal else 'Orbit · 工作记录'
    summary='把生活里的小事，慢慢记下来。' if journal else '记录进展与决定，让下一步更清晰。'
    css='''
:scope{background:VAR_SURFACE;color:VAR_TEXT;font-family:VAR_FONT;padding:72px 24px 32px}
:scope header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid VAR_BORDER;padding-bottom:18px}
:scope header b{font-size:18px;color:VAR_ACCENT}:scope small{font-size:11px;color:VAR_MUTED}
:scope h1{font-size:28px;line-height:1.4;margin:28px 0 10px}:scope p{font-size:13px;line-height:1.8;color:VAR_MUTED}
:scope .entry{background:VAR_BG;border:1px solid VAR_BORDER;border-radius:VAR_RADIUS;padding:18px;margin:20px 0}
:scope .entry h2{font-size:18px;margin:10px 0}:scope .entry p{margin-bottom:0}
:scope button{font:inherit;padding:12px 18px;border:0;border-radius:VAR_RADIUS;background:VAR_ACCENT;color:VAR_ON;cursor:pointer}
:scope .foot{display:flex;justify-content:space-between;border-top:1px solid VAR_BORDER;margin-top:28px;padding-top:18px;font-size:12px;color:VAR_ACCENT}
'''
    for key,value in {'VAR_SURFACE':theme['surface'],'VAR_TEXT':theme['text'],'VAR_FONT':theme['fontFamily'],'VAR_BORDER':theme['border'],'VAR_ACCENT':theme['accent'],'VAR_MUTED':theme['muted'],'VAR_BG':theme['background'],'VAR_RADIUS':theme['radius'],'VAR_ON':theme['onAccent']}.items():css=css.replace(key,value)
    content=f'<header><b>{title}</b><small>9 月 23 日 · 周三</small></header><h1>今天，有什么值得记下？</h1><p>{summary}</p><button type="button" data-record>写一条记录</button><article class="entry"><small>生活片段 · 08:40</small><h2>给自己一点慢下来的时间</h2><p>早晨经过熟悉的街角，买了一杯热咖啡。今天想把注意力留给真正重要的事。</p></article><article class="entry"><small>小小进展 · 昨天</small><h2>把想法变成第一步</h2><p>整理了这一周的记录，也终于开始了搁置很久的计划。</p></article><p data-count role="status">已记录 12 天</p><div class="foot"><span>全部记录</span><span>回顾</span><span>我的</span></div>'
    page={'id':'home','label':'全部记录','description':'浏览最近的生活片段','group':'日常记录','html':content,'css':css,'js':"root.querySelector('[data-record]').addEventListener('click',()=>root.querySelector('[data-count]').textContent='新记录已创建');"}
    model={'type':kind,'productPort':'ios','title':title,'shellTheme':theme,'presentation':{'summary':summary,'density':'comfortable' if journal else 'compact'},'pages':[page]}
    if kind!='direction':
        model['pages'] += [dict(page,id='detail',label='记录详情',description='阅读与整理一条记录'),dict(page,id='settings',label='阅读偏好',description='设置自己的阅读节奏',group='偏好')]
    if kind=='direction':
        model['direction']={'titleSample':'给平凡的一天，留一点位置。','bodySample':summary,'components':[
            {'title':'记录与保存','description':'主按钮承载主要操作，保存后反馈就地出现。','html':'<button type="button" data-save data-variant="primary">保存记录</button><button type="button" disabled>保存中…</button><span data-result role="status">尚未保存</span>'},
            {'title':'阅读偏好','description':'展开查看选项；原生控件保留键盘操作。','html':'<details><summary>调整阅读方式</summary><label>文字大小 <select><option>标准字号</option><option>大号文字</option></select></label></details>'},
            {'title':'轻量反馈','description':'提示融入内容，保留明确的完成状态。','html':'<div class="sample-note"><b>今天也认真记录了</b><p>连续 12 天，给自己的生活留下一点注脚。</p></div>'},
            {'title':'输入状态','description':'焦点颜色和圆角与产品表单一致。','html':'<label class="sample-field">给今天起个名字<input placeholder="写下一句话…" aria-label="记录标题"></label>'}]}
        model['directionCss']=':scope [data-result]{font-size:12px;color:var(--ycet-shell-accent)} :scope .sample-note{width:100%;padding:18px;background:var(--ycet-shell-background);border-left:3px solid var(--ycet-shell-accent);border-radius:var(--ycet-shell-radius)} :scope .sample-note p{font-size:13px;line-height:1.7;margin:8px 0 0} :scope .sample-field{display:grid;gap:10px;width:100%;font-size:12px}'
        model['directionJs']="root.querySelector('[data-save]').addEventListener('click',()=>{root.querySelector('[data-result]').textContent='已保存';});"
    return model


class PresentationTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_visual_board_and_offline(self):
        for style in ('journal','studio'):
            document=render(fixture(style=style),self.root)
            self.assertEqual([],audit(document));self.assertEqual(document.count('<article class="ycet-swatch">'),6);self.assertEqual(document.count('<article class="ycet-specimen">'),4)
            self.assertIn('.ycet-direction-summary .sample-note',document)
    def test_all_shell_types(self):
        for kind in ('pages','demo','nonframe'):
            document=render(fixture(kind),self.root);self.assertEqual([],audit(document))
            if kind=='nonframe':self.assertNotIn('class="ycet-shell-heading"',document)
            else:self.assertIn('class="ycet-shell-heading"',document)
    def test_source_model_unchanged(self):
        model=fixture();before=copy.deepcopy(model);render(model,self.root);self.assertEqual(model,before)
    def test_global_extensions_rejected(self):
        for key,value in [('directionCss','h1{color:red}'),('directionCss',':scope p,body{color:red}'),('directionJs','window.location.reload()')]:
            model=fixture();model[key]=value
            with self.assertRaises(BuildError):render(model,self.root)
    def test_remote_assets_and_bad_fragment_rejected(self):
        for fragment in ['<style>body{color:red}</style>','<img src="https://example.com/x.png">']:
            model=fixture();model['direction']['components'][0]['html']=fragment
            with self.assertRaises(BuildError):render(model,self.root)
    def test_partial_theme_and_bad_options(self):
        for key,value in [('motion','999ms'),('lineStyle','double'),('headingWeight','heavy')]:
            model=fixture();model['shellTheme'][key]=value
            with self.assertRaises(BuildError):render(model,self.root)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fixtures',type=Path);args=parser.parse_args()
    if args.fixtures:
        for style in ('journal','studio'):
            for kind in ('direction','pages','demo','nonframe'):build(fixture(kind,style),args.fixtures/style/'prototype')
        print(args.fixtures.resolve())
    else:unittest.main(argv=['test_presentation_v424.py'])
