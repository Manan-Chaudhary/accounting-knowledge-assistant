from types import SimpleNamespace

import app.rag.generator as generator
from app.rag.retriever import RetrievedChunk, format_retrieved_context


def test_format_retrieved_context():
    chunks = [
        RetrievedChunk(
            chunk_id=1,
            document_id=10,
            chunk_index=0,
            content="The basic eligibility conditions apply.",
            filename="ato-cgt-guidance.txt",
            source_label="ATO CGT guidance",
            distance=0.20,
        ),
        RetrievedChunk(
            chunk_id=2,
            document_id=11,
            chunk_index=3,
            content="Additional supporting guidance.",
            filename="ato-second-source.txt",
            source_label=None,
            distance=0.30,
        ),
    ]

    context = format_retrieved_context(chunks)

    assert "[1]" in context
    assert "[2]" in context
    assert "ATO CGT guidance" in context
    assert "ato-second-source.txt" in context
    assert "Document ID: 10" in context
    assert "Document ID: 11" in context
    assert "Chunk: 0" in context
    assert "Chunk: 3" in context
    assert "The basic eligibility conditions apply." in context
    assert "Additional supporting guidance." in context


def test_format_retrieved_context_when_empty():
    context = format_retrieved_context([])

    assert "No relevant document chunks were retrieved" in context
    assert "Do not answer using general knowledge" in context
    assert "no supporting source was found" in context


def test_generate_response_uses_retrieved_context(monkeypatch):
    retrieved_context = """[1]
Source: ATO guidance
File: ato-guidance.txt
Document ID: 8
Chunk: 0
Content:
Small business CGT concessions require basic eligibility conditions.
"""

    calls = []

    def fake_retrieve_context(query):
        calls.append(query)
        return retrieved_context

    monkeypatch.setattr(
        generator,
        "retrieve_context",
        fake_retrieve_context,
    )

    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="Grounded answer [1]."
                        )
                    )
                ]
            )

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = FakeChat()

    monkeypatch.setattr(generator, "OpenAI", FakeOpenAI)

    query = (
        "What are the eligibility requirements "
        "for the small business CGT concessions?"
    )

    result = generator.generate_response(
        query=query,
        model="test-model",
        api_base="http://example.test",
        api_key="test-key",
    )

    assert calls == [query]
    assert result == "Grounded answer [1]."

    messages = captured["messages"]

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    prompt = messages[1]["content"]

    assert query in prompt
    assert retrieved_context in prompt
    assert "[1]" in prompt


def test_generate_response_keeps_explicit_context(monkeypatch):
    def fail_if_called(query):
        raise AssertionError(
            "retrieve_context should not run when context is supplied"
        )

    monkeypatch.setattr(
        generator,
        "retrieve_context",
        fail_if_called,
    )

    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="Explicit context response."
                        )
                    )
                ]
            )

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = FakeChat()

    monkeypatch.setattr(generator, "OpenAI", FakeOpenAI)

    explicit_context = """[1]
Source: Test source
Content:
This context was supplied directly.
"""

    result = generator.generate_response(
        query="Test question",
        context=explicit_context,
        model="test-model",
        api_base="http://example.test",
        api_key="test-key",
    )

    assert result == "Explicit context response."
    assert explicit_context in captured["messages"][1]["content"]
