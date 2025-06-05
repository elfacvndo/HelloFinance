import pytest
import os
import tempfile
import sys

# Add project root to sys.path to allow importing 'app'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# By importing 'app' and 'db' here, we assume that app.py is structured
# in a way that these can be imported and then reconfigured for tests.
# If app.py runs db.create_all() on import, this might need adjustment,
# or the app factory pattern would be more robust.
from app import app as flask_app, db as app_db, User # Renamed as_db to app_db

@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask application."""

    # Create a temporary file for the SQLite DB
    db_fd, db_path = tempfile.mkstemp(suffix='.sqlite')

    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "SECRET_KEY": "test_secret_key",  # Test-specific secret key
        "WTF_CSRF_ENABLED": False, # Disable CSRF for simpler form testing in unit tests
        "SERVER_NAME": "localhost.test" # Add a dummy server name
    })

    with flask_app.app_context():
        app_db.create_all() # Create database tables using app_db

    yield flask_app # Provide the app object to tests

    # Teardown: close and remove the temporary database file
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture()
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture()
def runner(app):
    """A test CLI runner for Flask commands (if any)."""
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def db(app):
    """
    Yields the SQLAlchemy db object and handles table creation and cleanup.
    This ensures each test function gets a clean database.
    """
    with app.app_context():
        # Tables are created by the 'app' fixture session-wide.
        # For function scope, if we wanted truly isolated dbs per test,
        # we'd drop and create here. However, for SQLite :memory: or tempfile,
        # the app fixture already provides a fresh DB per session.
        # If tests modify data and don't clean up, this might need enhancement
        # to clear data from tables between tests, e.g., by deleting all rows.

        # For now, we assume tests will manage their own data or the app fixture's
        # fresh DB per session is sufficient. If not, we'd do:
        # app_db.drop_all()
        # app_db.create_all()
        pass

    yield app_db # use app_db

    # Clean up database tables after each test if necessary
    # This is a more robust way to ensure test isolation if tests add data.
    with app.app_context():
        # For example, to remove all data from all tables:
        for table in reversed(app_db.metadata.sorted_tables): # use app_db
            app_db.session.execute(table.delete()) # use app_db
        app_db.session.commit() # use app_db


@pytest.fixture
def auth_client(client, db):
    """A test client that is pre-authenticated with a test user."""
    # Register a test user
    client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123'
    })
    # Login the test user
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    return client

@pytest.fixture
def registered_user_details(app, db): # Changed app_db parameter to db
    """Creates a user and returns their details as a dict."""
    # Import User model inside the fixture to ensure it's from the app context
    # although it's likely already loaded globally in conftest.
    from app import User
    details = {
        'username': 'testuser_reg',
        'email': 'test_reg@example.com',
        'password_plaintext': 'password_fixture_user'
    }
    hashed_password = generate_password_hash(details['password_plaintext'])

    with app.app_context():
        user = User(username=details['username'], email=details['email'], password_hash=hashed_password)
        db.session.add(user) # Use db fixture
        db.session.commit() # Use db fixture
        details['id'] = user.id # Get the ID after creation
    return details

from werkzeug.security import generate_password_hash

@pytest.fixture
def logged_in_user(app, db):
    """
    Creates a user, logs them in, and returns the user object and test client.
    This is useful for tests that need an authenticated user context.
    """
    with app.app_context(): # Ensure app context for DB operations
        hashed_password = generate_password_hash("securepassword")
        test_user = User(username="autotestuser", email="autotest@example.com", password_hash=hashed_password)
        db.session.add(test_user)
        db.session.commit()

        # Use a separate client for login to not interfere with the client fixture if used separately
        login_client = app.test_client() # app.test_client() should be available
        with login_client.session_transaction() as sess:
            sess['user_id'] = test_user.id

        return test_user, login_client
