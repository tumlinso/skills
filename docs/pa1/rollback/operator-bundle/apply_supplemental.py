"""Inert, exact-path operator for PA1 consumer and evidence installation."""
from __future__ import annotations
import argparse, hashlib, json, os, stat, sys, tempfile
from pathlib import Path, PurePosixPath

STAGE=Path(__file__).resolve().parent
MANIFEST=STAGE/'supplemental-transition.json'
class Refuse(RuntimeError): pass

def digest(raw): return hashlib.sha256(raw).hexdigest()
def safe(rel):
    p=PurePosixPath(rel)
    if p.is_absolute() or '..' in p.parts or not rel or str(p)!=rel: raise Refuse('unsafe_path:'+rel)
    return rel
def target(root,rel):
    cur=root
    for part in PurePosixPath(safe(rel)).parts:
        cur=cur/part
        if cur.is_symlink(): raise Refuse('symlink_component:'+rel)
    if root not in cur.parents and cur!=root: raise Refuse('path_escape:'+rel)
    return cur
def load():
    m=json.loads(MANIFEST.read_text());
    if m.get('format')!='pa1-skills-supplemental-transition/1': raise Refuse('manifest_format')
    root=Path(m['source_root']).resolve(strict=True)
    return m,root
def verify_stage(m):
    listed=m['operator_bundle']['files']; bundle=STAGE/'operator-bundle'
    actual={p.relative_to(bundle).as_posix() for p in bundle.rglob('*') if p.is_file()}
    if any(p.is_symlink() for p in bundle.rglob('*')) or actual!=set(listed): raise Refuse('operator_bundle_file_set_mismatch')
    for rel,entry in listed.items():
        p=target(bundle,rel); raw=p.read_bytes()
        if digest(raw)!=entry['sha256'] or len(raw)!=entry['bytes'] or stat.S_IMODE(p.stat().st_mode)!=int(entry['mode'],8): raise Refuse('operator_bundle_identity:'+rel)

def primary_state(m,root):
    rollback=root/'docs/pa1/rollback'
    if not rollback.exists():
        if rollback.is_symlink(): raise Refuse('primary_rollback_path_symlink')
        return 'primary_ready'
    if rollback.is_symlink() or not rollback.is_dir(): raise Refuse('primary_rollback_path_invalid')
    for rel,src in [('local-coding-worker-portable.tar.gz',STAGE/'rollback/local-coding-worker-portable.tar.gz'),('provenance.json',STAGE/'rollback/provenance.json'),('runtime-transition.json',STAGE/'runtime-transition.json')]:
        p=target(rollback,rel)
        if not p.is_file() or digest(p.read_bytes())!=digest(src.read_bytes()): raise Refuse('primary_rollback_evidence_mismatch:'+rel)
    transition=json.loads((STAGE/'runtime-transition.json').read_text())
    skill=root/'local-coding-worker'
    for rel in transition['add']+transition['replace']:
        p=target(skill,rel.removeprefix('local-coding-worker/'))
        if not p.is_file() or digest(p.read_bytes())!=transition['candidate_hashes'][rel]: raise Refuse('primary_candidate_missing_or_drifted:'+rel)
    for rel in transition['remove']:
        p=target(skill,rel.removeprefix('local-coding-worker/'))
        if p.exists() or p.is_symlink(): raise Refuse('primary_removed_path_reappeared:'+rel)
    return 'primary_applied'

def preflight():
    m,root=load(); verify_stage(m)
    applied_state=primary_state(m,root)
    for rel,entry in m['replace'].items():
        p=target(root,rel)
        if not p.is_file() or digest(p.read_bytes())!=entry['source_sha256'] or stat.S_IMODE(p.stat().st_mode)!=int(entry['source_mode'],8): raise Refuse('consumer_source_drift:'+rel)
        s=target(STAGE,entry['staged_path'])
        if not s.is_file() or digest(s.read_bytes())!=entry['candidate_sha256'] or stat.S_IMODE(s.stat().st_mode)!=int(entry['candidate_mode'],8): raise Refuse('consumer_candidate_drift:'+rel)
    for rel,entry in m['add'].items():
        p=target(root,rel)
        if p.exists() or p.is_symlink(): raise Refuse('add_target_exists:'+rel)
        s=target(STAGE,entry['staged_path'])
        if not s.is_file() or digest(s.read_bytes())!=entry['sha256'] or stat.S_IMODE(s.stat().st_mode)!=int(entry['mode'],8): raise Refuse('staged_add_identity:'+rel)
        if not p.parent.is_dir():
            # Ancestor may be an explicitly declared directory created by this operator.
            parent_rel=p.parent.relative_to(root).as_posix()
            if parent_rel not in m['create_directories']: raise Refuse('add_parent_missing:'+rel)
    bundle_target=target(root,m['operator_bundle']['target'])
    if bundle_target.exists() or bundle_target.is_symlink(): raise Refuse('operator_bundle_target_exists')
    for rel in m['create_directories']:
        p=target(root,rel)
        if p.exists() and (not p.is_dir() or p.is_symlink()): raise Refuse('directory_conflict:'+rel)
    return m,root,applied_state

def atomic_copy(src,dst,mode):
    fd,name=tempfile.mkstemp(prefix='.'+dst.name+'.pa1-',dir=dst.parent); tmp=Path(name)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(src.read_bytes()); stream.flush(); os.fsync(stream.fileno())
        tmp.chmod(mode); os.replace(tmp,dst)
    except BaseException:
        tmp.unlink(missing_ok=True); raise

def apply():
    m,root,applied_state=preflight()
    if applied_state!='primary_applied': raise Refuse('primary_transition_must_be_applied_first')
    # No target is opened until the complete source/candidate/addition batch passed.
    # The operator bundle is created separately below with exist_ok=False; skip
    # it here even if an older manifest lists it among generic directories.
    bundle_rel=m['operator_bundle']['target']
    for rel in m['create_directories']:
        if rel == bundle_rel: continue
        target(root,rel).mkdir(parents=True,exist_ok=True)
    bundle_target=target(root,bundle_rel)
    bundle_target.mkdir(parents=True,exist_ok=False)
    for rel,entry in m['add'].items(): target(root,rel).parent.mkdir(parents=True,exist_ok=True)
    for rel,entry in m['replace'].items():
        dst=target(root,rel)
        if digest(dst.read_bytes())!=entry['source_sha256']: raise Refuse('consumer_changed_after_preflight:'+rel)
        atomic_copy(target(STAGE,entry['staged_path']),dst,int(entry['candidate_mode'],8))
        if digest(dst.read_bytes())!=entry['candidate_sha256']: raise Refuse('consumer_copy_verify:'+rel)
    for rel,entry in m['add'].items():
        dst=target(root,rel)
        if dst.exists() or dst.is_symlink(): raise Refuse('addition_changed_after_preflight:'+rel)
        atomic_copy(target(STAGE,entry['staged_path']),dst,int(entry['mode'],8))
        if digest(dst.read_bytes())!=entry['sha256']: raise Refuse('addition_copy_verify:'+rel)
    for rel,entry in m['operator_bundle']['files'].items():
        dst=target(root,m['operator_bundle']['target']+'/'+rel)
        dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists() or dst.is_symlink(): raise Refuse('operator_bundle_file_exists:'+rel)
        atomic_copy(target(STAGE/'operator-bundle',rel),dst,int(entry['mode'],8))
        if digest(dst.read_bytes())!=entry['sha256']: raise Refuse('operator_bundle_copy_verify:'+rel)
    print(f'SUPPLEMENTAL_APPLIED replacements={len(m["replace"])} additions={len(m["add"])} bundle_files={len(m["operator_bundle"]["files"])}')

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('operation',choices=['preflight','apply']); a=p.parse_args()
    try:
        m,root,applied_state=preflight()
        if a.operation=='preflight': print(f'SUPPLEMENTAL_PREFLIGHT_OK primary_state={applied_state} replacements={len(m["replace"])} additions={len(m["add"])} bundle_files={len(m["operator_bundle"]["files"])} source_root={root} no_source_mutation=true')
        else: apply()
    except (Refuse,OSError,ValueError,KeyError) as e: print(f'Supplemental transition refused: {e}',file=sys.stderr); return 2
    return 0
if __name__=='__main__': raise SystemExit(main())
