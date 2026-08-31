from pathlib import Path

import yaml


RELEASE_WORKFLOW = Path('.github/workflows/release.yml')
GAMER_COMPANIONS_WORKFLOW = Path('.github/workflows/release-gamer-companions.yml')
WINDOWS_SIGN_SCRIPT = Path('scripts/sign-windows.ps1')


def _workflow_text() -> str:
    return RELEASE_WORKFLOW.read_text(encoding='utf-8')


def test_release_workflow_is_valid_yaml():
    parsed = yaml.safe_load(_workflow_text())
    assert isinstance(parsed, dict)
    assert 'jobs' in parsed


def test_prerelease_tags_are_published_as_github_prereleases():
    text = _workflow_text()
    assert 'if [[ "${RELEASE_TAG}" == *-* ]]; then' in text
    assert 'release_flags+=(--prerelease)' in text
    assert '"${release_flags[@]}"' in text


def test_stable_windows_release_is_blocked_without_signing():
    text = _workflow_text()
    assert 'Block unsigned stable Windows releases' in text
    assert "!contains(env.RELEASE_TAG, '-')" in text
    assert "steps.signing.outputs.enabled != 'true'" in text
    assert 'Stable Windows releases must be code-signed' in text


def test_tagged_release_runs_regressions_before_packaging():
    text = _workflow_text()
    assert 'name: Run regression suite' in text
    assert 'python -m pytest -q' in text
    assert 'needs: [validate, security-audit, social-sdk-toolchain]' in text


def test_release_version_is_verified_in_validation_and_platform_builds():
    text = _workflow_text()
    assert text.count('name: Verify stamped release version') == 3
    assert "app_version.APP_VERSION == expected" in text


def test_windows_release_stamp_uses_powershell_environment_syntax():
    text = _workflow_text()
    windows_job = text.split('  windows:', 1)[1].split('  linux:', 1)[0]
    assert 'python scripts/write-version.py "$env:RELEASE_TAG"' in windows_job
    assert 'python scripts/write-version.py "${RELEASE_TAG}"' not in windows_job


def test_release_uses_curated_public_notes_instead_of_internal_commit_titles():
    text = _workflow_text()
    assert '--notes-file .github/RELEASE_NOTES.md' in text
    assert '--generate-notes' not in text
    assert Path('.github/RELEASE_NOTES.md').is_file()


def test_release_requires_pinned_social_sdk_toolchain():
    text = _workflow_text()
    assert 'SOCIAL_SDK_VERSION: "1.10.18687"' in text
    assert 'SOCIAL_SDK_TOOLCHAIN_ASSET_ID: "532548383"' in text
    assert 'SOCIAL_SDK_TOOLCHAIN_ASSET: "CYBREX-DiscordSocialSdk-1.10.18687-toolchain.zip"' in text
    assert 'SOCIAL_SDK_TOOLCHAIN_SHA256: "252d26b273887fb235691a40118d786b765539e86c7656f24ad44680bf549232"' in text
    download_step = text.split('name: Download pinned private Discord Social SDK toolchain', 1)[1].split(
        'name: Verify pinned Discord Social SDK toolchain', 1
    )[0]
    assert 'GH_TOKEN: ${{ secrets.SOCIAL_SDK_ASSET_TOKEN }}' in download_step
    assert 'GH_TOKEN: ${{ github.token }}' not in download_step
    assert 'SOCIAL_SDK_ASSET_TOKEN is required' in download_step
    assert 'releases/assets/${SOCIAL_SDK_TOOLCHAIN_ASSET_ID}' in text
    assert 'Accept: application/octet-stream' in text
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
    assert 'actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c' in text
    assert 'actions/checkout@v' not in text
    assert 'actions/setup-python@v' not in text
    assert 'actions/upload-artifact@v' not in text
    assert 'actions/download-artifact@v' not in text


def test_manual_release_rebuilds_an_existing_immutable_tag():
    text = _workflow_text()
    assert 'release_tag:' in text
    assert 'RELEASE_TAG: ${{ inputs.release_tag || github.ref_name }}' in text
    assert 'ref: ${{ env.RELEASE_TAG }}' in text
    assert 'sha=$(git rev-parse HEAD)' in text


def test_gamer_companion_release_commands_are_repository_scoped():
    text = GAMER_COMPANIONS_WORKFLOW.read_text(encoding='utf-8')
    assert 'gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY"' in text
    assert '--repo "$GITHUB_REPOSITORY" \\' in text


def test_windows_signing_verifies_both_inner_exe_and_installer():
    workflow = _workflow_text()
    script = WINDOWS_SIGN_SCRIPT.read_text(encoding='utf-8')
    assert './scripts/sign-windows.ps1 -Path "dist/DiscordRichPresence.exe"' in workflow
    assert './scripts/sign-windows.ps1 -Path "dist/CYBREX-Presence-Setup.exe"' in workflow
    assert 'Get-AuthenticodeSignature' in script
    assert "https://timestamp.digicert.com" in script
    assert "signature.Status -ne 'Valid'" in script
