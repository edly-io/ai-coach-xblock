import importlib
import json
import sys
import types
from unittest import mock

import pytest
from webob import Request
from xblock.field_data import DictFieldData
from xblock.fields import ScopeIds

from ai_coach import ai_coach
from ai_coach.ai_coach import AICoachXBlock


def make_block(**fields):
    return AICoachXBlock(
        runtime=mock.MagicMock(),
        field_data=DictFieldData(fields),
        scope_ids=ScopeIds("user", "ai_coach", "def", "usage"),
    )


def call(block, handler, data):
    request = Request.blank("/", method="POST", body=json.dumps(data).encode())
    response = getattr(block, handler)(request)
    return json.loads(response.body)


def completion(text):
    return mock.Mock(choices=[mock.Mock(message=mock.Mock(content=text))])


@pytest.fixture
def block():
    return make_block(question="What is 2+2?", api_key="sk-x", feedback_threshold=2)


def test_default_api_key_comes_from_settings():
    assert make_block().api_key == "sk-test"


def test_get_openai_client(block):
    with mock.patch.object(ai_coach, "OpenAI") as openai_cls:
        assert block.get_openai_client() is openai_cls.return_value
    openai_cls.assert_called_once_with(api_key="sk-x")


def test_get_openai_client_failure(block):
    with mock.patch.object(ai_coach, "OpenAI", side_effect=ValueError("boom")):
        assert block.get_openai_client() == {"error": "Failed to initialize OpenAI client"}


def test_resource_string(block):
    assert "<" in block.resource_string("static/html/ai_coach.html")


def test_resource_string_falls_back_to_package_when_files_raises_type_error(block):
    reader = mock.Mock()
    reader.joinpath.return_value.read_bytes.return_value = b"data"
    files = mock.Mock(side_effect=[TypeError, reader])
    with mock.patch.object(ai_coach.importlib_resources, "files", files):
        assert block.resource_string("x") == "data"
    assert files.call_args_list == [mock.call("ai_coach.ai_coach"), mock.call("ai_coach")]


def test_get_context(block):
    assert block.get_context() == {
        "title": "AI Coach",
        "question": "What is 2+2?",
        "student_answer": "",
        "feedback_count": 0,
        "feedback_threshold": 2,
    }


def test_render_template_uses_block_context(block):
    with mock.patch.object(block, "resource_string", return_value="{{ title }}|{{ question }}"):
        assert block.render_template("any.html", {"ignored": 1}) == "AI Coach|What is 2+2?"


def test_student_view(block):
    frag = block.student_view()
    assert "What is 2+2?" in frag.content
    assert frag.js_init_fn == "AICoachXBlock"
    assert frag.json_init_args["feedback_threshold"] == 2
    assert frag.resources


def test_get_chat_completion(block):
    client = mock.Mock()
    client.chat.completions.create.return_value = completion("good")
    with mock.patch.object(block, "get_openai_client", return_value=client):
        result = block.get_chat_completion("hi", "gpt-x", 0.2, 10, 1)
    assert result == {"response": "good"}
    client.chat.completions.create.assert_called_once_with(
        messages=[{"role": "user", "content": "hi"}], model="gpt-x", temperature=0.2, max_tokens=10, n=1
    )


def test_get_chat_completion_without_client(block):
    with mock.patch.object(block, "get_openai_client", return_value=None):
        assert "Unable to initialize" in block.get_chat_completion("hi")["error"]


def test_get_chat_completion_api_error(block):
    client = mock.Mock()
    client.chat.completions.create.side_effect = RuntimeError("down")
    with mock.patch.object(block, "get_openai_client", return_value=client):
        assert "Unable to connect" in block.get_chat_completion("hi")["error"]


def test_ask_from_coach_requires_answer(block):
    assert call(block, "ask_from_coach", {"answer": ""}) == {"error": "Answer must be required"}


def test_ask_from_coach_threshold_exhausted(block):
    block.feedback_count = 2
    assert "exhausted" in call(block, "ask_from_coach", {"answer": "4"})["error"]


def test_ask_from_coach_success(block):
    with mock.patch.object(block, "get_chat_completion", return_value={"response": "nice"}) as chat:
        result = call(block, "ask_from_coach", {"answer": "  4  "})
    assert result == {"success": True, "coach_answer": "nice", "feedback_count": 1, "feedback_threshold": 2}
    prompt = chat.call_args.args[0]
    assert '"What is 2+2?"' in prompt and '"4"' in prompt
    assert "{{" not in prompt
    assert block.feedback_count == 1


def test_ask_from_coach_error_does_not_consume_attempt(block):
    with mock.patch.object(block, "get_chat_completion", return_value={"error": "bad"}):
        assert call(block, "ask_from_coach", {"answer": "4"}) == {"error": "bad"}
    assert block.feedback_count == 0


def test_submit_answer_requires_answer(block):
    assert call(block, "submit_answer", {"answer": ""}) == {"error": "Answer must be required"}


def test_submit_answer(block):
    with mock.patch.object(block, "emit_completion") as emit:
        assert call(block, "submit_answer", {"answer": " 4 "}) == {"success": True}
    assert block.student_answer == "4"
    emit.assert_called_once_with(1.0)


def test_workbench_scenarios():
    names = [name for name, _ in AICoachXBlock.workbench_scenarios()]
    assert names == ["AICoachXBlock", "Multiple AICoachXBlock"]


def validate(context):
    block = make_block()
    validation = mock.Mock()
    data = mock.Mock(context=context)
    block.validate_field_data(validation, data)
    return [call.args[0].text for call in validation.add.call_args_list]


def test_validate_field_data_accepts_both_placeholders():
    assert validate("{{question}} {{answer}}") == []


def test_validate_field_data_reports_missing_answer():
    (message,) = validate("{{question}}")
    assert message.endswith("{{answer}}")


def test_validate_field_data_reports_both_missing_for_empty_context():
    (message,) = validate("")
    assert message.endswith("{{question}}, {{answer}}")


def test_validate_field_data_reports_both_missing_for_none_context():
    (message,) = validate(None)
    assert message.endswith("{{question}}, {{answer}}")


@pytest.fixture
def reloaded():
    yield lambda: importlib.reload(ai_coach)
    for name in ("importlib_resources", "xblock.utils.studio_editable"):
        sys.modules.pop(name, None)
    importlib.reload(ai_coach)


def test_import_prefers_backported_importlib_resources(monkeypatch, reloaded):
    fake = types.ModuleType("importlib_resources")
    monkeypatch.setitem(sys.modules, "importlib_resources", fake)
    assert reloaded().importlib_resources is fake


def test_import_falls_back_to_xblockutils_before_quince(monkeypatch, reloaded):
    import xblockutils.studio_editable as legacy

    monkeypatch.setitem(sys.modules, "xblock.utils.studio_editable", None)
    assert reloaded().StudioEditableXBlockMixin is legacy.StudioEditableXBlockMixin
