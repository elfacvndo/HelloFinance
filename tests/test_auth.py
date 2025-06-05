from flask import session, url_for
from app import User # Assuming User model can be imported

def test_register_page_loads(client, app):
    with app.app_context():
        response = client.get(url_for('register'))
    assert response.status_code == 200
    assert b"Register</h1>" in response.data

def test_register_success(client, app, db):
    with app.app_context():
        response = client.post(url_for('register'), data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'password123'
        }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Login</h1>" in response.data
    assert b"Registration successful! Please log in." in response.data
    with app.app_context():
        user = User.query.filter_by(email='newuser@example.com').first()
        assert user is not None
        assert user.username == 'newuser'

def test_register_duplicate_username(client, app, db, registered_user_details):
    with app.app_context():
        response = client.post(url_for('register'), data={
            'username': registered_user_details['username'],
            'email': 'new_dup_user@example.com',
            'password': 'password456'
        }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Register</h1>" in response.data
    assert b"Username or email already exists." in response.data
    with app.app_context():
        user_count = User.query.filter_by(username=registered_user_details['username']).count()
        assert user_count == 1

def test_register_duplicate_email(client, app, db, registered_user_details):
    with app.app_context():
        response = client.post(url_for('register'), data={
            'username': 'new_dup_email_user',
            'email': registered_user_details['email'],
            'password': 'password789'
        }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Register</h1>" in response.data
    assert b"Username or email already exists." in response.data
    with app.app_context():
        user_count = User.query.filter_by(email=registered_user_details['email']).count()
        assert user_count == 1

def test_login_page_loads(client, app):
    with app.app_context():
        response = client.get(url_for('login'))
    assert response.status_code == 200
    assert b"Login</h1>" in response.data

def test_login_success(client, app, registered_user_details):
    # User ('testuser_reg', 'test_reg@example.com') is created by registered_user_details fixture
    with app.app_context():
        response = client.post(url_for('login'), data={
            'email': registered_user_details['email'],
            'password': registered_user_details['password_plaintext'] # Use plain text password from fixture
        }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Your Transactions" in response.data
    assert b"Login successful!" in response.data
    with client.session_transaction() as sess:
        assert sess.get('user_id') is not None
        assert sess.get('user_id') == registered_user_details['id'] # Check correct user ID in session

def test_login_wrong_email(client, app, registered_user_details):
    with app.app_context():
        response = client.post(url_for('login'), data={
            'email': 'wrong@example.com', # Non-existent email
            'password': registered_user_details['password_plaintext'] # Correct password for fixture user
        }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Login</h1>" in response.data
    assert b"Invalid email or password." in response.data
    with client.session_transaction() as sess:
        assert sess.get('user_id') is None

def test_login_wrong_password(client, app):
    with app.app_context():
        client.post(url_for('register'), data={
            'username': 'loginpassuser',
            'email': 'loginpass@example.com',
            'password': 'correctpassword'
        })
        response = client.post(url_for('login'), data={
            'email': 'loginpass@example.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Login</h1>" in response.data
    assert b"Invalid email or password." in response.data
    with client.session_transaction() as sess:
        assert sess.get('user_id') is None

def test_logout(auth_client, app):
    with app.app_context():
        with auth_client.session_transaction() as sess:
            assert sess.get('user_id') is not None

        response = auth_client.get(url_for('logout'), follow_redirects=True)
    assert response.status_code == 200
    assert b"Login</h1>" in response.data
    assert b"You have been logged out." in response.data
    with auth_client.session_transaction() as sess:
        assert sess.get('user_id') is None

def test_access_protected_route_unauthenticated(client, app):
    with app.app_context():
        response = client.get(url_for('index'), follow_redirects=True)
    assert response.status_code == 200
    assert b"Login</h1>" in response.data
    assert b"Please log in to access this page." in response.data

def test_access_protected_route_authenticated(auth_client, app):
    with app.app_context():
        response = auth_client.get(url_for('index'))
    assert response.status_code == 200
    assert b"Your Transactions" in response.data
    assert b"Hello, testuser!" in response.data
