#!/usr/bin/env python3
"""Refresh document metadata and the current evidence-aware full Markdown guide."""
from __future__ import annotations
import collections
import hashlib
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'experiments/evidence/v100-20261006'

def portable_cuda_compiled(provenance: dict, raw_build_path: Path|None=None) -> bool:
    """Read the checked-in build receipt; compare ignored raw copy when present."""
    identity=provenance.get('campaign_identity',{})
    build=identity.get('build',{})
    receipt_hash=provenance.get('campaign_input_sha256',{}).get('build.json','')
    valid=(provenance.get('cuda_compiled') is True and build.get('returncode')==0 and
           bool(re.fullmatch(r'[0-9a-f]{64}',receipt_hash)) and
           build.get('receipt_sha256')==receipt_hash and
           bool(build.get('binary_sha256')))
    if not valid: return False
    if raw_build_path is not None and raw_build_path.is_file():
        if hashlib.sha256(raw_build_path.read_bytes()).hexdigest()!=receipt_hash:
            raise ValueError(f'Raw build receipt disagrees with portable provenance: {raw_build_path}')
    return True

def main() -> None:
    p=ROOT/'manifest.json'; obj=json.loads(p.read_text(encoding='utf-8'))
    # Preserve the original authoring-time claim separately from current checked-in
    # measurement evidence. This is intentionally idempotent across refreshes.
    obj.setdefault('authoring_evidence',{
        'source_commit':'5c1f805db80a81f7476ede8292abba69821d104f',
        'source_date':'2026-10-03',
        'gpu_measured':obj.get('gpu_measured',False),
        'cuda_compiled':obj.get('cuda_compiled',False),
    })
    for d in obj['documents']+obj['sources']:
        path=(ROOT/d['path']).resolve()
        if not path.is_relative_to(ROOT): raise ValueError(f"Unsafe path: {d['path']}")
        raw=path.read_bytes(); text=raw.decode('utf-8')
        d.update(words=len(text.split()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    counts=collections.Counter(d['kind'] for d in obj['documents'])
    obj['counts']=dict(counts)
    obj['counts']['source']=len(obj['sources'])
    obj['unique_document_words']=sum(d['words'] for d in obj['documents'])
    obj['source_capsule_words']=sum(d['words'] for d in obj['sources'])
    summaries={}
    for i in range(40):
        eid=f'E{i:02}'
        evidence_path=EVIDENCE/f'{eid}.json'
        if evidence_path.exists():
            summary=json.loads(evidence_path.read_text(encoding='utf-8'))
            if summary.get('experiment')!=eid: raise ValueError(f'Wrong evidence ID in {evidence_path}')
            summaries[eid]=summary
    for d in obj['documents']:
        if d.get('kind')!='experiment': continue
        eid=d['id']; summary=summaries.get(eid)
        if summary:
            d.setdefault('authoring_status','NOT_RUN_ON_GPU')
            d['status']=summary['status']
            d['evidence']=f"experiments/evidence/v100-20261006/{eid}.json"
    catalog=ROOT/'experiments/experiments.jsonl'
    if catalog.exists():
        lines=[]
        for line in catalog.read_text(encoding='utf-8').splitlines():
            if not line.strip(): continue
            row=json.loads(line)
            summary=summaries.get(row.get('id'))
            if summary:
                row.setdefault('authoring_status',row.get('status','NOT_RUN_ON_GPU'))
                row['status']=summary['status']
                row['evidence']=f"experiments/evidence/v100-20261006/{row['id']}.json"
            lines.append(json.dumps(row,ensure_ascii=False))
        catalog.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    obj.setdefault('global_authoring_evidence',{
        'source_commit':'5c1f805db80a81f7476ede8292abba69821d104f',
        'source_date':'2026-10-03',
        'gpu_measured':False,
        'cuda_compiled':False,
        'statement':'These flags record the original authoring state, not current campaign evidence.',
    })
    testfile=ROOT/'ledger/CPU_TEST_RESULTS.json'
    build_path=ROOT/'benchmark_runs/v100-20261006T145155Z-4bd01216/build.json'
    provenance_path=EVIDENCE/'provenance.json'
    provenance=json.loads(provenance_path.read_text(encoding='utf-8')) if provenance_path.exists() else {}
    build_ok=portable_cuda_compiled(provenance,build_path)
    obj['gpu_measured']=any(x.get('status')=='GPU_RUN' for x in summaries.values())
    obj['cuda_compiled']=build_ok
    obj['validation_status']={
        'gpu_measured':obj['gpu_measured'],
        'cuda_compiled':obj['cuda_compiled'],
        'measured_experiment_count':sum(x.get('status')=='GPU_RUN' for x in summaries.values()),
        'measurement_campaign':'v100-20261006T145155Z-4bd01216' if summaries else None,
        'complete_original_protocols':0,
        'interpretation_guide':'experiments/INTERPRETING_RESULTS.md',
    }
    if testfile.exists():
        test=json.loads(testfile.read_text())
        obj['validation_status']['cpu_semantics']={k:test[k] for k in ['status','assertions'] if k in test}
        obj['validation_status']['cpu_semantics']['test_groups']=len(test.get('groups',[]))
    # An explicit stable ID anchor makes the archival compendium navigable.
    order={'index':0,'reference':1,'mechanism':2,'composition':3,'experiment':4}
    docs=sorted(obj['documents'],key=lambda d:(order.get(d['kind'],9),d['id']))
    evidence_source_commit=None
    if provenance:
        evidence_source_commit=provenance.get('source_commit')
    full=['# V100 / SXM2 Software Circuit-Bending Atlas\n',
          '**Research/synthesis date:** 2026-10-03. **Edition:** 1.0.\n',
          'This is the all-in-one view of original protocols and current evidence. For selective model context, use START_HERE.md, NEED_INDEX.md and tools/read_atlas.py in the ZIP package.\n',
          'The original protocol cards and authoring provenance remain archived at commit `5c1f805db80a81f7476ede8292abba69821d104f`. Current status labels describe only the implemented subset recorded in portable campaign summaries from source commit `'+str(evidence_source_commit)+'`; they do not validate an entire protocol or authorize restricted work.\n',
          '## Contents\n']
    for d in docs: full.append(f"- [{d['id']} — {d['title']}](#{d['id'].lower()})\n")
    for d in docs:
        full += [f"\n---\n\n<a id=\"{d['id'].lower()}\"></a>\n\n",(ROOT/d['path']).read_text(encoding='utf-8')]
    full += ['\n---\n\n# Source capsules\n']
    for s in obj['sources']:
        full += [f"\n<a id=\"{s['id'].lower()}\"></a>\n\n",(ROOT/s['path']).read_text(encoding='utf-8'),'\n']
    for path in ['ledger/CORRECTIONS.md','ledger/OPEN_QUESTIONS.md','ledger/SCOPE.md','ledger/LEGACY_SCOPE.md','ledger/MAINTENANCE.md']:
        full += ['\n---\n\n',(ROOT/path).read_text(encoding='utf-8')]
    if testfile.exists():
        t=json.loads(testfile.read_text())
        full += ['\n---\n\n# Local semantic validation\n',f"\nCPU status: {t.get('status')}. Assertions: {t.get('assertions')}. Test groups: {len(t.get('groups',[]))}.\n",
                 '\nThese validate algebra, encoding and logical coordinate mappings, not actual tensor rounding, memory coherence, generated SASS or performance.\n']
    full += ['\n---\n\n# Current measured subset\n',
             '\nPer-experiment portable summaries in `experiments/evidence/v100-20261006/` are the current checked-in measurement record. Raw campaign artifacts remain local and are linked from each experiment card. Interpret matched comparisons with complete setup and conversion costs; do not infer a general speedup from selected cases. These synthetic and mechanism-level results make no biological claim.\n']
    for path in ['experiments/README.md','experiments/INTERPRETING_RESULTS.md','experiments/CLAIM_LIMITS.md']:
        doc=ROOT/path
        if doc.exists(): full += ['\n---\n\n',doc.read_text(encoding='utf-8')]
    text='\n'.join(full)
    (ROOT/'V100_ATLAS_FULL.md').write_text(text,encoding='utf-8')
    obj['compendium']={'path':'V100_ATLAS_FULL.md','words':len(text.split()),'sha256':hashlib.sha256(text.encode()).hexdigest()}
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'counts':obj['counts'],'unique_document_words':obj['unique_document_words'],'full_words':obj['compendium']['words']}))
if __name__=='__main__':main()
