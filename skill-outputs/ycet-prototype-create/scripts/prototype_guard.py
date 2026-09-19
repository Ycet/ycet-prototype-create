#!/usr/bin/env python3
"""校验 v4 独立原型。静态检查不能替代逐页浏览器验证。"""
import argparse,json,re,sys,base64
from html.parser import HTMLParser
from pathlib import Path
class Document(HTMLParser):
    def __init__(self):
        super().__init__();self.errors=[];self.ids=[];self.pages=[];self.targets=[];self.meta='';self.scripts=[];self.styles=[];self.mode=None;self.kind=''
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('iframe','object','embed','base') or 'srcdoc' in a:self.errors.append('禁止页面嵌套或 base')
        if 'id' in a:self.ids.append(a['id'])
        if 'data-ycet-page-id' in a:self.pages.append(a['data-ycet-page-id'])
        if 'data-ycet-nav-target' in a:self.targets.append(a['data-ycet-nav-target'].split('?')[0].split('#')[0])
        if tag=='meta' and a.get('http-equiv','').lower()=='refresh':self.errors.append('禁止重定向')
        for k,v in attrs:
            v=(v or '').strip()
            if k in ('src','poster','data') or k in ('href','xlink:href') and tag!='a':
                if not v.startswith(('data:','#')):self.errors.append('资源未内联：'+v[:80])
            if k=='href' and tag=='a' and v and not v.startswith('#'):self.errors.append('跨文件链接')
            if k in ('action','formaction') and v and not v.startswith('#'):self.errors.append('外部表单提交')
            if k=='srcset' and (not v.startswith('data:') or re.search(r'(?:https?:|file:|\.\./)',v)):self.errors.append('srcset 未完全内联')
            if v.startswith('data:image/svg+xml;base64,'):
                try:
                    nested=Document();nested.feed(base64.b64decode(v.split(',',1)[1].split('#')[0]).decode());self.errors.extend(nested.errors)
                    self.styles.extend(nested.styles);self.scripts.extend(nested.scripts)
                except (ValueError,UnicodeError):self.errors.append('SVG 数据无效')
            if k=='style':self.styles.append(v)
            if k.startswith('on'):self.scripts.append(v)
        if tag=='script':self.mode='meta' if a.get('id')=='ycet-metadata' else 'script' if a.get('type') not in ('application/json','application/ld+json') else None
        if tag=='style':self.mode='style'
    handle_startendtag=handle_starttag
    def handle_data(self,data):
        if self.mode=='meta':self.meta+=data
        if self.mode=='script':self.scripts.append(data)
        if self.mode=='style':self.styles.append(data)
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.mode=None

def audit(source):
    d=Document();d.feed(source)
    if len(set(d.ids))!=len(d.ids):d.errors.append('重复 DOM ID')
    if not d.pages or len(set(d.pages))!=len(d.pages):d.errors.append('页面 ID 缺失或重复')
    try:
        m=json.loads(d.meta)
        if m.get('schemaVersion')!=1 or m.get('type') not in ('pages','demo','nonframe','mobile','direction'):raise ValueError()
        if m.get('type')=='nonframe':
            routing=json.loads((Path(__file__).resolve().parents[1]/'assets/frames/manifest.json').read_text())['routing']
            if m.get('frame') is not None or m.get('productPort') not in routing: raise ValueError()
            if any(p.get('layout','document') not in ('document','app') for p in m['pages']): raise ValueError()
        if [p['id'] for p in m['pages']]!=d.pages or m['initial'] not in d.pages:raise ValueError()
    except (ValueError,KeyError,TypeError):d.errors.append('原型元数据无效');m={}
    if any(t not in d.pages for t in d.targets):d.errors.append('未登记页面目标')
    for css in d.styles:
        if re.search(r'@import\b',css):d.errors.append('CSS import 未内联')
        for match in re.finditer(r'url\(\s*[\'"]?([^\)]+)',css):
            if not match[1].startswith(('data:','#')):d.errors.append('CSS 资源未内联')
    for script in d.scripts:
        if re.search(r'\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|importScripts)\b|\bimport\s*\(|\.srcdoc\b|createElement\s*\(\s*[\'"](?:iframe|object|embed)[\'"]|location\.(?:href|assign|replace)|window\.open|sendBeacon',script):d.errors.append('脚本包含外部请求或页面嵌套／离开文档行为')
    return list(dict.fromkeys(d.errors))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('file',type=Path);a=p.parse_args();errors=audit(a.file.read_text())
    for e in errors:print('[FAIL]',e)
    if not errors:print('[OK] 单文件结构与依赖静态校验通过；浏览器结果需另行记录')
    return bool(errors)
if __name__=='__main__':sys.exit(main())
