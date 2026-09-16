"""v4 生成、保护与离线结构回归。"""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from build_prototype import build,render,ROOT
from prototype_guard import audit
from prototype_document import BuildError

def fixture(kind='demo'):
    return {'type':kind,'pages':[{'id':'home','label':'首页','html':'<button data-ycet-nav-target="detail">详情</button><input aria-label="姓名"><button data-ycet-element-id="count">计数</button>','css':':scope {background:#fff} :scope button {color:#2563eb}','js':'let count=0;root.querySelector("[data-ycet-element-id=count]").addEventListener("click",e=>e.target.textContent=String(++count));'},{'id':'detail','label':'详情','html':'<h1>详情</h1><button data-ycet-back>返回</button><button data-ycet-element-id="count">另一页按钮</button>'}]}

class BuildTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'prototype';self.root.mkdir()
    def tearDown(self):self.temp.cleanup()
    def test_all_types_offline(self):
        for k in ('pages','demo','mobile','direction'):
            m=fixture(k)
            if k=='direction':m['pages']=m['pages'][:1];m['pages'][0]['html']='<h1>首页</h1>';m['pages'][0]['js']=''
            p=build(m,self.root);self.assertEqual([],audit(p.read_text()));self.assertNotIn('<iframe',p.read_text());self.assertEqual(p.parent,(self.root/'outputs').resolve())
        self.assertEqual({'outputs'},set(p.name for p in self.root.iterdir()))
    def test_independent_versions(self):
        self.assertEqual(build(fixture(),self.root).name,'prototype-demo.html')
        self.assertEqual(build(fixture(),self.root,'iterate').name,'prototype-demo-v2.html')
        self.assertEqual(build(fixture('mobile'),self.root).name,'prototype-mobile.html')
    def test_create_does_not_overwrite(self):
        build(fixture(),self.root)
        with self.assertRaises(BuildError):build(fixture(),self.root)
    def test_overwrite_requires_digest(self):
        p=build(fixture(),self.root);before=p.read_bytes()
        with self.assertRaises(BuildError):build(fixture(),self.root,'overwrite',p.name,'wrong')
        self.assertEqual(before,p.read_bytes())
        m=fixture();m['title']='更新';build(m,self.root,'overwrite',p.name,hashlib.sha256(before).hexdigest());self.assertIn('更新',p.read_text())
    def test_unrelated_and_log_unchanged(self):
        log=self.root/'EditLog.md';log.write_text('历史');build(fixture(),self.root);self.assertEqual('历史',log.read_text())
    def test_bad_sources_blocked(self):
        for content in ['<iframe></iframe>','<img src="https://example.com/a.png">','<img src="../outside.png">','<script>alert(1)</script>']:
            m=fixture();m['pages'][0]['html']=content
            with self.assertRaises(BuildError):build(m,self.root)
        self.assertFalse(list(((self.root/'outputs').resolve()).glob('*.html')))
    def test_target_guard(self):
        m=fixture();m['pages'][0]['html']='<button data-ycet-nav-target="missing">走</button>'
        with self.assertRaises(BuildError):build(m,self.root)
    def test_duplicate_ids(self):
        m=fixture();m['pages'][0]['html']='<p id="same">A</p>';m['pages'][1]['html']='<p id="same">B</p>'
        with self.assertRaises(BuildError):build(m,self.root)
    def test_all_frames(self):
        for f in json.loads((ROOT/'assets/frames/manifest.json').read_text())['frames']:
            m=fixture();m['frameId']=f['id'];self.assertEqual([],audit(render(m,self.root)))
    def test_embed_asset_and_svg_namespace(self):
        assets=self.root/'assets';assets.mkdir();(assets/'test.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle r="3"/></svg>')
        m=fixture();m['pages'][0]['html']='<img src="assets/test.svg">';m['pages'][0]['js']='';p=build(m,self.root);self.assertIn('data:image/svg+xml;base64,',p.read_text());self.assertTrue((assets/'test.svg').exists())
    def test_global_css_rejected(self):
        m=fixture();m['pages'][0]['css']=':scope {color:red} button {font-size:30px}'
        with self.assertRaises(BuildError):build(m,self.root)
    def test_embedded_svg_remote_rejected(self):
        import base64
        svg='<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/a.png"/></svg>'
        m=fixture();m['pages'][0]['html']='<img src="data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()+'">';m['pages'][0]['js']=''
        with self.assertRaises(BuildError):build(m,self.root)
    def test_version_gap_and_metadata(self):
        p=build(fixture(),self.root);p.rename(p.with_name('prototype-demo-v8.html'))
        new=build(fixture(),self.root,'iterate');self.assertEqual(new.name,'prototype-demo-v9.html');self.assertIn('"artifactVersion":9',new.read_text())
    def test_new_file_collision_preserves_other_writer(self):
        import os
        from unittest.mock import patch
        original=os.link
        def race(source,dest):
            Path(dest).write_text('concurrent')
            return original(source,dest)
        with patch('build_prototype.os.link',race),self.assertRaises(FileExistsError):build(fixture(),self.root)
        self.assertEqual((self.root/'outputs/prototype-demo.html').read_text(),'concurrent')
        self.assertFalse(list((self.root/'outputs').glob('*.tmp')))

if __name__=='__main__':
    import sys
    if len(sys.argv)==3 and sys.argv[1]=='--fixtures':
        root=Path(sys.argv[2]).resolve()/'prototype';root.mkdir(parents=True,exist_ok=True)
        for kind in ('pages','demo','mobile','direction'):
            model=fixture(kind)
            if kind=='demo':
                model['pages'][0]['html']+='<div style="height:1800px">长页面底部可滚动</div>'
                model['pages'] += [{'id':f'extra-{i}','label':f'更多页面 {i}','html':'<p>页面</p>'} for i in range(40)]
            if kind=='direction':
                model['pages']=model['pages'][:1];model['pages'][0]['html']='<h1>首页预览</h1>';model['pages'][0]['js']=''
            print(build(model,root))
    else:unittest.main()
