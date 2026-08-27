from pathlib import Path

import yaml


RELEASE_WORKFLOW = Path('.github/workflows/release.yml')
WINDOWS_SIGN_SCRIPT = Path('scripts/sign-windows.ps1')


def _workflow_text() -> str:
    return RELEASE_WORKFLOW.read_text(encoding='utf-8')


def test_release_workflow_is_valid_yaml():
    parsed = yaml.safe_load(_workflow_text())
    assert isinstance(parsed, dict)
    assert 'jobs' in parsed


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
    assert 'needs: [validate, security-audit, social-sdk-toolchain]' in text


def test_release_requires_pinned_social_sdk_toolchain():
    text = _workflow_text()
    assert 'SOCIAL_SDK_VERSION: "1.10.18687"' in text
    assert 'SOCIAL_SDK_TOOLCHAIN_RELEASE: "social-sdk-toolchain-1.10.18687"' in text
    assert 'SOCIAL_SDK_TOOLCHAIN_ASSET: "CYBREX-DiscordSocialSdk-1.10.18687-toolchain.zip"' in text
    assert 'SOCIAL_SDK_TOOLCHAIN_SHA256: "252d26b273887fb235691a40118d786b765539e86c7656f24ad44680bf549232"' in text
    assert 'gh release download "${SOCIAL_SDK_TOOLCHAIN_RELEASE}"' in text
    assert 'CYBREX_SOCIAL_SDK_BUNDLE_DIR' in text
    assert 'Build Windows executable with Social SDK' in text
    assert 'Build Linux executable with Social SDK' in text
    assert 'Verify Social SDK is embedded in Windows executable' in text
    assert 'Verify Social SDK is embedded in Linux executable' in text
    assert 'discord_social_sdk_embedded=true' in text


def test_release_publishes_checksums_and_provenance():
    text = _workflow_text()
    assert 'SHA256SUMS.txt' in text
    assert 'BUILD-PROVENANCE.txt' in text
    assert 'windows_authenticode=${WINDOWS_SIGNED}' in text
    assert 'discord_social_sdk=${SOCIAL_SDK_VERSION}' in text
    assert 'discord_social_sdk_toolchain_sha256=${SOCIAL_SDK_TOOLCHAIN_SHA256}' in text


def test_release_critical_actions_are_commit_pinned():
    text = _workflow_text()
    assert 'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1' in text
    assert 'actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97' in text
    assert 'actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a' in text
    assert 'actions/download-artifact@37930b1c2abaa49bbe596cd826c3c89aef350131' in text
    assert 'actions/checkout@v' not in text
    assert 'actions/setup-python@v' not in text
    assert 'actions/upload-artifact@v' not in text
    assert 'actions/download-artifact@v' not in text


def test_windows_signing_verifies_both_inner_exe_and_installer():
    workflow = _workflow_text()
    script = WINDOWS_SIGN_SCRIPT.read_text(encoding='utf-8')
    assert './scripts/sign-windows.ps1 -Path "dist/DiscordRichPresence.exe"' in workflow
    assert './scripts/sign-windows.ps1 -Path "dist/CYBREX-Presence-Setup.exe"' in workflow
    assert 'Get-AuthenticodeSignature' in script
    assert "https://timestamp.digicert.com" in script
    assert "signature.Status -ne 'Valid'" in script
