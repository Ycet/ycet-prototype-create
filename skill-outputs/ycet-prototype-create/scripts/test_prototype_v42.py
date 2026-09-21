"""v4.2 正确性与轻量扫描回归，全部使用临时目录。"""
import argparse
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from build_prototype import build
from prototype_document import BuildError, assign_element_ids
from prototype_guard import audit
from prototype_syntax import script_problem
import prototype_workbench as workbench


class SyntaxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def render_page(self, **page):
        return build({'type':'nonframe','productPort':'web','pages':[dict(id='home', **page)]}, self.root).read_text()
    def test_function_and_attribute_selector_commas(self):
        source = self.render_page(html='<button>按钮</button>', css=':scope :is(button, a), :scope [title="a,b"] {color:red} @media (min-width:1px) {:scope :not(.off, .disabled) {color:blue}}')
        self.assertIn(':is(button, a)', source)
    def test_unscoped_selector_still_rejected(self):
        with self.assertRaises(BuildError):
            self.render_page(html='<p>页面</p>',css=':scope :is(button, a), body {color:red}')
    def test_prose_comments_regex_and_template_prose_allowed(self):
        self.render_page(html='<p>页面</p>',js='// fetch("https://example.com")\nconst prose="fetch document window.open"; const pattern=/fetch\\(document/; root.textContent=`fetch ${1 + 2} window`;')
    def test_network_and_template_interpolation_still_rejected(self):
        for source in ['fetch("/api")', 'window.open("x")', 'new XMLHttpRequest()', '`text ${fetch("/api")}`', '`text ${`nested ${fetch("/api")}`}`']:
            with self.subTest(source=source):
                self.assertIsNotNone(script_problem(source, page=True))
    def test_dynamic_nesting_still_rejected(self):
        self.assertIsNotNone(script_problem('document.createElement("iframe")'))
        self.assertIsNone(script_problem('const tip="document.createElement(\\"iframe\\")";'))
    def test_generated_element_ids_avoid_existing_ids(self):
        source = self.render_page(html='<button data-ycet-element-id="home-el-1">甲</button><button>乙</button>')
        self.assertEqual(1, source.count('data-ycet-element-id="home-el-1"'))
        self.assertIn('data-ycet-element-id="home-el-2"',source)
    def test_explicit_duplicate_element_ids_rejected(self):
        with self.assertRaises(BuildError):
            self.render_page(html='<p data-ycet-element-id="same">甲</p><p data-ycet-element-id="same">乙</p>')
    def test_ids_parser_handles_greater_than_and_comments(self):
        source=assign_element_ids('<!-- <p> -->\n<button title="a > b">按钮</button>', 'home')
        self.assertIn('title="a > b"',source)
        self.assertEqual(1,source.count('data-ycet-element-id='))
    def test_guard_rejects_manually_introduced_duplicate_ids(self):
        source=self.render_page(html='<p>甲</p><p>乙</p>')
        self.assertIn('页面内元素 ID 缺失或重复',audit(source.replace('home-el-2','home-el-1')))
    def test_inline_global_event_rejected_but_local_event_kept(self):
        with self.assertRaises(BuildError):
            self.render_page(html='<button onclick="document.body.remove()">按钮</button>')
        self.render_page(html='<button onclick="this.textContent=\'fetch\'">按钮</button>')
    def test_mail_and_phone_links_consistent(self):
        source=self.render_page(html='<a href="mailto:a@example.com">邮件</a><a href="tel:12345">电话</a>')
        self.assertEqual([],audit(source))


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        (self.root/'prototype').mkdir()
        self.first=self.root/'prototype/a.html';self.first.write_text('<p>A</p>')
        self.second=self.root/'prototype/b.html';self.second.write_text('<p>B</p>')
        self.workspace=workbench.Workspace(self.root)
    def tearDown(self):
        self.temp.cleanup()
    def test_unchanged_scan_does_not_read_html_bytes(self):
        original=Path.read_bytes
        reads=[]
        def read(path):
            if path.suffix=='.html':reads.append(path)
            return original(path)
        with patch.object(Path,'read_bytes',read):
            self.workspace.scan()
            self.assertEqual([],reads)
            self.first.write_text('<p>changed</p>')
            self.workspace.scan()
            self.assertEqual([self.first.resolve()],reads)
    def test_same_size_edit_with_restored_mtime_detected(self):
        before=self.first.stat()
        old=self.workspace.data['files'][0]['sha256']
        self.first.write_text('<p>Z</p>')
        os.utime(self.first,ns=(before.st_atime_ns,before.st_mtime_ns))
        self.workspace.scan()
        self.assertNotEqual(old,self.workspace.data['files'][0]['sha256'])
    def test_send_rechecks_digest_even_with_cached_metadata(self):
        record=self.workspace.data['files'][0]
        self.first.write_text('<p>external change</p>')
        with self.assertRaises(workbench.WorkbenchError):
            workbench.validate_request(self.workspace,{'files':[{'fileId':record['id'],'sha256':record['sha256'],'operations':[{'type':'annotation','text':'修改'}]}]})
    def begin(self):
        package=workbench.validate_request(self.workspace,{'files':[{'fileId':record['id'],'sha256':record['sha256'],'operations':[{'type':'annotation','text':'修改'}]} for record in self.workspace.data['files']]})
        workbench.atomic_json(workbench.request_path(self.root,package['requestId']),package)
        self.package=package
        self.command('begin')
    def command(self, action, result=None):
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(argparse.Namespace(project_root=str(self.root),request_id=self.package['requestId'],request_action=action,result=result,reason=''))
    def complete(self, items):
        path=self.root/'result.json';path.write_text(json.dumps({'items':items}))
        self.command('complete',str(path))
    def test_missing_result_rejected_and_corrected_result_can_complete(self):
        self.begin()
        first,second=self.package['files']
        Path(first['path']).write_text('<p>已修改</p>')
        success={'fileId':first['fileId'],'status':'success'}
        with self.assertRaises(workbench.WorkbenchError):self.complete([success])
        self.assertEqual('processing',workbench.load_request_state(self.root,self.package['requestId'])['status'])
        self.complete([success,{'fileId':second['fileId'],'status':'failed','reason':'无法定位'}])
        self.assertEqual('partial',workbench.load_request_state(self.root,self.package['requestId'])['status'])
    def test_duplicate_unknown_and_invalid_results_rejected(self):
        self.begin()
        first,second=self.package['files']
        for items in [
            [{'fileId':first['fileId'],'status':'success'}]*2,
            [{'fileId':'unknown','status':'failed'},{'fileId':second['fileId'],'status':'failed'}],
            [{'fileId':first['fileId'],'status':'invalid'},{'fileId':second['fileId'],'status':'failed'}],
        ]:
            with self.subTest(items=items),self.assertRaises(workbench.WorkbenchError):self.complete(items)
        self.complete([{'fileId':item['fileId'],'status':'failed'} for item in self.package['files']])


if __name__=='__main__':unittest.main()
