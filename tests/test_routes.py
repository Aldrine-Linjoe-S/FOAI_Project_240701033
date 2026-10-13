from conftest import post_form

def test_assessment_is_saved_and_results_are_user_scoped(client, register_user):
    register_user()
    data={"education":"Undergraduate","skill_names":["Python","SQL"],"level_Python":"Advanced","level_SQL":"Intermediate","interests":["Data and analytics"],"strengths":["Logical thinking"],"work_styles":["Research"],"career_directions":["data-analyst"],"hours_per_week":"3–5 hours","learning_style":"Hands-on projects","csrf_token":""}
    with client.session_transaction() as sess: data["csrf_token"]=sess["csrf_token"]
    response=client.post("/assessment",data=data,follow_redirects=False)
    assert response.status_code==302 and "/results/" in response.location
    result=client.get(response.location)
    assert result.status_code==200 and b"Data Analyst" in result.data

def test_assessment_rejects_missing_required_answers(client, register_user):
    register_user(); response=post_form(client,"/assessment",{"education":"","interests":[]})
    assert b"Please complete your education level" in response.data

def test_career_explorer_search_and_detail(client):
    assert b"Web Developer" in client.get("/careers?q=web").data
    assert client.get("/careers/not-a-career").status_code==404

def test_csrf_is_required(client):
    assert client.post("/login",data={"email":"nobody@example.test","password":"x"}).status_code==400

def test_signed_in_pages_render_and_roadmap_progress_is_saved(client, register_user):
    register_user()
    for path in ("/dashboard", "/history", "/skills", "/assessment", "/roadmap/web-developer"):
        assert client.get(path).status_code==200, path
    with client.session_transaction() as sess: token=sess["csrf_token"]
    response=client.post("/roadmap/web-developer",data={"csrf_token":token,"task_id":["0-0"]},follow_redirects=True)
    assert response.status_code==200 and b"1 of 9 milestones complete" in response.data

def test_one_student_cannot_read_another_students_result(client, register_user):
    register_user("first@example.test")
    data={"education":"Undergraduate","skill_names":["Python"],"level_Python":"Beginner","interests":["Software development"]}
    with client.session_transaction() as sess: data["csrf_token"]=sess["csrf_token"]
    response=client.post("/assessment",data=data)
    private_result=response.location
    post_form(client,"/logout",{})
    register_user("second@example.test")
    assert client.get(private_result).status_code==404

def test_every_career_has_a_renderable_detail_page(client):
    from recommendation_engine import all_careers
    for career in all_careers():
        response=client.get(f"/careers/{career['slug']}")
        assert response.status_code==200 and career["name"].encode() in response.data
