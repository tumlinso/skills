#!/usr/bin/env python3
"""Read complete atlas cards under a word budget; no third-party dependencies."""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def resolve(path: str) -> Path:
    p = (ROOT / path).resolve()
    if not p.is_relative_to(ROOT):
        raise ValueError('Manifest path escapes the atlas directory')
    return p

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('search', help='Search summaries/tags; opt in to full text')
    p.add_argument('query'); p.add_argument('--limit', type=int, default=8)
    p.add_argument('--full', action='store_true')
    p = sub.add_parser('read', help='Emit complete cards or a summary when budget is too small')
    p.add_argument('ids', nargs='+'); p.add_argument('--budget', type=int, default=2000)
    p.add_argument('--refs', action='store_true', help='Add prerequisite/source summaries only')
    p = sub.add_parser('list')
    p.add_argument('--kind', choices=['reference','mechanism','composition','experiment','index','source'])
    args = ap.parse_args()
    try:
        manifest = json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
        docs = {d['id']:d for d in manifest['documents']}
        sources = {s['id']:s for s in manifest['sources']}
    except (OSError, ValueError, KeyError) as exc:
        ap.error(f'Cannot read manifest: {exc}')
    if args.command == 'list':
        entries = list(docs.values()) + ([dict(s,kind='source') for s in sources.values()] if args.kind == 'source' else [])
        for d in entries:
            if args.kind and d.get('kind') != args.kind: continue
            print(f"{d['id']}\t{d.get('words','?')} words\t{d['title']}\t{d['path']}")
        return 0
    if args.command == 'search':
        terms = re.findall(r'[a-z0-9]+',args.query.lower())
        if not terms: ap.error('Query must contain a searchable word')
        if args.limit < 1: ap.error('Limit must be positive')
        scored=[]
        for d in docs.values():
            text=' '.join([d['title'],d['summary']]+d['tags']).lower()
            hits=sum(bool(re.search(r'\b'+re.escape(t),text)) for t in terms)
            score=hits*12+sum(min(text.count(t),3) for t in terms)
            if args.full:
                body=resolve(d['path']).read_text(encoding='utf-8').lower()
                score+=sum(min(body.count(t),4) for t in terms)
            if score:
                score*=dict(mechanism=1.15,composition=1.1,experiment=.75,index=.7).get(d['kind'],1.0)
                scored.append((score,d))
        for _,d in sorted(scored,key=lambda item:(-item[0],item[1].get('words',0)))[:args.limit]:
            print(f"{d['id']} | {d.get('words','?')} words | {d['path']}\n{d['summary']}\n")
        if not scored: print('No matching summaries. Try --full or a related computational need.')
        return 0
    if args.budget < 1: ap.error('Budget must be positive')
    missing=[x for x in args.ids if x not in docs and x not in sources]
    if missing:
        print('Unknown IDs: '+', '.join(missing),file=sys.stderr)
        return 2
    remaining=args.budget; refs=[]
    for id in args.ids:
        d=docs.get(id) or sources[id]
        text=resolve(d['path']).read_text(encoding='utf-8')
        if id in docs: refs += d['requires']+d['sources']
        words=len(text.split())
        if words>remaining:
            summary=d.get('summary',d.get('evidence_capsule',''))
            text=f"[{id}: complete card deferred, not truncated]\n{summary}\nRead {d['path']} ({words} words), including its constraints and evidence.\n"
        size=len(text.split())
        if size<=remaining:
            print(text,end='\n' if not text.endswith('\n\n') else '')
            remaining-=size
        else:
            print(f'[{id}: deferred; word budget exhausted.]',file=sys.stderr)
    if args.refs:
        for id in dict.fromkeys(refs):
            if id in args.ids: continue
            d=docs.get(id) or sources.get(id)
            if not d: continue
            summary=d.get('summary',d.get('evidence_capsule',''))
            # Source capsules are intentionally concise and independently readable.
            text=f"Reference {id}: {summary} [{d['path']}]\n"
            if len(text.split())<=remaining:
                print(text,end=''); remaining-=len(text.split())
    print(f'[{args.budget-remaining}/{args.budget} words emitted; evidence status unchanged.]',file=sys.stderr)
    return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except (OSError,ValueError,KeyError) as exc:
        print(f'Atlas reader error: {exc}',file=sys.stderr)
        raise SystemExit(2)
