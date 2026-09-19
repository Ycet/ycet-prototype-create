"""v4.1：无框架生成、修改免验收及写入保护。仅 Skill 开发时运行。"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from build_prototype import build, render
from prototype_document import BuildError
from prototype_guard import audit
from test_prototype_v4 import fixture


def sample(port='web'):
    model = fixture('nonframe')
    model['productPort'] = port
    model['pages'][0]['html'] += '<div style="height:1800px">长内容</div><button data-ycet-element-id="last">末端操作</button>'
    model['pages'].append({'id': 'app', 'label': '应用布局', 'layout': 'app',
                          'html': '<header>产品工具栏</header><main data-ycet-scroll><div style="height:2000px">内容</div><button data-ycet-element-id="app-last">面板末端</button></main><footer>产品底栏</footer>'})
    import base64
    svg='<svg xmlns="http://www.w3.org/2000/svg" width="400" height="1200"><rect width="400" height="1200" fill="#dbeafe"/></svg>'
    data='data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()
    model['pages'].append({'id':'image','label':'图片','imagePrototype':True,
        'html':'<div style="position:relative"><img alt="完整长图" src="'+data+'"><button class="ycet-image-hotspot" style="left:10%;top:90%;width:70%;height:8%" aria-label="图片返回" data-ycet-nav-target="home"></button></div>'})
    model['pages'] += [{'id': f'extra-{i}', 'label': f'页面 {i}', 'html': '<p>短页面</p>'} for i in range(30)]
    return model


class NonframeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_ports_and_no_template_dependency(self):
        original = Path.read_text
        def read(path, *args, **kwargs):
            if path.parent.name == 'frames' and path.suffix == '.html':
                raise AssertionError('无框架不得读取设备模板')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', read):
            for port in ('ios', 'iphone', 'android', 'h5', 'mobile-h5', 'wechat-mini-program', 'ipad', 'web', 'desktop-app', 'windows', 'macos'):
                source = render(sample(port), self.root)
                self.assertEqual(audit(source), [])
                self.assertIn('"frame":null', source)
                self.assertNotIn('--logical-w', source)
                self.assertNotIn('ycet-fit', source)
                self.assertNotIn('data-ycet-zoom', source)

    def test_workbench_recognizes_new_old_and_arbitrary_names(self):
        import prototype_workbench
        root=self.root/'prototype'; root.mkdir()
        source=render(sample(), root)
        (root/'任意名称.html').write_text(source)
        (root/'prototype-mobile.html').write_text(source.replace('"type":"nonframe"', '"type":"mobile"'))
        (root/'普通.html').write_text('<p>普通</p>')
        records=prototype_workbench.Workspace(self.root).public()['files']
        self.assertEqual({r['name']:r['kind'] for r in records}, {'任意名称.html':'nonframe','prototype-mobile.html':'mobile','普通.html':'html'})

    def test_invalid_inputs(self):
        for value in ('', 'unknown'):
            with self.assertRaises(BuildError): render(sample(value), self.root)
        model = sample(); model['type'] = 'unknown'
        with self.assertRaises(BuildError): render(model, self.root)
        model = sample(); model['pages'][0]['layout'] = 'unknown'
        with self.assertRaises(BuildError): render(model, self.root)

    def test_legacy_alias_and_independent_versions(self):
        (self.root/'outputs').mkdir()
        (self.root/'outputs/prototype-mobile-v9.html').write_text('历史')
        model = sample('ios'); model['type'] = 'mobile'
        with self.assertWarns(UserWarning): output = build(model, self.root)
        self.assertEqual(output.name, 'prototype-nonframe.html')
        self.assertEqual(build(sample(), self.root, 'iterate').name, 'prototype-nonframe-v2.html')
        self.assertEqual((self.root/'outputs/prototype-mobile-v9.html').read_text(), '历史')

    def test_initial_audit_and_modify_skip(self):
        # mock 仅捕获真正的 audit 调用，防止文档说免验收但内部仍调用。
        with patch('prototype_guard.audit', return_value=[]) as checker:
            first = build(sample(), self.root)
            self.assertEqual(checker.call_count, 1)
            digest = hashlib.sha256(first.read_bytes()).hexdigest()
            build(sample(), self.root, 'overwrite', first.name, digest)
            build(sample(), self.root, 'iterate')
            self.assertEqual(checker.call_count, 1)
            build(sample(), self.root, 'iterate', validate=True)
            self.assertEqual(checker.call_count, 2)
        with tempfile.TemporaryDirectory() as directory, patch('prototype_guard.audit') as checker:
            build(sample(), Path(directory), purpose='modify')
            checker.assert_not_called()

    def test_modify_keeps_write_protection(self):
        output = build(sample(), self.root)
        before = output.read_bytes()
        with self.assertRaises(BuildError): build(sample(), self.root, 'overwrite', output.name, 'stale')
        self.assertEqual(before, output.read_bytes())
        model = sample(); model['pages'][0]['html'] = '<img src="../outside.png">'
        with self.assertRaises(BuildError): build(model, self.root, 'iterate')

    def test_legacy_html_and_new_metadata_guard(self):
        source = render(sample(), self.root)
        self.assertTrue(audit(source.replace('"productPort":"web"', '"productPort":"unknown"')))
        self.assertEqual(audit(source.replace('"type":"nonframe"', '"type":"mobile"')), [])


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == '--fixtures':
        root = Path(sys.argv[2])
        for port in ('ios', 'web', 'desktop-app'):
            print(build(sample(port), root/port/'prototype'))
    else:
        unittest.main()
