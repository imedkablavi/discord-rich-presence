from pathlib import Path


RELEASE_WORKFLOW = Path('.github/workflows/release.yml')


def _workflow_text() -> str:
    return RELEASE_WORKFLOW.read_text(encoding='utf-8')


def test_prerelease_tags_are_published_as_github_prereleases():
    text = _workflow_text()
    assert 'if [[ "${GITHUB_REF_NAME}" == *-* ]]; then' in text
    assert 'release_flags+=(--prerelease)' in text
    assert '"${release_flags[@]}"' in text


def test_stable_windows_release_is_blocked_without_signing():
    text = _workflow_text()
    assert 'Block unsigned stable Windows releases' in text
    assert "!contains(github.ref_name, '-')" in text
    assert "steps.signing.outputs.enabled != 'true'" in text
    assert 'Stable Windows releases must be code-signed' in text


def test_tagged_release_runs_regressions_before_packaging():
    text = _workflow_text()
    assert 'name: Run regression suite' in text
    assert 'python -m pytest -q' in text
    assert 'needs: [validate, security-audit]' in text


def test_release_publishes_checksums_and_provenance():
    text = _workflow_text()
    assert 'SHA256SUMS.txt' in text
    assert 'BUILD-PROVENANCE.txt' in text
    assert 'windows_authenticode=${WINDOWS_SIGNED}' in text
