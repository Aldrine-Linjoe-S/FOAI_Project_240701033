import pytest
from app import create_app

@pytest.fixture
def app(tmp_path):
    application = create_app({"TESTING":True,"SECRET_KEY":"test-secret","DATABASE":str(tmp_path/"test.sqlite3")})
    yield application

@pytest.fixture
def client(app): return app.test_client()

def post_form(client, path, data):
    client.get(path)
    with client.session_transaction() as sess: data["csrf_token"] = sess["csrf_token"]
    return client.post(path, data=data, follow_redirects=True)

@pytest.fixture
def register_user(client):
    def register(email="student@example.test"):
        return post_form(client,"/register",{"name":"Test Student","email":email,"password":"sample-pass-123"})
    return register

@pytest.fixture
def post_form_fixture(): return post_form
