from flask import url_for, session
from app import Transaction, User # Assuming these models can be imported
import datetime

# Helper function to create a user and log them in
def login_test_user(client, app, username='tx_user', email='tx@example.com', password='tx_password'):
    with app.app_context():
        # Register user
        client.post(url_for('register'), data={
            'username': username,
            'email': email,
            'password': password
        })
        # Login user
        response = client.post(url_for('login'), data={
            'email': email,
            'password': password
        }, follow_redirects=True)
    assert response.status_code == 200
    with client.session_transaction() as sess:
        return sess.get('user_id')

def test_add_transaction_page_loads(auth_client, app):
    with app.app_context():
        response = auth_client.get(url_for('add_transaction'))
    assert response.status_code == 200
    assert b"Add New Transaction" in response.data

def test_add_transaction_success(auth_client, app, db):
    with auth_client.session_transaction() as sess:
        user_id = sess['user_id']
        assert user_id is not None

    today_str = datetime.date.today().strftime('%Y-%m-%d')
    with app.app_context():
        response = auth_client.post(url_for('add_transaction'), data={
            'type': 'income',
            'category': 'Salary',
            'description': 'Monthly pay',
            'amount': '3000.00',
            'date': today_str
        }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Transaction added successfully!" in response.data
    assert b"Your Transactions" in response.data

    with app.app_context():
        tx = Transaction.query.filter_by(user_id=user_id, description='Monthly pay').first()
        assert tx is not None
        assert tx.category == 'Salary'
        assert tx.amount == 3000.00
        assert tx.type == 'income'

def test_add_transaction_requires_login(client, app):
    with app.app_context():
        response = client.get(url_for('add_transaction'), follow_redirects=True)
    assert response.status_code == 200
    assert b"Login</h1>" in response.data
    assert b"Please log in to access this page." in response.data

    with app.app_context():
        response = client.post(url_for('add_transaction'), data={
            'type': 'income', 'category': 'Freelance', 'amount': '100', 'date': '2023-01-01'
        }, follow_redirects=True)
    assert b"Login</h1>" in response.data

def test_view_transactions_and_filtering(auth_client, app, db):
    with auth_client.session_transaction() as sess:
        user_id = sess['user_id']

    tx_data = [
        {'type': 'income', 'category': 'Salary', 'description': 'Pay 1', 'amount': 2000, 'date': '2023-01-05'},
        {'type': 'expense', 'category': 'Groceries', 'description': 'Food shopping', 'amount': 75, 'date': '2023-01-06'},
        {'type': 'expense', 'category': 'Util', 'description': 'Electric bill', 'amount': 120, 'date': '2023-01-07'},
        {'type': 'income', 'category': 'Bonus', 'description': 'Work bonus', 'amount': 500, 'date': '2023-01-08'},
    ]
    with app.app_context():
        for item in tx_data:
            auth_client.post(url_for('add_transaction'), data=item)

    with app.app_context():
        response = auth_client.get(url_for('index'))
    assert response.status_code == 200
    assert b"Pay 1" in response.data
    assert b"Food shopping" in response.data
    assert b"Electric bill" in response.data
    assert b"Work bonus" in response.data

    with app.app_context():
        response = auth_client.get(url_for('index', filter='income'))
    assert b"Pay 1" in response.data
    assert b"Work bonus" in response.data
    assert b"Food shopping" not in response.data
    assert b"Electric bill" not in response.data

    with app.app_context():
        response = auth_client.get(url_for('index', filter='expense'))
    assert b"Food shopping" in response.data
    assert b"Electric bill" in response.data
    assert b"Pay 1" not in response.data
    assert b"Work bonus" not in response.data

def test_edit_transaction_page_loads(auth_client, app, db):
    with auth_client.session_transaction() as sess:
        user_id = sess['user_id']

    with app.app_context():
        auth_client.post(url_for('add_transaction'), data={
            'type': 'expense', 'category': 'TestEdit', 'description': 'Item to edit',
            'amount': '50', 'date': '2023-02-01'
        })
        tx = Transaction.query.filter_by(user_id=user_id, description='Item to edit').first()
        assert tx is not None
        response = auth_client.get(url_for('edit_transaction', transaction_id=tx.id))
    assert response.status_code == 200
    assert b"Edit Transaction" in response.data
    assert b"Item to edit" in response.data
    assert b'50' in response.data


def test_edit_transaction_success(auth_client, app, db):
    with auth_client.session_transaction() as sess:
        user_id = sess['user_id']

    with app.app_context():
        auth_client.post(url_for('add_transaction'), data={
            'type': 'expense', 'category': 'BeforeEdit', 'description': 'Original Desc',
            'amount': '100', 'date': '2023-02-02'
        })
        tx = Transaction.query.filter_by(user_id=user_id, description='Original Desc').first()
        assert tx is not None
        original_tx_id = tx.id

        response = auth_client.post(url_for('edit_transaction', transaction_id=original_tx_id), data={
            'type': 'income', 'category': 'AfterEdit', 'description': 'Updated Desc',
            'amount': '200', 'date': '2023-02-03'
        }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Transaction updated successfully!" in response.data
    with app.app_context():
        updated_tx = db.session.get(Transaction, original_tx_id)
        assert updated_tx.description == 'Updated Desc'
        assert updated_tx.category == 'AfterEdit'
        assert updated_tx.type == 'income'
        assert updated_tx.amount == 200
        assert updated_tx.date == datetime.date(2023, 2, 3)

def test_edit_transaction_wrong_user(auth_client, client, app, db):
    with auth_client.session_transaction() as sess:
        user1_id = sess['user_id']

    with app.app_context():
        auth_client.post(url_for('add_transaction'), data={
            'type': 'expense', 'category': 'User1s TX', 'description': 'U1 TX', 'amount': '10', 'date': '2023-03-01'
        })
        tx_user1 = Transaction.query.filter_by(user_id=user1_id, description='U1 TX').first()
        assert tx_user1 is not None

    login_test_user(client, app, username='user2', email='user2@example.com', password='password2')

    with app.app_context():
        response = client.get(url_for('edit_transaction', transaction_id=tx_user1.id), follow_redirects=True)
    assert response.status_code == 200
    assert b"You are not authorized to edit this transaction." in response.data
    assert b"Your Transactions" in response.data

    with app.app_context():
        response = client.post(url_for('edit_transaction', transaction_id=tx_user1.id), data={
            'type': 'income', 'category': 'HackAttempt', 'description': 'Tried to edit',
            'amount': '1000', 'date': '2023-03-01'
        }, follow_redirects=True)
    assert response.status_code == 200
    assert b"You are not authorized to edit this transaction." in response.data
    with app.app_context():
        tx_still_user1 = db.session.get(Transaction, tx_user1.id)
        assert tx_still_user1.description == 'U1 TX'
        assert tx_still_user1.category == 'User1s TX'


def test_delete_transaction_success(auth_client, app, db):
    with auth_client.session_transaction() as sess:
        user_id = sess['user_id']

    with app.app_context():
        auth_client.post(url_for('add_transaction'), data={
            'type': 'expense', 'category': 'ToDelete', 'description': 'Will be deleted',
            'amount': '5', 'date': '2023-03-03'
        })
        tx = Transaction.query.filter_by(user_id=user_id, description='Will be deleted').first()
        assert tx is not None
        tx_id_to_delete = tx.id

        response = auth_client.post(url_for('delete_transaction', transaction_id=tx_id_to_delete), follow_redirects=True)
    assert response.status_code == 200
    assert b"Transaction deleted successfully!" in response.data
    with app.app_context():
        deleted_tx = db.session.get(Transaction, tx_id_to_delete)
        assert deleted_tx is None

def test_delete_transaction_wrong_user(auth_client, client, app, db):
    with auth_client.session_transaction() as sess:
        user1_id = sess['user_id']
    with app.app_context():
        auth_client.post(url_for('add_transaction'), data={
            'type': 'expense', 'category': 'User1Delete', 'description': 'U1 TX Del', 'amount': '10', 'date': '2023-03-04'
        })
        tx_user1 = Transaction.query.filter_by(user_id=user1_id, description='U1 TX Del').first()
        assert tx_user1 is not None

    login_test_user(client, app, username='user2del', email='user2del@example.com', password='password2del')

    with app.app_context():
        response = client.post(url_for('delete_transaction', transaction_id=tx_user1.id), follow_redirects=True)
    assert response.status_code == 200
    assert b"You are not authorized to delete this transaction." in response.data
    with app.app_context():
        tx_still_exists = db.session.get(Transaction, tx_user1.id)
        assert tx_still_exists is not None
