import importlib.util
import pathlib
import subprocess
import sys


SCRIPT = (
    pathlib.Path(__file__).resolve().parents[1]
    / "scripts"
    / "check_publish_ref.py"
)
SPEC = importlib.util.spec_from_file_location("check_publish_ref", SCRIPT)
guard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = guard
SPEC.loader.exec_module(guard)


def test_accepts_protected_branch():
    context = guard.context_from_env(
        {
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_REF_TYPE": "branch",
            "GITHUB_REF_PROTECTED": "true",
        }
    )

    assert (
        guard.validate_publish_ref(context)
        == "protected branch accepted: main"
    )


def test_rejects_unprotected_branch():
    context = guard.context_from_env(
        {
            "GITHUB_REF": "refs/heads/feature/unreviewed",
            "GITHUB_REF_TYPE": "branch",
            "GITHUB_REF_PROTECTED": "false",
        }
    )

    try:
        guard.validate_publish_ref(context)
    except guard.PublishRefError as exc:
        assert "branch ref is not protected" in str(exc)
    else:
        raise AssertionError("unprotected branch was accepted")


def test_manual_dispatch_input_cannot_override_github_ref():
    context = guard.context_from_env(
        {
            "GITHUB_REF": "refs/heads/feature/unreviewed",
            "GITHUB_REF_TYPE": "branch",
            "GITHUB_REF_PROTECTED": "false",
            "INPUT_REF": "refs/heads/main",
        }
    )

    assert context.ref_name == "feature/unreviewed"
    try:
        guard.validate_publish_ref(context)
    except guard.PublishRefError as exc:
        assert "not protected" in str(exc)
    else:
        raise AssertionError("manual input overrode the GitHub ref")


def test_accepts_signed_release_tag():
    context = guard.context_from_env(
        {
            "GITHUB_REF": "refs/tags/v2.4.2",
            "GITHUB_REF_TYPE": "tag",
        }
    )

    assert (
        guard.validate_publish_ref(
            context,
            tag_verifier=lambda tag: tag == "v2.4.2",
        )
        == "signed release tag accepted: v2.4.2"
    )


def test_rejects_unsigned_release_tag():
    context = guard.context_from_env(
        {
            "GITHUB_REF": "refs/tags/v2.4.2",
            "GITHUB_REF_TYPE": "tag",
        }
    )

    try:
        guard.validate_publish_ref(context, tag_verifier=lambda _tag: False)
    except guard.PublishRefError as exc:
        assert "not signed" in str(exc)
    else:
        raise AssertionError("unsigned release tag was accepted")


def test_rejects_non_release_tag_before_signature_check():
    checked = []
    context = guard.context_from_env(
        {
            "GITHUB_REF": "refs/tags/latest",
            "GITHUB_REF_TYPE": "tag",
        }
    )

    try:
        guard.validate_publish_ref(
            context,
            tag_verifier=lambda tag: checked.append(tag),
        )
    except guard.PublishRefError as exc:
        assert "not a release tag" in str(exc)
        assert checked == []
    else:
        raise AssertionError("non-release tag was accepted")


def test_verify_signed_tag_uses_git_tag_verification():
    calls = []

    def fake_runner(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout="Good signature")

    assert guard.verify_signed_tag("v2.4.2", runner=fake_runner)
    assert calls[0][0] == ["git", "tag", "-v", "v2.4.2"]
