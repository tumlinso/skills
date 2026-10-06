"""Guarded restoration for PA1 supplemental consumer and evidence files."""
from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path, PurePosixPath

HERE=Path(__file__).resolve().parent
MAP=HERE/'consumer-restore-manifest.json'
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
 return cur
def restore():
 m=json.loads(MAP.read_text())
 if m.get('format')!='pa1-skills-supplemental-transition/1': raise Refuse('manifest_format')
 root=Path(m['source_root']).resolve(strict=True)
 bundle=HERE
 # Verify every consumer preimage bundled before changing any consumer target.
 for rel,entry in m['replace'].items():
  p=target(root,rel)
  if not p.is_file() or digest(p.read_bytes())!=entry['candidate_sha256']: raise Refuse('restore_candidate_drift:'+rel)
  backup=target(bundle,'rollback-preimages/'+rel)
  if not backup.is_file() or digest(backup.read_bytes())!=entry['source_sha256']: raise Refuse('restore_preimage_invalid:'+rel)
 for rel,entry in m['add'].items():
  p=target(root,rel)
  if not p.is_file() or digest(p.read_bytes())!=entry['sha256']: raise Refuse('restore_addition_drift:'+rel)
 # All preconditions have passed; atomically restore original consumers.
 for rel,entry in m['replace'].items():
  dst=target(root,rel); src=target(bundle,'rollback-preimages/'+rel)
  fd,name=tempfile.mkstemp(prefix='.'+dst.name+'.pa1-restore-',dir=dst.parent); tmp=Path(name)
  try:
   with os.fdopen(fd,'wb') as stream: stream.write(src.read_bytes()); stream.flush(); os.fsync(stream.fileno())
   tmp.chmod(int(entry['source_mode'],8)); os.replace(tmp,dst)
  except BaseException: tmp.unlink(missing_ok=True); raise
  if digest(dst.read_bytes())!=entry['source_sha256']: raise Refuse('restore_verify:'+rel)
 # Remove only exact staged additions, deepest files first; leave created directories for audit.
 for rel,entry in sorted(m['add'].items(),key=lambda item:len(PurePosixPath(item[0]).parts),reverse=True):
  p=target(root,rel)
  if digest(p.read_bytes())!=entry['sha256']: raise Refuse('addition_changed_during_restore:'+rel)
  p.unlink()
 print(f'SUPPLEMENTAL_RESTORED replacements={len(m["replace"])} additions_removed={len(m["add"])}')
def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument('operation',choices=['restore']); p.parse_args()
 try: restore()
 except (Refuse,OSError,ValueError,KeyError) as e: print(f'Supplemental rollback refused: {e}',file=sys.stderr); return 2
 return 0
if __name__=='__main__': raise SystemExit(main())
