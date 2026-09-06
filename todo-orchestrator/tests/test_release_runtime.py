import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from todo_orchestrator import runtime_identity as runtime

class ReleaseRuntimeTests(unittest.TestCase):
    def test_installed_runtime_requires_exact_pinned_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);skills=root/'skills';source=skills/'todo-orchestrator/todo_orchestrator';installed=root/'installed/todo_orchestrator'
            for package in (source,installed):
                package.mkdir(parents=True)
                (package/'__init__.py').write_text('VALUE=1\n')
                (package/'runtime_identity.py').write_text('# identity fixture\n')
            digest=hashlib.sha256()
            for path in sorted(source.rglob('*.py')):
                digest.update(path.relative_to(source).as_posix().encode()+b'\0'+path.read_bytes()+b'\0')
            manifest=root/'release.json';manifest.write_text(json.dumps({'schema_version':2,'skills_root':str(skills),'todo_runtime_fingerprint':digest.hexdigest()}))
            environment={'PROJECT_CONTROL_RELEASE_MANIFEST':str(manifest),'PROJECT_CONTROL_RELEASE_DIGEST':hashlib.sha256(manifest.read_bytes()).hexdigest()}
            with patch.object(runtime,'__file__',str(installed/'runtime_identity.py')),patch.dict(os.environ,environment,clear=True):
                identity=runtime._candidate_identity(skills)
                self.assertEqual(identity.package_root,installed)
                (installed/'__init__.py').write_text('VALUE=2\n')
                with self.assertRaises(runtime.RuntimeIdentityError):runtime._candidate_identity(skills)
                (installed/'__init__.py').write_text('VALUE=1\n')
                os.environ.pop('PROJECT_CONTROL_RELEASE_DIGEST')
                with self.assertRaises(runtime.RuntimeIdentityError):runtime._candidate_identity(skills)
                os.environ.clear()
                with self.assertRaises(runtime.RuntimeIdentityError):runtime._candidate_identity(skills)
