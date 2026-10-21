import pytest
import os
from services.llm_service import AIEngine

def test_spelling_correction_and_normalization():
    """Verify that misspelled queries and technical typos are properly normalized."""
    engine = AIEngine()
    
    # 1. Obvious typos
    query_with_typos = "what is normaliztion and b-tre indexx in dbbms?"
    corrected = engine.correct_spelling(query_with_typos)
    
    # Assert typos are cleaned
    assert "normalization" in corrected.lower()
    assert "tree" in corrected.lower()
    assert "dbms" in corrected.lower()

    # 2. Already correct query should remain stable
    clean_query = "What is database normalization?"
    corrected_clean = engine.correct_spelling(clean_query)
    assert "normalization" in corrected_clean.lower()

def test_web_search_fallback_retrieval():
    """Verify multi-source web search (DuckDuckGo + Wikipedia) returns authoritative context."""
    engine = AIEngine()
    
    context, sources = engine.perform_web_search("Relational database normalization")
    assert len(context) > 50
    assert len(sources) >= 1
    assert any("wikipedia" in s.get("source", "").lower() or "duckduckgo" in s.get("source", "").lower() for s in sources)
    assert any("http" in s.get("url", "") for s in sources)

def test_no_relevant_documents_fallback_flow():
    """
    Verify that when querying without uploaded course materials,
    the engine clearly flags that no relevant documents were found,
    switches to internet search, and returns web citations.
    """
    engine = AIEngine()
    
    # Query with non-existent course code so no vector docs match
    res = engine.generate_response(
        query="What is the difference between inner join and outer join in SQL?",
        course_code="NON_EXISTENT_COURSE_XYZ999",
        department_id="fake_dept",
        branch_id="fake_branch",
        return_sources=True
    )
    
    assert isinstance(res, dict)
    assert res.get("source_type") == "internet"
    assert "No relevant answer was found in the uploaded course documents" in res.get("answer", "")
    assert len(res.get("sources", [])) >= 1

def test_complex_quiz_structure_with_diagram_and_image():
    """Verify complex quiz question format with diagram, image_svg, and image_url keys."""
    sample_complex_quiz = [
        {
            "question": "Analyze the entity-relationship schema below. Which cardinal relationship is represented?",
            "image_svg": "<svg viewBox='0 0 500 140' xmlns='http://www.w3.org/2000/svg'><rect x='20' y='30' width='140' height='70'/></svg>",
            "diagram": "Entity A [1] ----< M >---- [N] Entity B",
            "image_url": "https://example.com/schema.png",
            "options": ["One-to-One", "One-to-Many", "Many-to-Many", "Unary"],
            "answer": "Many-to-Many",
            "explanation": "The relationship diamond indicates an M:N cardinal connectivity."
        },
        {
            "question": "In a B-tree of order 4, what happens when a node overflows?",
            "image_svg": None,
            "diagram": "[ 10 | 20 | 30 | 40 ] -> Split",
            "image_url": None,
            "options": ["Node splits into two and median promotes", "Node is deleted", "Underflow error", "Data is compressed"],
            "answer": "Node splits into two and median promotes",
            "explanation": "When an order-m node exceeds m-1 keys, it splits at the median key."
        }
    ]
    
    for q in sample_complex_quiz:
        assert "question" in q and len(q["question"]) > 10
        assert "options" in q and len(q["options"]) == 4
        assert "answer" in q and q["answer"] in q["options"]
        assert "explanation" in q and len(q["explanation"]) > 10
        assert "diagram" in q
        assert "image_url" in q
        assert "image_svg" in q

    # Verify dynamic SVG diagram card generation for questions with text/ASCII diagrams
    from views.student_view import generate_svg_diagram_card
    svg_output = generate_svg_diagram_card(sample_complex_quiz[1]["diagram"], title="B-Tree Overflow")
    assert "<svg" in svg_output and "</svg>" in svg_output
    assert "B-Tree Overflow" in svg_output
    assert "Split" in svg_output

def test_query_request_schema_with_rich_chat_history():
    """Verify that QueryRequest accepts chat_history containing nested sources lists."""
    from api.routes.chat_routes import QueryRequest
    
    # Simulates what Streamlit session_state.messages sends on second+ messages
    rich_history = [
        {"role": "user", "content": "What is SQL?"},
        {
            "role": "assistant",
            "content": "SQL is a standard language for storing, manipulating and retrieving data.",
            "sources": [{"source": "Page 340", "content": "Sample content"}],
            "source_type": "course_material"
        }
    ]
    
    req = QueryRequest(
        query="give me an exaple sql query",
        chat_history=rich_history
    )
    assert len(req.chat_history) == 2
    assert req.chat_history[1]["sources"][0]["source"] == "Page 340"

