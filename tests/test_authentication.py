from conftest import post_form

def test_registration_hashes_password_and_login_works(client, app):
    response=post_form(client,"/register",{"name":"A Student","email":"a@example.test","password":"password-123"})
    assert b"account is ready" in response.data
    with app.app_context():
        from database import connect_db
        db=connect_db(app.config["DATABASE"]); row=db.execute("SELECT password_hash FROM users").fetchone(); db.close()
    assert row["password_hash"]!="password-123"
    post_form(client,"/logout",{})
    response=post_form(client,"/login",{"email":"a@example.test","password":"password-123"})
    assert b"Welcome back" in response.data

def test_protected_pages_redirect(client):
    response=client.get("/dashboard")
    assert response.status_code==302 and "/login" in response.location

def test_invalid_credentials_do_not_log_in(client, register_user):
    register_user(); post_form(client,"/logout",{})
    response=post_form(client,"/login",{"email":"student@example.test","password":"wrong-password"})
    assert b"Email or password" in response.data
    assert client.get("/dashboard").status_code==302
