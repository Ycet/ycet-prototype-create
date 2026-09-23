"""展示壳主题与旧输入兼容回归；--fixtures 生成离线浏览器样本。"""
import argparse, tempfile, unittest
from pathlib import Path
from build_prototype import build, render
from prototype_document import BuildError
from prototype_guard import audit
from test_prototype_v4 import fixture

THEMES = {
    'light': dict(background='#edf4f2',surface='#ffffff',text='#183a35',muted='#526d67',border='#c5d8d2',accent='#147d64',onAccent='#ffffff',activeBackground='#d7efe5',activeText='#145a47',fontFamily='Georgia, serif',radius='12px',shadow='0px 4px 18px #c5d8d2',colorScheme='light'),
    'dark': dict(background='#151a26',surface='#20283a',text='#eef0ff',muted='#b3bcd6',border='#414b67',accent='#b4a2ff',onAccent='#201942',activeBackground='#443568',activeText='#f1eaff',fontFamily='system-ui, sans-serif',radius='4px',shadow='none',colorScheme='dark'),
}

def themed(kind, name):
    model=fixture(kind);theme=THEMES[name];model['shellTheme']=theme;model['title']='灵感笔记 · '+name
    if kind=='direction':
        model['pages']=model['pages'][:1];model['pages'][0]['html']='<h1>灵感笔记</h1><p>留住每一次好想法。</p>';model['pages'][0]['js']=''
        model['directionHtml']='<h1>灵感笔记 · 设计方向</h1><p>清晰的层级、舒适的阅读与随手记录；外围导航沿用产品的视觉语言。</p>'
    for page in model['pages']:
        page['css']=f':scope {{background:{theme["surface"]};color:{theme["text"]};font-family:{theme["fontFamily"]};padding:48px 24px}} :scope button {{background:{theme["accent"]};color:{theme["onAccent"]};border:0;border-radius:{theme["radius"]};padding:12px;margin:8px 0}} :scope input {{max-width:100%}}'
    return model

class ShellTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_all_types_and_themes(self):
        for kind in ('pages','demo','direction','nonframe'):
            for name in THEMES:
                document=render(themed(kind,name),self.root)
                self.assertEqual(audit(document),[])
                self.assertIn('--ycet-shell-accent:'+THEMES[name]['accent'],document)
    def test_legacy_opt_out(self):
        for kind in ('pages','demo','nonframe'):
            self.assertNotIn('--ycet-shell-',render(fixture(kind),self.root))
    def test_product_and_runtime_unchanged(self):
        # 使用输出片段比较，主题不重写产品 CSS、页面标识或脚本。
        import re
        model=fixture();old=render(model,self.root);model['shellTheme']=THEMES['dark'];new=render(model,self.root)
        for pattern in [r'<section class="ycet-page".*?</section>',r'<script>(.*?)</script>']:
            self.assertEqual(re.findall(pattern,old,re.S),re.findall(pattern,new,re.S))
        self.assertIn('[data-ycet-page-id="home"] button {color:#2563eb}',new)
    def test_injection_and_invalid_values_rejected(self):
        for key,value in [('accent','#fff;display:none'),('fontFamily','x</style><script>x'),('shadow','url(https://example.com/x)'),('radius','-2px'),('colorScheme','auto'),('surface',None),('unknown','x')]:
            model=themed('demo','dark');model['shellTheme']=dict(model['shellTheme'],**{key:value})
            with self.subTest(key=key),self.assertRaises(BuildError):render(model,self.root)
    def test_incomplete_theme_rejected(self):
        for value in [{},'dark',{'accent':'#123456'}]:
            model=fixture();model['shellTheme']=value
            with self.assertRaises(BuildError):render(model,self.root)
    def test_derived_defaults_do_not_reintroduce_blue(self):
        from shell_theme import shell_theme,REQUIRED
        theme,_=shell_theme({k:v for k,v in THEMES['dark'].items() if k in REQUIRED})
        self.assertEqual(theme['activeBackground'],theme['accent']);self.assertEqual(theme['activeText'],theme['onAccent'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fixtures',type=Path);args=parser.parse_args()
    if args.fixtures:
        for name in THEMES:
            for kind in ('pages','demo','direction','nonframe'):build(themed(kind,name),args.fixtures/name/'prototype')
        print(args.fixtures.resolve())
    else:unittest.main(argv=['test_shell_theme_v423.py'])
