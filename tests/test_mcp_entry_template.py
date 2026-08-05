"""mcp-entry-template.json is the exact shape skills/setup/SKILL.md tells Claude to fill in
(step 4). It must stay valid JSON with the fields setup's prose promises."""

import json

from conftest import SKILLS_DIR

TEMPLATE_PATH = SKILLS_DIR / "setup" / "mcp-entry-template.json"


def test_template_is_valid_json():
    json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def test_template_iadc_block_has_expected_shape():
    data = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    iadc = data["iadc"]
    assert iadc["type"] == "http"
    assert "url" in iadc
    assert "appian-api-key" in iadc["headers"]
