"""构建时生成展示壳样式；不解析产品 CSS、不修改设备模板或业务 DOM。"""
import re
from pathlib import Path
from prototype_document import BuildError

COLORS = {'background', 'surface', 'text', 'muted', 'border', 'accent', 'onAccent', 'activeBackground', 'activeText'}
REQUIRED = {'background', 'surface', 'text', 'muted', 'accent', 'onAccent'}
OPTIONAL = {'fontFamily', 'headingFontFamily', 'radius', 'shadow', 'colorScheme', 'headingWeight', 'lineStyle', 'motion'}
HEX = r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})'
LENGTH = r'-?\d+(?:\.\d+)?(?:px|rem|em)'


def shell_theme(value):
    # 旧输入不带主题时保持原样；新产物由 Agent 从已确认的产品视觉提取参数。
    if value is None:
        return {}, ''
    if not isinstance(value, dict) or REQUIRED - value.keys() or value.keys() - COLORS - OPTIONAL:
        raise BuildError('shellTheme 需要 background/surface/text/muted/accent/onAccent，且不能包含未知字段')
    theme = {
        'border': value['muted'], 'activeBackground': value['accent'], 'activeText': value['onAccent'],
        'fontFamily': 'system-ui, sans-serif', 'radius': '8px', 'shadow': 'none', 'colorScheme': 'light', 'headingWeight': '600', 'lineStyle': 'solid', 'motion': '160ms', **value,
    }
    theme.setdefault('headingFontFamily', theme['fontFamily'])
    for key, item in theme.items():
        if not isinstance(item, str) or len(item) > 240:
            raise BuildError('shellTheme.' + key + ' 必须是有效样式字符串')
        valid = False
        if key in COLORS:
            valid = re.fullmatch(HEX, item)
        elif key in ('fontFamily', 'headingFontFamily'):
            valid = re.fullmatch(r"[\w\s,\-'\"]+", item) and item.strip() and '\n' not in item and '\r' not in item
        elif key == 'radius':
            valid = re.fullmatch(r'(?:0|\d+(?:\.\d+)?(?:px|rem|em))', item)
        elif key == 'shadow':
            valid = item == 'none' or re.fullmatch(r'(?:inset )?(?:' + LENGTH + r' ){2,4}' + HEX, item)
        elif key == 'headingWeight':
            valid = item in ('400','500','600','700','800')
        elif key == 'lineStyle':
            valid = item in ('solid','dashed','dotted')
        elif key == 'motion':
            valid = re.fullmatch(r'(?:0|[1-9]\d{0,2})ms', item) and int(item[:-2]) <= 300
        elif key == 'colorScheme':
            valid = item in ('light', 'dark')
        if not valid:
            raise BuildError('shellTheme.' + key + ' 格式无效，参见展示壳主题契约')
    # 白名单只允许样式值，避免闭合标签、声明注入及外部资源请求。
    declarations = ';'.join('--ycet-shell-' + re.sub(r'[A-Z]', lambda m: '-' + m[0].lower(), key) + ':' + item for key, item in theme.items())
    css = ':root{' + declarations + '}\n' + (Path(__file__).resolve().parents[1] / 'assets/shell-theme.css').read_text()
    return theme, css
