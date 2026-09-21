"""轻量词法检查；不执行用户脚本，也不引入构建依赖。"""
import re

JS_TOKEN = re.compile(r"[A-Za-z_$][\w$]*|=>|\?\.")


def script_tokens(source):
    """区分代码、字符串和注释；模板插值仍作为代码检查。"""
    tokens = []
    length = len(source)

    def scan(index, interpolation=False):
        depth = 0
        while index < length:
            char = source[index]
            if char.isspace():
                index += 1
                continue
            if source.startswith('//', index):
                end = source.find('\n', index)
                index = length if end < 0 else end + 1
                continue
            if source.startswith('/*', index):
                end = source.find('*/', index + 2)
                index = length if end < 0 else end + 2
                continue
            if char in "\"'`":
                quote = char
                start = index = index + 1
                while index < length:
                    if source[index] == '\\':
                        index += 2
                    elif quote == '`' and source.startswith('${', index):
                        tokens.append(('string', source[start:index]))
                        tokens.append(('code', '('))
                        index = scan(index + 2, True)
                        tokens.append(('code', ')'))
                        start = index
                    elif source[index] == quote:
                        tokens.append(('string', source[start:index]))
                        index += 1
                        break
                    else:
                        index += 1
                continue
            # 表达式开头的斜杠按正则字面量处理，避免把正则内容当调用。
            previous = tokens[-1][1] if tokens else ''
            if char == '/' and (not tokens or previous in ('=', '(', '[', ',', ':', '!', '?', ';', '{', 'return', '=>')):
                index += 1
                in_class = False
                while index < length:
                    if source[index] == '\\':
                        index += 2
                        continue
                    if source[index] == '[':
                        in_class = True
                    elif source[index] == ']':
                        in_class = False
                    elif source[index] == '/' and not in_class:
                        index += 1
                        while index < length and source[index].isalpha():
                            index += 1
                        break
                    index += 1
                tokens.append(('string', ''))
                continue
            if char == '}' and interpolation and depth == 0:
                return index + 1
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
            match = JS_TOKEN.match(source, index)
            value = match[0] if match else char
            tokens.append(('code', value))
            index += len(value)
        return index

    scan(0)
    return tokens


def script_problem(source, page=False):
    tokens = script_tokens(source)
    code = ' '.join(value if kind == 'code' else 'STRING' for kind, value in tokens)
    if page and re.search(r'\b(?:document|window|globalThis|self|parent|top|location)\b|\b(?:eval|Function)\s*\(', code):
        return '页面 JS 请使用 root、navigate；全局访问需先重构'
    if re.search(r'\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|importScripts|sendBeacon)\s*(?:\?\.)?\s*\(|\bimport\s*\(|\.\s*srcdoc\b|\blocation\s*\.\s*(?:href|assign|replace)\b|\bwindow\s*\.\s*open\s*\(|\bserviceWorker\s*\.\s*register\s*\(', code):
        return '脚本包含外部请求或页面嵌套／离开文档行为'
    for index, (kind, value) in enumerate(tokens):
        if kind == 'code' and value == 'createElement' and tokens[index + 1:index + 2] == [('code', '(')]:
            argument = tokens[index + 2:index + 3]
            if argument and argument[0][0] == 'string' and argument[0][1].lower() in ('iframe', 'object', 'embed'):
                return '禁止动态页面嵌套'
    return None


def split_selectors(header):
    """只在选择器顶层切分逗号，保留函数和属性字符串中的逗号。"""
    result, start, depth, quote, escaped = [], 0, 0, None, False
    for index, char in enumerate(header):
        if escaped:
            escaped = False
        elif char == '\\':
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char in '([':
            depth += 1
        elif char in ')]':
            depth -= 1
        elif char == ',' and depth == 0:
            result.append(header[start:index])
            start = index + 1
    result.append(header[start:])
    return result
