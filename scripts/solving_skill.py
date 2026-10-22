"""Capture the self-contained, linked resource closure of one solving skill."""
from __future__ import annotations

from html.parser import HTMLParser
import os
from pathlib import Path, PurePosixPath
import re
import stat
from urllib.parse import unquote, urlsplit


def _read_source(root_fd: int, relative: str) -> tuple[bytes, tuple[int, ...]]:
    """Read through directory descriptors so symlink swaps cannot escape root."""
    directory = os.dup(root_fd)
    try:
        parts = PurePosixPath(relative).parts
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        with os.fdopen(descriptor, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError('solving reference is not a regular file: ' + relative)
            data = stream.read()
            after = os.fstat(stream.fileno())
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size,
                                  value.st_mtime_ns, value.st_ctime_ns)
        if identity(before) != identity(after):
            raise ValueError('solving source changed while loading: ' + relative)
        return data, identity(after)
    except OSError as exc:
        raise ValueError('invalid or unsafe solving reference: ' + relative) from exc
    finally:
        os.close(directory)


def _prose(text: str) -> str:
    """Ignore illustrative links inside Markdown code and HTML comments."""
    text = re.sub(r'<!--[\s\S]*?-->', lambda match: '\n' * match[0].count('\n'), text)
    # One raw HTML tag can span indented attribute lines. Protect the complete
    # tag first, so its opening line decides whether it belongs to prose/code.
    prefix = 'SCIREL_PRESERVED_HTML_'
    while prefix in text:
        prefix += '_'
    tags = {}

    def protect(match):
        before = text[text.rfind('\n', 0, match.start()) + 1:match.start()]
        if (re.search(r'\]\([ \t]*$', before) or
                re.fullmatch(r' {0,3}\[[^\]]+\]:[ \t]*', before)):
            # Angle-bracket Markdown destinations are URLs, not containers.
            return match[0]
        token = prefix + str(len(tags)) + '_'
        tags[token] = match[0]
        return token

    text = re.sub(r'''</?[A-Za-z][A-Za-z0-9:-]*(?=[\s/>])(?:[^"'<>]|"[^"]*"|'[^']*')*>''',
                  protect, text)
    lines, fence, list_indents, html_stack = [], None, [], []
    void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                 'link', 'meta', 'param', 'source', 'track', 'wbr'}
    inline_code = r'(?<!`)(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)'

    def html_context(line):
        # Quoted HTML examples never open a prose container for following lines.
        line = re.sub(inline_code, '', line)
        for token in re.findall(re.escape(prefix) + r'[0-9]+_', line):
            tag = tags[token]
            name = re.match(r'</?([A-Za-z][A-Za-z0-9:-]*)', tag)[1].lower()
            if tag.startswith('</'):
                if name in html_stack:
                    del html_stack[len(html_stack) - 1 - html_stack[::-1].index(name):]
            elif name not in void_tags and not tag.rstrip().endswith('/>'):
                html_stack.append(name)

    for line in text.splitlines():
        expanded = line.expandtabs(4)
        if fence:
            marker = re.match(r'^ {0,3}(`{3,}|~{3,})', expanded[fence[1]:])
            if (marker and marker[1][0] == fence[0][0] and len(marker[1]) >= len(fence[0])
                    and not expanded[fence[1] + marker.end():].strip()):
                fence = None
            lines.append('')
        else:
            if expanded.strip():
                indent = len(expanded) - len(expanded.lstrip())
                while list_indents and indent < list_indents[-1]:
                    list_indents.pop()
                content_indent = list_indents[-1] if list_indents else 0
                marker = re.match(r'^ {0,3}(`{3,}|~{3,})', expanded[content_indent:])
                if marker:
                    fence = marker[1], content_indent
                    lines.append('')
                    continue
                if indent >= content_indent + 4 and not html_stack:
                    lines.append('')
                    continue
                bullet = re.match(r'^\s*(?:[-+*]|[0-9]+[.)])[ \t]+', expanded)
                if bullet and not html_stack:
                    list_indents.append(bullet.end())
            lines.append(line)
            html_context(line)
    text = re.sub(inline_code, '', '\n'.join(lines))
    for token, tag in tags.items():
        text = text.replace(token, tag)
    return text


def _destination(text: str) -> str:
    text = text.strip()
    if text.startswith('<'):
        end = text.find('>')
        if end < 0:
            raise ValueError('invalid solving Markdown reference destination')
        target, title = text[1:end], text[end + 1:].strip()
    else:
        match = re.match(r'(?:\\.|[^\s])+', text)
        target = match[0] if match else ''
        title = text[len(target):].strip()
    if not target or (title and not re.fullmatch(r'"[^"\n]*"|\x27[^\x27\n]*\x27|\([^\n]*\)', title)):
        raise ValueError('invalid solving Markdown reference destination')
    return re.sub(r'\\([!"#$%&\x27()*+,\-./:;<=>?@\[\\\]^_`{|}~ ])', r'\1', target)


def srcset_links(value: str) -> list[str]:
    """Read static image candidates, rejecting unsupported descriptor syntax."""
    targets, position = [], 0
    while position < len(value):
        while position < len(value) and value[position] in ' \t\r\n\f,':
            position += 1
        start = position
        while position < len(value) and value[position] not in ' \t\r\n\f':
            position += 1
        target = value[start:position]
        if not target:
            break
        if target.endswith(','):
            target, descriptors = target.rstrip(','), []
        else:
            start = position
            while position < len(value) and value[position] != ',':
                position += 1
            descriptors = value[start:position].split()
            position += position < len(value)
        if (not target or len(descriptors) > 1 or
                descriptors and not re.fullmatch(
                    r'(?:[1-9][0-9]*w|(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)x)', descriptors[0])):
            raise ValueError('invalid static resource srcset')
        targets.append(target)
    return targets


class _HTMLLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []
        self.anchors: set[str] = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if value is not None and (key in {'href', 'src', 'xlink:href', 'poster'}
                                      or tag == 'object' and key == 'data'):
                self.targets.append(value)
            if value is not None and key == 'srcset':
                self.targets.extend(srcset_links(value))
            if value is not None and key in {'id', 'name'}:
                self.anchors.add(value)


def html_links(text: str) -> tuple[list[str], set[str]]:
    parser = _HTMLLinks()
    parser.feed(text)
    return parser.targets, parser.anchors


def markdown_links(text: str) -> tuple[list[str], set[str]]:
    """Return used link destinations and anchors from static Markdown prose."""
    prose = _prose(text)
    targets, anchors = html_links(prose)
    definitions = {}
    for match in re.finditer(r'^ {0,3}\[([^\]\n]+)\]:[ \t]*(.*)$', prose, re.MULTILINE):
        key = ' '.join(match[1].split()).casefold()
        if key in definitions:
            raise ValueError('duplicate solving Markdown reference definition: ' + key)
        definitions[key] = _destination(match[2])
    prose = re.sub(r'^ {0,3}\[([^\]\n]+)\]:[ \t]*(.*)$', '', prose, flags=re.MULTILINE)
    references = list(re.finditer(r'\[([^\]\n]*)\]\[([^\]\n]*)\]', prose))
    for match in references:
        label = match[2] or match[1]
        key = ' '.join(label.split()).casefold()
        if key not in definitions:
            raise ValueError('undefined solving Markdown reference: ' + label)
        targets.append(definitions[key])
    prose = re.sub(r'\[([^\]\n]*)\]\[([^\]\n]*)\]', '', prose)
    inline_spans = []
    for match in re.finditer(r'\]\(', prose):
        start, position, depth = match.end(), match.end(), 1
        angle = False
        while position < len(prose) and depth:
            char = prose[position]
            if char == '\\':
                position += 2
                continue
            if char == '<':
                angle = True
            elif char == '>':
                angle = False
            elif not angle and char == '(':
                depth += 1
            elif not angle and char == ')':
                depth -= 1
            position += 1
        if depth:
            raise ValueError('unclosed solving Markdown reference')
        targets.append(_destination(prose[start:position - 1]))
        # A label with an inline destination is not a shortcut reference too.
        label = prose.rfind('[', 0, match.start())
        inline_spans.append((label if label >= 0 else match.start(), position))
    shortcuts = prose
    for start, end in reversed(inline_spans):
        shortcuts = shortcuts[:start] + ' ' * (end - start) + shortcuts[end:]
    for match in re.finditer(r'\[([^\]\n]+)\]', shortcuts):
        key = ' '.join(match[1].split()).casefold()
        if key in definitions:
            targets.append(definitions[key])
    counts = {}
    for match in re.finditer(r'^ {0,3}#{1,6}[ \t]+(.+?)#*[ \t]*$', prose, re.MULTILINE):
        heading = re.sub(r'<[^>]*>', '', match[1]).casefold()
        heading = re.sub(r'[^\w\-\s]', '', heading)
        slug = re.sub(r'\s', '-', heading)
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        anchors.add(slug + ('-' + str(count) if count else ''))
    return targets, anchors


def _local_reference(parent: str, target: str) -> tuple[str, str] | None:
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme in {'http', 'https'} and parsed.netloc:
            return None
        if parsed.scheme == 'mailto' and parsed.path:
            return None
        raise ValueError('unsupported or cross-skill solving reference: ' + target)
    if parsed.query or re.search(r'%(?![0-9a-fA-F]{2})', parsed.path + parsed.fragment):
        raise ValueError('invalid solving reference: ' + target)
    path = unquote(parsed.path, errors='strict')
    if path.startswith('/') or '\\' in path or '\x00' in path:
        raise ValueError('solving reference leaves its skill: ' + target)
    parts = list(PurePosixPath(parent).parent.parts)
    if path:
        for part in path.split('/'):
            if part in {'', '.'}:
                continue
            if part == '..':
                if not parts:
                    raise ValueError('solving reference leaves its skill: ' + target)
                parts.pop()
            else:
                parts.append(part)
        relative = '/'.join(parts)
    else:
        relative = parent
    if not relative:
        raise ValueError('solving reference names a directory: ' + target)
    return relative, unquote(parsed.fragment, errors='strict')


def load_solving_skill(skill_root: Path) -> dict[str, bytes]:
    """Return unchanged bytes for SKILL.md and its reachable local resources.

    Markdown links, reference definitions and HTML href/src attributes declare
    the closure. Only Markdown is traversed; executable helpers and assets stay
    at their original relative paths. No input is taken from another skill or
    from a previous export, and unlinked source-local files are not exported.
    """
    try:
        root_fd = os.open(skill_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise ValueError('invalid or unsafe solving skill root: ' + str(skill_root)) from exc
    sources, identities, anchors, fragments = {}, {}, {}, []
    pending = ['SKILL.md']
    try:
        while pending:
            relative = pending.pop()
            if relative in sources:
                continue
            data, identity = _read_source(root_fd, relative)
            sources[relative], identities[relative] = data, identity
            if PurePosixPath(relative).suffix.lower() == '.md':
                try:
                    targets, anchors[relative] = markdown_links(data.decode('utf-8'))
                except UnicodeError as exc:
                    raise ValueError('invalid UTF-8 solving Markdown: ' + relative) from exc
                for target in targets:
                    local = _local_reference(relative, target)
                    if local is not None:
                        path, fragment = local
                        pending.append(path)
                        if fragment and PurePosixPath(path).suffix.lower() == '.md':
                            fragments.append((path, fragment))
        for relative, fragment in fragments:
            if fragment not in anchors[relative]:
                raise ValueError('missing solving Markdown anchor: ' + relative + '#' + fragment)
        for relative, data in sources.items():
            current, identity = _read_source(root_fd, relative)
            if current != data or identity != identities[relative]:
                raise ValueError('solving source changed while loading: ' + relative)
        return dict(sorted(sources.items()))
    finally:
        os.close(root_fd)
