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
    lines, fence = [], None
    for line in text.splitlines():
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
            lines.append('')
        elif marker:
            fence = marker[1]
            lines.append('')
        else:
            lines.append(line)
    text = re.sub(r'<!--[\s\S]*?-->', '', '\n'.join(lines))
    return re.sub(r'(`+)(.*?)\1', '', text)


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


class _HTMLLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []
        self.anchors: set[str] = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if value is not None and key in {'href', 'src'}:
                self.targets.append(value)
            if value is not None and key in {'id', 'name'}:
                self.anchors.add(value)


def _markdown_links(text: str) -> tuple[list[str], set[str]]:
    prose = _prose(text)
    html = _HTMLLinks()
    html.feed(prose)
    targets = list(html.targets)
    definitions = {}
    for match in re.finditer(r'^ {0,3}\[([^\]\n]+)\]:[ \t]*(.*)$', prose, re.MULTILINE):
        key = ' '.join(match[1].split()).casefold()
        if key in definitions:
            raise ValueError('duplicate solving Markdown reference definition: ' + key)
        definitions[key] = _destination(match[2])
    targets.extend(definitions.values())
    for match in re.finditer(r'\[[^\]\n]*\]\[([^\]\n]*)\]', prose):
        label = match[1] or re.search(r'\[([^\]\n]*)\]', match[0])[1]
        if ' '.join(label.split()).casefold() not in definitions:
            raise ValueError('undefined solving Markdown reference: ' + label)
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
    anchors = set(html.anchors)
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
                    targets, anchors[relative] = _markdown_links(data.decode('utf-8'))
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
