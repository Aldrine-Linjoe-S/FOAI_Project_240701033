from recommendation_engine import recommend

def test_scores_are_deterministic_and_bounded():
    answers={"skill_levels":{"Python":"Advanced","SQL":"Intermediate"},"interests":["Data and analytics"],"strengths":["Logical thinking"]}
    first=recommend(answers); second=recommend(answers)
    assert [(x["slug"],x["score"]) for x in first]==[(x["slug"],x["score"]) for x in second]
    assert all(0<=x["score"]<=100 for x in first)

def test_missing_answers_are_safe():
    result=recommend({})
    assert len(result)==3 and all(x["score"]==0 for x in result)

def test_relevant_answers_surface_career_evidence():
    matches=recommend({"skill_levels":{"HTML/CSS":"Advanced","JavaScript":"Advanced"},"interests":["Web applications"],"strengths":["Creativity"]})
    assert matches[0]["slug"]=="web-developer"
    assert "HTML/CSS" in matches[0]["matching_skills"]
    assert matches[0]["reasons"]
