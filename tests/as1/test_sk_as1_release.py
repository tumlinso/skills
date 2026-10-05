"""Strict consumer of the controller's actual paired release; no activation."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('skills_as1_release', ROOT / 'integrations/as1_release.py')
CONSUMER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONSUMER)


def manifest():
    return json.loads(CONSUMER.DEFAULT.read_text())


@pytest.mark.as1_case('PIN-01')
def test_qualified_standalone_pair_is_pinned_to_actual_release():
    assert CONSUMER.validate_release(manifest())['status'] == 'passed'


@pytest.mark.as1_case('PIN-02')
def test_bound_native_installation_and_actual_rollback_preserve_queued_state_and_projects():
    assert CONSUMER.validate_release(manifest())['cases'] == ['PIN-01', 'PIN-02']


def test_consumer_candidate_identity_is_exact_and_read_only():
    before = CONSUMER.sha(CONSUMER.DEFAULT)
    release = manifest()
    candidate = CONSUMER.validate_identity(release)
    assert candidate.name == 'as1-paired-6d1a732-269646d-20261004'
    assert CONSUMER.sha(CONSUMER.DEFAULT) == before


def test_consumer_refuses_pending_release():
    release = manifest()
    release['status'] = 'pending'
    with pytest.raises(AssertionError, match='pending actual qualification'):
        CONSUMER.validate_release(release)


def test_consumer_refuses_changed_candidate_manifest():
    release = manifest()
    release['candidate']['manifest_sha256'] = '0' * 64
    with pytest.raises(AssertionError):
        CONSUMER.validate_identity(release)


def test_consumer_refuses_missing_or_changed_proof(tmp_path):
    missing = tmp_path / 'missing.json'
    with pytest.raises(FileNotFoundError):
        CONSUMER.read_bound({'path': str(missing), 'sha256': '0' * 64})
    missing.write_text('{}')
    with pytest.raises(AssertionError, match='Unbound or changed artifact'):
        CONSUMER.read_bound({'path': str(missing), 'sha256': '0' * 64})


def test_consumer_refuses_failed_or_absent_qualification():
    with pytest.raises(AssertionError, match='Qualification failed'):
        CONSUMER.passing_cases({'pytest_exitstatus': 1}, {'SQA-01'})
    with pytest.raises(KeyError):
        CONSUMER.passing_cases({'pytest_exitstatus': 0, 'cases': {}}, {'SQA-01'})
    with pytest.raises(AssertionError, match='SQA-01'):
        CONSUMER.passing_cases({'pytest_exitstatus': 0, 'cases': {'SQA-01': [{'outcome': 'failed'}]}}, {'SQA-01'})
