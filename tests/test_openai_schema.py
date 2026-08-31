"""Step 5B.2 — OpenAI strict structured-output schema fix.

Live-confirmed in Step 5B.1: OpenAI's strict mode
(response_format: {"type": "json_schema", ..., "strict": True}) rejects a
schema with HTTP 400 ("'additionalProperties' is required to be supplied
and to be false") unless every object node explicitly sets it.
Pydantic's model_json_schema() doesn't add this by default.

WorksheetResponse.model_json_schema() stays the single source of truth --
this only post-processes a copy of its output, applied only at the
OpenAI provider boundary. No live API call in this file.
"""
import copy
import inspect
import json
from unittest.mock import MagicMock

from src.config import Settings
from src.models.ai_schemas import WorksheetResponse
from src.services.ai_providers import gemini_provider
from src.services.ai_providers.openai_provider import (
    _WORKSHEET_JSON_SCHEMA,
    OpenAIProvider,
    _with_additional_properties_false,
)


def _all_object_nodes(schema):
    """Yield every dict node in the schema tree that represents a JSON
    Schema object (has type=="object" or a "properties" key)."""
    if isinstance(schema, dict):
        if schema.get("type") == "object" or "properties" in schema:
            yield schema
        for value in schema.values():
            yield from _all_object_nodes(value)
    elif isinstance(schema, list):
        for item in schema:
            yield from _all_object_nodes(item)


def _settings(**overrides) -> Settings:
    values = dict(
        gemini_api_key="gemini-test-key",
        gemini_model="gemini-test",
        google_cloud_project="proj",
        firebase_project_id="proj",
        firebase_web_api_key="web-key",
        port=8080,
        openai_api_key="openai-test-key",
        openai_model="gpt-4o-mini",
    )
    values.update(overrides)
    return Settings(**values)


# --- A. root object -------------------------------------------------------------


def test_root_schema_has_additional_properties_false():
    schema = _WORKSHEET_JSON_SCHEMA["schema"]
    assert schema["additionalProperties"] is False


# --- B. every nested object -------------------------------------------------------


def test_every_object_node_has_additional_properties_false():
    schema = _WORKSHEET_JSON_SCHEMA["schema"]
    object_nodes = list(_all_object_nodes(schema))
    assert len(object_nodes) >= 2  # root WorksheetResponse + nested GeneratedQuestion
    for node in object_nodes:
        assert node.get("additionalProperties") is False


def test_nested_defs_entry_has_additional_properties_false():
    schema = _WORKSHEET_JSON_SCHEMA["schema"]
    assert schema["$defs"]["GeneratedQuestion"]["additionalProperties"] is False


# --- C. existing constraints preserved --------------------------------------------


def test_existing_constraints_are_preserved():
    schema = _WORKSHEET_JSON_SCHEMA["schema"]

    assert schema["required"] == ["title", "objective", "difficulty", "questions"]
    assert schema["properties"]["title"]["minLength"] == 1
    assert schema["properties"]["objective"]["minLength"] == 1
    assert schema["properties"]["difficulty"]["enum"] == ["easy", "medium", "hard"]
    assert schema["properties"]["questions"]["minItems"] == 1
    assert schema["properties"]["questions"]["maxItems"] == 10

    question_schema = schema["$defs"]["GeneratedQuestion"]
    assert question_schema["required"] == [
        "id",
        "prompt",
        "options",
        "correct_answer_index",
        "concept",
    ]
    assert question_schema["properties"]["options"]["minItems"] == 2
    assert question_schema["properties"]["options"]["maxItems"] == 6
    assert question_schema["properties"]["correct_answer_index"]["minimum"] == 0
    assert question_schema["properties"]["prompt"]["minLength"] == 1
    assert question_schema["properties"]["concept"]["minLength"] == 1


# --- D. no mutation of the original ------------------------------------------------


def test_transform_does_not_mutate_its_input():
    original = WorksheetResponse.model_json_schema()
    snapshot = copy.deepcopy(original)

    _with_additional_properties_false(original)

    assert original == snapshot
    assert "additionalProperties" not in original


def test_transform_returns_a_distinct_object_from_its_input():
    original = {"type": "object", "properties": {}}

    result = _with_additional_properties_false(original)

    assert result is not original
    assert result["additionalProperties"] is False
    assert "additionalProperties" not in original


# --- E. existing OpenAI provider behavior unchanged apart from schema --------------


def test_generate_worksheet_still_succeeds_and_sends_the_transformed_schema(monkeypatch):
    valid_payload = json.dumps(
        {
            "title": "T",
            "objective": "O",
            "difficulty": "easy",
            "questions": [
                {
                    "id": "1",
                    "prompt": "P",
                    "options": ["a", "b"],
                    "correct_answer_index": 0,
                    "concept": "c",
                }
            ],
        }
    )
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=valid_payload))]
    )
    monkeypatch.setattr(OpenAIProvider, "_client", lambda self: client)

    provider = OpenAIProvider(_settings())
    result = provider.generate_worksheet("prompt", "safety instruction")

    assert result.title == "T"  # unchanged success behavior
    assert client.chat.completions.create.call_count == 1  # unchanged call count

    _, kwargs = client.chat.completions.create.call_args
    sent_schema = kwargs["response_format"]["json_schema"]["schema"]
    assert sent_schema["additionalProperties"] is False
    assert sent_schema["$defs"]["GeneratedQuestion"]["additionalProperties"] is False


# --- F. Gemini untouched -----------------------------------------------------------


def test_gemini_provider_module_is_not_touched_by_this_fix():
    source = inspect.getsource(gemini_provider)
    assert "_with_additional_properties_false" not in source
    assert "additionalProperties" not in source


# --- G. no secret leakage -----------------------------------------------------------


def test_schema_payload_contains_no_secret_looking_values():
    serialized = json.dumps(_WORKSHEET_JSON_SCHEMA)
    assert "sk-" not in serialized
    assert "AIzaSy" not in serialized
    assert "openai-test-key" not in serialized
