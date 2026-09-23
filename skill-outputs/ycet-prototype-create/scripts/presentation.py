"""展示壳的确定性排版与设计样本：只生成外围节点，复用产品视觉参数。"""
import html
import re
from prototype_document import BuildError
from shell_theme import HEX


def text(value):
    return html.escape(str(value), quote=True)


def heading(model, kind, count):
    labels = {'direction': '设计方向', 'pages': f'静态原型 · {count} 个页面', 'demo': '交互演示'}
    summary = model.get('presentation', {}).get('summary', '')
    return f'<header class="ycet-shell-heading"><small>{labels[kind]}</small><h1>{text(model.get("title", "产品原型"))}</h1>' + (f'<p>{text(summary)}</p>' if summary else '') + '</header>'


def navigation(model, pages):
    parts = [heading(model, 'demo', len(pages))]
    group = None
    for page in pages:
        current = page.get('group', '页面导航')
        if current != group:
            parts.append(f'<p class="ycet-nav-group">{text(current)}</p>')
            group = current
        description = page.get('description', '')
        parts.append(f'<button type="button" data-ycet-tool-target="{page["id"]}"><span>{text(page.get("label",page["id"]))}</span>' + (f'<small>{text(description)}</small>' if description else '') + '</button>')
    parts.append('<p class="ycet-nav-hint">选择页面浏览原型<br>页面中的操作保留演示状态</p>')
    return ''.join(parts)


def direction(model, theme, bundler, owner):
    data = model.get('direction', {})
    if not isinstance(data, dict):
        raise BuildError('direction 必须为包含 palette、components 等字段的对象')
    palette = data.get('palette') or [{'name': label, 'value': theme[key], 'usage': usage} for key,label,usage in [
        ('accent','主色','主要操作与焦点'),('background','背景','外围画布'),('surface','表面','卡片与面板'),
        ('text','正文','主要内容'),('muted','次级文字','辅助说明'),('border','边框','分隔与轮廓')]]
    if not isinstance(palette, list):
        raise BuildError('direction.palette 必须为数组')
    swatches = []
    for color in palette:
        if not isinstance(color, dict) or not re.fullmatch(HEX, str(color.get('value', ''))):
            raise BuildError('色板 value 必须为十六进制颜色')
        swatches.append(f'<article class="ycet-swatch"><span style="background:{color["value"]}" aria-hidden="true"></span><b>{text(color.get("name", "色彩"))}</b><code>{color["value"]}</code><small>{text(color.get("usage", ""))}</small></article>')
    title_sample = data.get('titleSample', model.get('title', '产品标题'))
    body_sample = data.get('bodySample', model.get('presentation', {}).get('summary') or '在这里展示产品的正文、说明与阅读节奏。')
    typography = f'<div class="ycet-type-card"><small>标题 · {text(theme["headingFontFamily"])}</small><strong>{text(title_sample)}</strong></div><div class="ycet-type-card"><small>正文 · {text(theme["fontFamily"])}</small><p>{text(body_sample)}</p><span>辅助文字与内容保持清晰的层级。</span></div>'
    components = data.get('components', [])
    if not isinstance(components, list):
        raise BuildError('direction.components 必须为数组')
    specimens = []
    for component in components:
        if not isinstance(component, dict):
            raise BuildError('组件样本必须为对象')
        fragment = component.get('html', '')
        if not isinstance(fragment, str) or re.search(r'<(?:html|head|body|script|style|link)\b', fragment, re.I):
            raise BuildError('组件 html 只接受片段，样式／交互使用 directionCss／directionJs')
        specimens.append('<article class="ycet-specimen"><h3>'+text(component.get('title','组件'))+'</h3><div class="ycet-specimen-stage">'+bundler.inline_html_text(fragment,owner)+'</div><p>'+text(component.get('description',''))+'</p></article>')
    legacy = bundler.inline_html_text(model.get('directionHtml', ''), owner)
    return '<section class="ycet-direction-summary">'+heading(model,'direction',1)+'<section class="ycet-board-section"><h2>色彩方案</h2><div class="ycet-palette">'+''.join(swatches)+'</div></section><section class="ycet-board-section"><h2>文字层级</h2><div class="ycet-type-grid">'+typography+'</div></section>'+('<section class="ycet-board-section"><h2>组件与反馈</h2><div class="ycet-specimens">'+''.join(specimens)+'</div></section>' if specimens else '')+('<section class="ycet-board-section ycet-direction-custom">'+legacy+'</section>' if legacy else '')+'</section>'


def scoped_css(css, selector, prefix):
    """页面与展板共用作用域契约，媒体查询保留，动画名分开。"""
    from prototype_syntax import split_selectors
    if css and ':scope' not in css:
        raise BuildError('CSS 使用 :scope 限定所属区域')
    for rule in re.finditer(r'([^{}]+)\{', re.sub(r'/\*.*?\*/','',css,flags=re.S)):
        header=rule[1].strip()
        if header.startswith('@'):
            if 'keyframes' in header and not re.search(r'keyframes\s+'+re.escape(prefix)+'-',header):
                raise BuildError('动画名必须加所属区域 ID 前缀')
            continue
        if re.fullmatch(r'(?:from|to|[\d.% ,]+)',header):
            continue
        if any(':scope' not in part for part in split_selectors(header)):
            raise BuildError('每个 CSS 选择器必须限定 :scope')
    return css.replace(':scope', selector)
