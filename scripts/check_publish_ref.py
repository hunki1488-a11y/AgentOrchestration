#!/usr/bin/env python3
"""Validate that a package publish job is running from a trusted Git ref."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence


RELEASE_TAG_RE = re.compile(r"^v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
TRUTHY = {"1", "true", "yes", "on"}


class PublishRefError(ValueError):
    """Raised when the GitHub ref is not safe for package publishing."""


@dataclass(frozen=True)
class PublishRefContext:
    ref: str
    ref_type: str
    ref_name: str
    ref_protected: bool


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in TRUTHY


def context_from_env(env: Mapping[str, str]) -> PublishRefContext:
    """Build context only from GitHub-provided ref variables.

    Workflow dispatch inputs are ignored so callers cannot point manual runs at
    unreviewed refs while pretending they are release branches.
    """

    ref = env.get("GITHUB_REF", "")
    ref_type = env.get("GITHUB_REF_TYPE", "")
    ref_name = env.get("GITHUB_REF_NAME", "")

    if not ref_name and ref.startswith("refs/heads/"):
        ref_name = ref.removeprefix("refs/heads/")
    elif not ref_name and ref.startswith("refs/tags/"):
        ref_name = ref.removeprefix("refs/tags/")

    return PublishRefContext(
        ref=ref,
        ref_type=ref_type,
        ref_name=ref_name,
        ref_protected=_truthy(env.get("GITHUB_REF_PROTECTED")),
    )


def verify_signed_tag(
    tag_name: str,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> bool:
    result = runner(
        ["git", "tag", "-v", tag_name],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.returncode == 0


def validate_publish_ref(
    context: PublishRefContext,
    tag_verifier: Callable[[str], bool] = verify_signed_tag,
) -> str:
    if context.ref_type == "branch":
        if not context.ref_protected:
            raise PublishRefError(
                "package publish blocked: branch ref is not protected"
            )
        return f"protected branch accepted: {context.ref_name}"

    if context.ref_type == "tag":
        if not RELEASE_TAG_RE.match(context.ref_name):
            raise PublishRefError(
                "package publish blocked: tag is not a release tag"
            )
        if not tag_verifier(context.ref_name):
            raise PublishRefError(
                "package publish blocked: release tag is not signed "
                "or cannot be verified"
            )
        return f"signed release tag accepted: {context.ref_name}"

    raise PublishRefError(
        f"package publish blocked: unsupported ref type {context.ref_type!r}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-tag-signature-check",
        action="store_true",
        help="Only for local dry-runs; never use in registry publish jobs.",
    )
    args = parser.parse_args(argv)

    context = context_from_env(os.environ)
    verifier = (
        (lambda _tag: True)
        if args.skip_tag_signature_check
        else verify_signed_tag
    )

    try:
        message = validate_publish_ref(context, verifier)
    except PublishRefError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
