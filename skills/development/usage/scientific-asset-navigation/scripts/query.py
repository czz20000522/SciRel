"""Offline progressive discovery over a bound SciRel documentation snapshot.

Standard library only. Projects and platform bundles use this same consumer
tool; it does not import science, build documents, or decide applicability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


class Catalog:
    def __init__(self, root, expected_digest=None):
        self.root = Path(root).resolve()
        self.manifest = json.loads((self.root / 'manifest.json').read_bytes())
        unsigned = {k: v for k, v in self.manifest.items() if k != 'snapshot_sha256'}
        self.digest = hashlib.sha256(encode(unsigned)).hexdigest()
        if (self.manifest.get('schema') != 'scirel.documentation-snapshot'
                or self.digest != self.manifest.get('snapshot_sha256')):
            raise ValueError('invalid snapshot manifest')
        if expected_digest and expected_digest != self.digest:
            raise ValueError('snapshot differs from expected digest')
        self.capability_index = self.read('capabilities.json')
        self.capabilities = {x['asset_id']: x for x in self.capability_index['assets']}
        self.records = self.capabilities
        if len(self.capabilities) != self.manifest['asset_count']:
            raise ValueError('capability index coverage mismatch')
        self.book = self.read('handbook.json')
        self.topics = {}
        ids = []
        chapters = self.book['chapters']
        if len({c['id'] for c in chapters}) != len(chapters):
            raise ValueError('duplicate chapter')
        for chapter in chapters:
            for topic in chapter['topics']:
                if topic['id'] in self.topics:
                    raise ValueError('duplicate topic')
                self.topics[topic['id']] = topic
                ids.extend(topic['assets'])
        if len(ids) != len(set(ids)) or set(ids) != set(self.records):
            raise ValueError('route coverage differs from snapshot index')

    def read(self, relative):
        binding = self.manifest['files'][relative]
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('snapshot path escapes root')
        data = path.read_bytes()
        if len(data) != binding['bytes'] or hashlib.sha256(data).hexdigest() != binding['sha256']:
            raise ValueError('snapshot bytes changed: ' + relative)
        return json.loads(data)

    def envelope(self, **items):
        return dict(snapshot_sha256=self.digest, indexed_assets=len(self.records),
                    coverage='bound documentation snapshot only; not proof of scientific availability', **items)

    def routes(self, chapter=None):
        if chapter is None:
            return self.envelope(items=[dict(id=c['id'], title=c['title'],
                topic_count=len(c['topics']), asset_count=sum(len(t['assets']) for t in c['topics']))
                for c in self.book['chapters']])
        c = next((c for c in self.book['chapters'] if c['id'] == chapter), None)
        if c is None:
            raise KeyError('unknown chapter: ' + chapter)
        return self.envelope(chapter=chapter, items=[dict(id=t['id'], title=t['title'],
            introduction=t['introduction'], asset_count=len(t['assets'])) for t in c['topics']])

    def search(self, q='', topic=None, kind=None, offset=0, limit=5):
        if not q.strip() and not topic:
            raise ValueError('search needs --q or --topic; use routes for orientation')
        if len(q) > 512 or offset < 0 or not 1 <= limit <= 20:
            raise ValueError('q <= 512 characters, offset >= 0, limit 1..20 required')
        if kind not in (None, 'operator', 'task_graph'):
            raise ValueError('invalid kind')
        allowed = set(self.topics[topic]['assets']) if topic else set(self.records)
        if kind is not None:
            raise ValueError('this snapshot has no TaskGraph kind facet; use the capability index')
        terms = q.lower().split()
        # Lexical retrieval only; preserve every match and expose pagination.
        matches = [x for x in self.capabilities.values() if x['asset_id'] in allowed
                   and all(t in self.capability_index['search_text'].get(x['asset_id'], '').lower()
                           for t in terms)]
        matches.sort(key=lambda x: x['asset_id'])
        cards = [{k: x.get(k) for k in ('asset_id', 'capability', 'capability_summary',
                                         'summary_zh', 'public_api', 'device_scope')}
                 for x in matches[offset:offset + limit]]
        return self.envelope(items=cards, query=q, topic=topic, kind=kind,
            inspected_assets=len(allowed), total=len(matches), offset=offset,
            next_offset=offset + limit if offset + limit < len(matches) else None,
            applicability='unassessed; read selected exact contracts; zero keyword hits do not establish a gap')

    def show(self, asset, view='call'):
        if asset not in self.records:
            raise KeyError('unknown asset: ' + asset)
        doc = self.read('records/' + asset + '.json')
        if doc.get('asset_id') != asset:
            raise ValueError('exact record identity mismatch')
        if view == 'full':
            return self.envelope(view=view, document=doc)
        if view == 'graph':
            if 'graph' not in doc:
                raise ValueError('asset has no graph; use call or full')
            return self.envelope(view=view, asset_id=asset, graph=doc['graph'])
        if view != 'call':
            raise ValueError('invalid document view')
        # Copy whole public sections, never summarize away domains or failures.
        omitted = {'graph', 'provenance'}
        result = {k: v for k, v in doc.items() if k not in omitted}
        if 'graph' in doc:
            result['graph_execution'] = doc['graph']['execution']
        return self.envelope(view=view, document=result,
                             omitted_sections=sorted(omitted & doc.keys()),
                             detail='exact public sections; use --view graph for wiring, --view full for original record')


def bundled_snapshot():
    script = Path(__file__).resolve()
    for parent in script.parents:
        if (parent.name == 'skills' and script.relative_to(parent).as_posix()
                == 'development/usage/scientific-asset-navigation/scripts/query.py'):
            path = parent.parent / 'docs/manual'
            if (path / 'manifest.json').is_file():
                return path
            break
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=bundled_snapshot())
    parser.add_argument('--expected-digest')
    sub = parser.add_subparsers(dest='command', required=True)
    route = sub.add_parser('routes', help='small chapter list or one chapter of topics')
    route.add_argument('--chapter')
    search = sub.add_parser('search', help='bounded candidate cards, not full contracts')
    search.add_argument('--q', default='')
    search.add_argument('--topic')
    search.add_argument('--offset', type=int, default=0)
    search.add_argument('--limit', type=int, default=5)
    show = sub.add_parser('show', help='exact public sections; graph internals and provenance on demand')
    show.add_argument('asset')
    show.add_argument('--view', choices=['call', 'graph', 'full'], default='call')
    args = parser.parse_args(argv)
    if not args.snapshot:
        parser.error('provide --snapshot PATH; no docs/manual beside the bundled skills directory found')
    try:
        catalog = Catalog(args.snapshot, args.expected_digest)
        if args.command == 'routes':
            result = catalog.routes(args.chapter)
        elif args.command == 'search':
            result = catalog.search(args.q, args.topic, None, args.offset, args.limit)
        else:
            result = catalog.show(args.asset, args.view)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'error': str(error), 'outcome': 'catalog_unavailable_not_capability_absent'}), file=sys.stderr)
        return 2
    # One complete JSON record for machine consumption. Keep canonical encode()
    # unchanged: existing snapshot digests bind its pretty-printed byte format.
    print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
