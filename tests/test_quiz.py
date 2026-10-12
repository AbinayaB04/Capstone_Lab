def test_quiz_score_calculation():
    sample_quiz = [
        {"question": "Q1", "options": ["A", "B", "C"], "answer": "A", "explanation": "A is correct."},
        {"question": "Q2", "options": ["A", "B", "C"], "answer": "B", "explanation": "B is correct."},
        {"question": "Q3", "options": ["A", "B", "C"], "answer": "C", "explanation": "C is correct."},
        {"question": "Q4", "options": ["A", "B", "C"], "answer": "A", "explanation": "A is correct."},
        {"question": "Q5", "options": ["A", "B", "C"], "answer": "B", "explanation": "B is correct."},
    ]

    user_answers = {
        0: "A", # correct
        1: "B", # correct
        2: "A", # wrong (expected C)
        3: "A", # correct
        4: "C", # wrong (expected B)
    }

    score = 0
    for i, q in enumerate(sample_quiz):
        if user_answers.get(i) == q["answer"]:
            score += 1

    total = len(sample_quiz)
    percentage = round((score / total) * 100, 1)

    assert score == 3
    assert total == 5
    assert percentage == 60.0

def test_quiz_attempt_formatting():
    from database.mongo_manager import record_quiz_attempt, get_quiz_attempts_by_user

    sample_quiz = [
        {"question": "What is 2+2?", "options": ["3", "4", "5"], "answer": "4", "explanation": "Basic addition."}
    ]

    test_username = "quiz_test_student"
    attempt_id = record_quiz_attempt(
        username=test_username,
        course_code="TEST101",
        branch_id="test_branch",
        semester=1,
        score=1,
        total_questions=1,
        difficulty="easy",
        user_answers={"0": "4"},
        quiz_details=sample_quiz
    )

    assert attempt_id is not None
    attempts = get_quiz_attempts_by_user(test_username, "TEST101")
    assert len(attempts) >= 1
    assert attempts[0]["score"] == 1
    assert attempts[0]["percentage"] == 100.0
    assert attempts[0]["difficulty"] == "easy"

    # Cleanup test data
    from database.mongo_manager import quiz_attempts_col
    quiz_attempts_col.delete_many({"username": test_username})

