#!/usr/bin/env python3
"""从已确认的页面片段生成独立 HTML；不推断需求或代替用户确认。"""
from __future__ import annotations
import argparse, hashlib, html, json, os, re, tempfile, warnings
from pathlib import Path
from prototype_document import BuildError, ResourceBundler, safe_json_script, assign_element_ids
from shell_theme import shell_theme
from prototype_syntax import script_problem
from presentation import heading, navigation, direction, scoped_css

ROOT = Path(__file__).resolve().parents[1]
NAMES = {'pages':'prototype-pages','demo':'prototype-demo','nonframe':'prototype-nonframe','direction':'design-direction'}

def normalize_model(model):
    model = dict(model)
    if model.get('type') == 'mobile':
        warnings.warn('旧 mobile 输入已转为 nonframe，输出 prototype-nonframe 文件族', UserWarning)
        model['type'] = 'nonframe'
    if model.get('type') not in NAMES: raise BuildError('未知原型类型')
    return model

def output_path(root, kind, mode, target=None):
    directory = root/'outputs'; stem=NAMES[kind]
    matches=[(int(m[1] or 1),p) for p in directory.glob('*.html') if (m:=re.fullmatch(re.escape(stem)+r'(?:-v([2-9]\d*|1\d+))?\.html',p.name))]
    if mode=='overwrite':
        if not target: raise BuildError('覆盖必须指定现有 --target')
        p=(directory/target).resolve()
        if p.parent!=directory.resolve() or not p.is_file() or not any(p==q.resolve() for _,q in matches): raise BuildError('目标必须是 outputs 中对应类型的现有文件')
        return p
    if mode=='create' and matches: raise BuildError('该类型已存在；明确选择修改或迭代策略')
    n=max((v for v,_ in matches),default=0)+1
    return directory/(stem+('' if n==1 else f'-v{n}')+'.html')

STYLE='''
*{box-sizing:border-box}html,body{margin:0;width:100%;min-height:100%;font-family:system-ui,sans-serif;background:#f3f4f6;color:#171719}html,body,[data-ycet-scroll]{scrollbar-width:none}::-webkit-scrollbar{width:0;height:0;display:none}button{cursor:pointer;font:inherit}button:focus-visible,a:focus-visible{outline:2px solid #2563eb} [hidden]{display:none!important}
.ycet-page{position:relative;width:var(--logical-w);height:var(--logical-h);overflow:hidden;background:white;contain:layout paint}.ycet-page [data-ycet-scroll]{overflow:auto;max-height:100%}.ycet-page{padding:var(--safe-top) 0 var(--safe-bottom)}
.ycet-grid{display:grid;grid-template-columns:repeat(var(--columns),max-content);gap:32px;padding:32px;width:max-content;min-width:100%}.ycet-card{margin:0}.ycet-card h2{font-size:16px}.ycet-layout{height:100vh;height:100dvh;display:grid;grid-template-columns:clamp(220px,18vw,296px) minmax(0,1fr);overflow:hidden}.ycet-nav{min-height:0;min-width:0;padding:16px;overflow:auto;overscroll-behavior:contain}.ycet-nav button{display:block;width:100%;border:0;padding:12px;text-align:left;background:transparent}.ycet-nav button[aria-current=page]{background:#dbeafe;color:#1d4ed8}.ycet-viewer{min-width:0;min-height:0;display:grid;grid-template-rows:auto minmax(0,1fr)}.ycet-toolbar{display:flex;justify-content:flex-end;align-items:center;gap:8px;padding:8px 16px;background:white;flex-wrap:wrap}.ycet-toolbar button{min-height:36px;border:1px solid #cbd5e1;border-radius:6px;background:white;padding:4px 12px}.ycet-stage{min-width:0;min-height:0;overflow:auto;overscroll-behavior:contain}.ycet-stage-inner{min-width:100%;min-height:100%;width:max-content;display:flex;padding:24px}.ycet-fit{position:relative;flex:none;margin:auto;overflow:hidden}.ycet-fit-content{position:absolute;top:0;left:0;transform-origin:top left}.ycet-demo .ycet-page{overflow-y:auto}.ycet-menu{touch-action:none;min-width:44px;min-height:44px;position:fixed;top:max(8px,env(safe-area-inset-top));left:8px;z-index:100;border:0;border-radius:8px;padding:10px;background:#111;color:white}.ycet-drawer{position:fixed;inset:0 auto 0 0;width:min(82vw,320px);background:white;z-index:102;overflow:auto}.ycet-overlay{position:fixed;inset:0;background:#0006;z-index:101;border:0}.ycet-error{position:fixed;bottom:16px;left:16px;z-index:150;background:#991b1b;color:white;padding:12px}.ycet-image-hotspot{position:absolute;background:transparent;border:0;outline:1px dashed transparent;outline-offset:-1px;z-index:10}.ycet-image-hotspot:hover,.ycet-image-hotspot:focus-visible{outline-color:rgba(37,99,235,.72)}
@media(max-width:1000px){.ycet-grid{grid-template-columns:repeat(2,max-content)}}@media(max-width:760px){.ycet-grid{grid-template-columns:max-content}.ycet-layout{grid-template-columns:1fr;grid-template-rows:minmax(0,120px) minmax(0,1fr)}.ycet-layout>.ycet-nav{max-height:120px}}
'''
RUNTIME='''
// 同文档页面注册表，所有业务导航只接受已登记页面。
(()=>{const meta=JSON.parse(document.getElementById('ycet-metadata').textContent);const interactive=['demo','nonframe'].includes(meta.type);const pages=[...document.querySelectorAll('[data-ycet-page-id]')];let current=meta.initial;
const error=document.querySelector('.ycet-error');
const frameless=meta.type==='nonframe';const scrolls=new Map();let shown=false,drawerOpen=false,returnFocus=null,bodyState=null;
if(frameless&&'scrollRestoration' in history)history.scrollRestoration='manual';
function viewport(){const v=window.visualViewport;if(!v||Math.abs(v.scale-1)<.01)document.documentElement.style.setProperty('--ycet-view-height',(v?v.height:innerHeight)+'px');clampMenu();}
if(frameless){window.addEventListener('resize',viewport);window.visualViewport?.addEventListener('resize',viewport);window.visualViewport?.addEventListener('scroll',clampMenu);}

function show(id){if(!meta.pages.some(p=>p.id===id)){error.hidden=false;error.textContent='未知页面：'+id;return false;}if(frameless&&shown&&current!==id)scrolls.set(current,[scrollX,scrollY]);
const changed=current!==id;current=id;pages.forEach(p=>{p.hidden=interactive&&p.dataset.ycetPageId!==id;p.inert=p.hidden;});document.querySelectorAll('[data-ycet-tool-target]').forEach(b=>b.setAttribute('aria-current',b.dataset.ycetToolTarget===id?'page':'false'));error.hidden=true;
if(frameless&&(!shown||changed)){const position=scrolls.get(id)||[0,0];window.scrollTo(...position);}
shown=true;return true;}
function navigate(id){if(!interactive)return;const split=String(id).match(/^([a-z][a-z0-9-]*)([?#].*)?$/);if(!split||!meta.pages.some(p=>p.id===split[1])){error.hidden=false;error.textContent='无效页面目标';return;}const hash='#ycet='+encodeURIComponent(id);if(location.hash!==hash)location.hash=hash;else show(split[1]);}
function fromHash(){let value=meta.initial;try{if(location.hash.startsWith('#ycet='))value=decodeURIComponent(location.hash.slice(6));}catch(e){}const id=value.split(/[?#]/)[0];if(show(id)){const root=pages.find(p=>p.dataset.ycetPageId===id);root.tabIndex=-1;root.focus({preventScroll:true});root.dispatchEvent(new CustomEvent('ycet-enter',{detail:{target:value}}));}}
let dragged=false;
const menu=document.querySelector('.ycet-menu');let drag=null;
function clampMenu(){if(!menu)return;const rect=menu.getBoundingClientRect(),v=window.visualViewport,style=getComputedStyle(document.documentElement);
const safe=name=>parseFloat(style.getPropertyValue('--ycet-safe-'+name))||0;
const x=v?v.offsetLeft:0,y=v?v.offsetTop:0,w=v?v.width:innerWidth,h=v?v.height:innerHeight;
menu.style.left=Math.max(x+safe('left'),Math.min(x+w-rect.width-safe('right'),rect.left))+'px';
menu.style.top=Math.max(y+safe('top'),Math.min(y+h-rect.height-safe('bottom'),rect.top))+'px';}
menu?.addEventListener('pointerdown',e=>{const rect=menu.getBoundingClientRect();drag={x:e.clientX,y:e.clientY,left:rect.left,top:rect.top};dragged=false;menu.setPointerCapture(e.pointerId)});
menu?.addEventListener('pointermove',e=>{if(!drag)return;if(Math.hypot(e.clientX-drag.x,e.clientY-drag.y)>5)dragged=true;if(dragged){menu.style.left=drag.left+e.clientX-drag.x+'px';menu.style.top=drag.top+e.clientY-drag.y+'px';clampMenu();}});
menu?.addEventListener('pointerup',()=>{drag=null});menu?.addEventListener('pointercancel',()=>{drag=null});window.addEventListener('resize',clampMenu);
function drawer(open){
const panel=document.querySelector('.ycet-drawer');if(!panel||open===drawerOpen)return;
drawerOpen=open;
if(open){returnFocus=document.activeElement;bodyState={style:document.body.getAttribute('style'),x:scrollX,y:scrollY};
document.body.style.position='fixed';document.body.style.top=-bodyState.y+'px';document.body.style.left=-bodyState.x+'px';document.body.style.width='100%';}
document.querySelectorAll('.ycet-drawer,.ycet-overlay').forEach(e=>{e.hidden=!open;e.inert=!open});menu?.setAttribute('aria-expanded',String(open));if(menu)menu.inert=open;
pages.forEach(p=>p.inert=open||p.hidden);
if(open)panel.querySelector('[data-ycet-close]')?.focus();
else{if(bodyState.style===null)document.body.removeAttribute('style');else document.body.setAttribute('style',bodyState.style);window.scrollTo(bodyState.x,bodyState.y);returnFocus?.focus({preventScroll:true});}}
document.addEventListener('click',e=>{const tool=e.target.closest('[data-ycet-tool-target]'),business=e.target.closest('[data-ycet-nav-target]');
if(tool){drawer(false);navigate(tool.dataset.ycetToolTarget);}else if(business&&interactive){e.preventDefault();navigate(business.dataset.ycetNavTarget);}
if(e.target.closest('.ycet-menu')){if(!dragged)drawer(true);dragged=false;}
if(e.target.closest('.ycet-overlay,[data-ycet-close]'))drawer(false);
if(e.target.closest('[data-ycet-back]'))history.back();});
document.addEventListener('keydown',e=>{if(e.key==='Escape')drawer(false);
if(e.key==='Tab'&&drawerOpen){const nodes=[...document.querySelector('.ycet-drawer').querySelectorAll('button,a[href],input,[tabindex]')].filter(n=>!n.disabled&&n.tabIndex>=0&&!n.hidden);
const first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}}});
window.addEventListener('hashchange',()=>{drawer(false);fromHash();});if(frameless)viewport();if(interactive){if(!location.hash.startsWith('#ycet='))history.replaceState(null,'','#ycet='+encodeURIComponent(meta.initial));fromHash();}else show(meta.initial);
// 仅缩放设备内容；实际占位同步缩放，放大后可滚动到所有边缘。
const stage=document.querySelector('.ycet-stage'),fit=document.querySelector('.ycet-fit'),content=document.querySelector('.ycet-fit-content');
if(stage&&fit){let automatic=true,scale=1;const width=meta.frame.preview.width,height=meta.frame.preview.height;
const output=document.querySelector('[data-ycet-zoom-value]');const minus=document.querySelector('[data-ycet-zoom="out"]'),plus=document.querySelector('[data-ycet-zoom="in"]');
content.style.width=width+'px';content.style.height=height+'px';
function resize(){if(automatic)scale=Math.max(.01,Math.min(1,(stage.clientWidth-48)/width,(stage.clientHeight-48)/height));fit.style.width=width*scale+'px';fit.style.height=height*scale+'px';content.style.transform='scale('+scale+')';output.textContent=Math.round(scale*100)+'%';minus.disabled=scale<=.1;plus.disabled=scale>=3;}
document.querySelectorAll('[data-ycet-zoom]').forEach(button=>button.addEventListener('click',()=>{const action=button.dataset.ycetZoom;automatic=action==='fit';if(!automatic)scale=Math.max(.1,Math.min(3,scale+(action==='in'?.1:-.1)));resize();if(automatic){stage.scrollTop=0;stage.scrollLeft=0;}}));
if(typeof ResizeObserver!=='undefined')new ResizeObserver(resize).observe(stage);window.addEventListener('resize',resize);resize();}
/* PAGE_INITIALIZERS */
})();
'''

def render(model, root):
    model=normalize_model(model); kind=model['type']
    theme, theme_css = shell_theme(model.get('shellTheme'))
    presentation = model.get('presentation', {})
    if not isinstance(presentation, dict) or presentation.get('density', 'comfortable') not in ('comfortable', 'compact'):
        raise BuildError('presentation 需要对象，density 为 comfortable 或 compact')
    presented = bool(theme) and kind != 'nonframe'
    if presented: theme_css += (ROOT/'assets/presentation.css').read_text()
    if kind == 'direction' and (model.get('directionCss') or model.get('directionJs') or model.get('direction')) and not theme:
        raise BuildError('结构化设计展板与局部样式需要 shellTheme')
    manifest=json.loads((ROOT/'assets/frames/manifest.json').read_text())
    port=str(model.get('productPort','')).strip().lower()
    route=manifest['routing'].get(port)
    if kind=='nonframe' and not route: raise BuildError('无框架原型必须指定有效 productPort')
    if port and not route: raise BuildError('未知 productPort，请先确认端口')
    model['productPort']=route.get('canonicalPort',port) if route else port
    frame=None
    if kind=='nonframe':
        if model.get('frameId'): warnings.warn('nonframe 忽略 frameId，不限制浏览器视口', UserWarning)
    else:
        default=(route or {}).get('defaultFrameId','iphone-15-pro')
        if route and model.get('hostDevice'):
            default=route.get('hostOverrides',{}).get(model['hostDevice'],default)
        frame_id=model.get('frameId',default)
        frame=next((f for f in manifest['frames'] if f['id']==frame_id),None)
        if not frame: raise BuildError('未知设备框架')
    pages=model.get('pages',[])
    if not pages or kind=='direction' and len(pages)!=1: raise BuildError('页面为空或设计预览不止一页')
    ids=[p['id'] for p in pages]
    if len(set(ids))!=len(ids) or any(not re.fullmatch('[a-z][a-z0-9-]*',i) for i in ids): raise BuildError('页面 ID 必须唯一且为 ASCII kebab-case')
    initial=model.get('initial',ids[0])
    if initial not in ids: raise BuildError('初始页未登记')
    bundler=ResourceBundler(root); owner=root/'build-input.json'; fragments=[]; styles=[]; scripts=[]
    for p in pages:
        ident=p['id']; source=p.get('html','')
        if p.get('layout','document') not in ('document','app'): raise BuildError('未知页面 layout')
        if re.search(r'<(?:html|head|body|script|style|link)\b',source,re.I): raise BuildError('html 只接受页面片段；CSS/JS 放入独立字段')
        # 为普通元素补稳定标识；原文件编辑时不重新编号。
        source=assign_element_ids(source,ident)
        fragment=bundler.inline_html_text(source,owner)
        selector=f'[data-ycet-page-id="{ident}"]'
        css=p.get('css','')
        # 页面样式与设计展板样式分别限定作用域，保持产品 DOM 隔离。
        styles.append(bundler.inline_css_text(scoped_css(css,selector,ident),owner))
        js=p.get('js','')
        problem=script_problem(js,page=True)
        if problem: raise BuildError(problem)
        scripts.append('(function(root,navigate){'+js+'})(document.querySelector('+json.dumps(selector)+'),navigate);')
        attr=' data-ycet-image-prototype="true"' if p.get('imagePrototype') else ''
        fragments.append(f'<section class="ycet-page" data-ycet-page-id="{ident}" data-ycet-layout="{p.get("layout","document")}" aria-label="{html.escape(p.get("label",ident),quote=True)}"{attr}>{fragment}</section>')
    template=''; frame_css=''
    if frame:
        template=(ROOT/'assets/frames'/frame['file']).read_text()
        frame_css=re.search('<style>(.*?)</style>',template,re.S)[1]
        template=re.sub('<style>.*?</style>','',template,flags=re.S)
    def device(content):return template.replace('{{CONTENT}}',content)
    nav=''.join(f'<button type="button" data-ycet-tool-target="{p["id"]}">{html.escape(p.get("label",p["id"]))}</button>' for p in pages)
    if presented and kind == 'demo': nav=navigation(model,pages)
    if kind in ('pages','direction'):
        body='<main class="ycet-grid">'+''.join(f'<article class="ycet-card"><h2>{html.escape(p.get("label",p["id"]))}</h2>'+((f'<p class="ycet-card-description">{html.escape(p.get("description",""))}</p>') if presented and p.get('description') else '')+device(frag)+'</article>' for p,frag in zip(pages,fragments))+'</main>'
        if kind=='direction':
            if presented:
                body=direction(model,theme,bundler,owner)+body
                styles.append(bundler.inline_css_text(scoped_css(model.get('directionCss',''),'.ycet-direction-summary','direction'),owner))
                js=model.get('directionJs','')
                problem=script_problem(js,page=True)
                if problem: raise BuildError(problem)
                if js: scripts.append('(function(root){'+js+'})(document.querySelector(".ycet-direction-summary"));')
            else: body=bundler.inline_html_text(model.get('directionHtml',''),owner)+body
        elif presented: body=heading(model,kind,len(pages))+body
    elif kind=='demo':body='<main class="ycet-layout"><nav class="ycet-nav" aria-label="页面导航" tabindex="0">'+nav+'</nav><div class="ycet-viewer"><div class="ycet-toolbar" role="group" aria-label="原型缩放"><button data-ycet-zoom="out" aria-label="缩小原型">−</button><output data-ycet-zoom-value aria-live="polite">100%</output><button data-ycet-zoom="in" aria-label="放大原型">＋</button><button data-ycet-zoom="fit">适应窗口</button></div><div class="ycet-stage" tabindex="0" aria-label="原型展示区"><div class="ycet-stage-inner"><div class="ycet-fit"><div class="ycet-fit-content">'+device(''.join(fragments))+'</div></div></div></div></div></main>'
    else:body=''.join(fragments)+'<button class="ycet-menu" aria-label="打开页面导航" aria-expanded="false">☰</button><button class="ycet-overlay" hidden aria-label="关闭导航"></button><aside class="ycet-drawer ycet-nav" role="dialog" aria-modal="true" aria-label="页面导航" hidden inert><button data-ycet-close>关闭</button>'+nav+'</aside>'
    meta={'schemaVersion':1,'skillVersion':'4.2.4','artifactVersion':model.get('artifactVersion',1),'type':kind,'productPort':model.get('productPort',''),'frame':frame,'initial':initial,'pages':[{'id':p['id'],'label':p.get('label',p['id']),'layout':p.get('layout','document')} for p in pages]}
    if theme: meta['shellTheme'] = theme
    if presented: meta['presentation'] = presentation
    variables='' if frame is None else f'--logical-w:{frame["logicalViewport"]["width"]}px;--logical-h:{frame["logicalViewport"]["height"]}px;--safe-top:{frame["safeArea"]["top"]}px;--safe-bottom:{frame["safeArea"]["bottom"]}px;--columns:{frame["defaultColumns"]}'
    css=((ROOT/'assets/nonframe.css').read_text() if kind=='nonframe' else STYLE+frame_css)+theme_css+'\n'.join(styles)
    if re.search('</(?:style|script)',css+'\n'.join(scripts),re.I):raise BuildError('代码字段含结束标签')
    runtime=RUNTIME
    if kind=='nonframe':
        start=runtime.index('// 仅缩放设备内容')
        end=runtime.index('/* PAGE_INITIALIZERS */',start)
        runtime=runtime[:start]+runtime[end:]
    body_class='ycet-'+kind+(' ycet-presented' if presented else '')
    density=html.escape(presentation.get('density','comfortable'),quote=True)
    document='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>'+html.escape(model.get('title','产品原型'))+'</title><style>'+css+'</style></head><body class="'+body_class+'" data-density="'+density+'" style="'+variables+'">'+body+'<div class="ycet-error" role="status" hidden></div><script type="application/json" id="ycet-metadata">'+safe_json_script(meta)+'</script><script>'+runtime.replace('/* PAGE_INITIALIZERS */','\n'.join(scripts))+'</script></body></html>'
    return document

def build(model, root, mode='create', target=None, expected_sha=None, *, purpose=None, validate=False):
    from prototype_guard import audit
    model=normalize_model(model)
    if mode not in ('create','iterate','overwrite'): raise BuildError('未知写入模式')
    purpose=purpose or ('initial' if mode=='create' else 'modify')
    if purpose not in ('initial','modify'): raise BuildError('未知任务用途')
    if mode in ('iterate','overwrite') and purpose=='initial': raise BuildError('迭代／覆盖属于修改任务')
    root=root.resolve(); (root/'outputs').mkdir(parents=True,exist_ok=True)
    output=output_path(root,model['type'],mode,target)
    before=hashlib.sha256(output.read_bytes()).hexdigest() if output.exists() else None
    if mode=='overwrite' and (not expected_sha or expected_sha!=before):raise BuildError('覆盖必须提供匹配的 --expected-sha')
    version=re.search(r'-v(\d+)\.html$',output.name)
    model={**model,'artifactVersion':int(version[1]) if version else 1}
    document=render(model,root)
    # 修改不隐式验收；显式 --validate 才执行。首次构建保留默认守卫。
    if purpose=='initial' or validate:
        problems=audit(document)
        if problems:raise BuildError('; '.join(problems))
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=output.parent,suffix='.tmp',delete=False) as f:
            temporary=Path(f.name); f.write(document); f.flush(); os.fsync(f.fileno())
        if mode=='overwrite':
            if hashlib.sha256(output.read_bytes()).hexdigest()!=before:raise BuildError('目标并发变化')
            os.replace(temporary,output)
        else:
            # 硬链接独占创建，避免覆盖同时出现的版本文件。
            os.link(temporary,output)
        return output
    finally:
        if temporary:temporary.unlink(missing_ok=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--prototype-dir',type=Path,required=True);p.add_argument('--mode',choices=['create','iterate','overwrite'],default='create');p.add_argument('--target');p.add_argument('--expected-sha');p.add_argument('--purpose',choices=['initial','modify']);p.add_argument('--validate',action='store_true',help='仅用户明确要求验收时用于修改任务');a=p.parse_args()
    try:print(build(json.loads(a.input.read_text()),a.prototype_dir,a.mode,a.target,a.expected_sha,purpose=a.purpose,validate=a.validate))
    except (BuildError,ValueError,KeyError,OSError) as e:p.exit(1,str(e)+'\n')
if __name__=='__main__':main()
