"""Application titles are optional display metadata, not identity or CV content."""

import pytest

from core.models import TailoredCV
from core.pipeline import _build_prompt, _build_system_prompt_for_chat, _build_user_prompt


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  cplace  -  Senior DevOps Engineer\n", "cplace - Senior DevOps Engineer"),
        (None, None),
        ("", None),
        ("just a company", None),
        ("Company - ", None),
        (" - Role", None),
        ({"company": "Company"}, None),
        ("Company - " + "a" * 201, None),
    ],
)
def test_application_title_normalization(minimal_tailored_cv, raw, expected):
    data = minimal_tailored_cv.model_dump()
    data["application_title"] = raw
    assert TailoredCV.model_validate(data).application_title == expected


def test_legacy_cv_without_title_still_loads(minimal_tailored_cv):
    data = minimal_tailored_cv.model_dump()
    data.pop("application_title", None)
    assert TailoredCV.model_validate(data).application_title is None


def test_cli_and_chat_request_grounded_application_title(base_cv):
    listing = "cplace is hiring a Senior DevOps Engineer."
    cli = _build_prompt(base_cv, listing)
    chat = _build_system_prompt_for_chat() + _build_user_prompt(base_cv, listing)
    for prompt in (cli, chat):
        assert '"application_title"' in prompt
        assert '"Company Name - Job Title"' in prompt
        assert "JOB LISTING only" in prompt
        assert "return null rather than inventing it" in prompt
