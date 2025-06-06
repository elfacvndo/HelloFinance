from flask import url_for, session
from app import TaxItem, User # Assuming these models can be imported
import datetime

def test_taxes_page_loads(auth_client, app):
    with app.app_context():
        response = auth_client.get(url_for('taxes'))
    assert response.status_code == 200
    assert b"Gestione Tasse" in response.data # Updated heading
    assert b"Aggiungi Elemento Tassabile" in response.data # Updated sub-heading

def test_add_tax_item_success(auth_client, app, db):
    with auth_client.session_transaction() as sess:
        user_id = sess['user_id']
        assert user_id is not None

    today_str = datetime.date.today().strftime('%Y-%m-%d')
    with app.app_context():
        response = auth_client.post(url_for('add_tax_item'), data={
            'description': 'Medical Expense',
            'amount': '150.75',
            'date': today_str,
            'deduction_type': 'Health'
        }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Tax item added successfully!" in response.data
    assert b"I Tuoi Elementi Tassabili" in response.data # Updated sub-heading on taxes page

    with app.app_context():
        item = TaxItem.query.filter_by(user_id=user_id, description='Medical Expense').first()
        assert item is not None
        assert item.amount == 150.75
        assert item.deduction_type == 'Health'

def test_add_tax_item_requires_login(client, app):
    with app.app_context():
        response = client.get(url_for('taxes'), follow_redirects=True)
    assert response.status_code == 200
    assert b"Accedi al tuo account" in response.data # Login page heading
    assert b"Please log in to access this page." in response.data

    with app.app_context():
        response = client.post(url_for('add_tax_item'), data={
            'description': 'Charity Donation', 'amount': '50', 'date': '2023-01-01', 'deduction_type': 'Charity'
        }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Accedi al tuo account" in response.data # Login page heading

def test_view_tax_items(auth_client, app, db):
    with auth_client.session_transaction() as sess:
        user_id = sess['user_id']

    item_data = [
        {'description': 'Health Insurance Premium', 'amount': 300, 'date': '2023-01-10', 'deduction_type': 'Health'},
        {'description': 'Educational Course Fee', 'amount': 500, 'date': '2023-01-11', 'deduction_type': 'Education'},
    ]
    with app.app_context():
        for item_params in item_data:
            auth_client.post(url_for('add_tax_item'), data=item_params)

    with app.app_context():
        response = auth_client.get(url_for('taxes'))
    assert response.status_code == 200
    assert b"Health Insurance Premium" in response.data
    assert b"Educational Course Fee" in response.data
    assert b"300" in response.data
    assert b"500" in response.data

def test_edit_tax_item_page_loads(auth_client, app, db):
    with auth_client.session_transaction() as sess:
        user_id = sess['user_id']

    with app.app_context():
        auth_client.post(url_for('add_tax_item'), data={
            'description': 'Item to Edit Tax', 'amount': '99',
            'date': '2023-02-10', 'deduction_type': 'Work Expense'
        })
        item = TaxItem.query.filter_by(user_id=user_id, description='Item to Edit Tax').first()
        assert item is not None
        response = auth_client.get(url_for('edit_tax_item', item_id=item.id))
    assert response.status_code == 200
    assert b"Modifica Elemento Tassabile" in response.data # Updated heading
    assert b"Item to Edit Tax" in response.data # Check description in form
    assert b'99' in response.data # Check amount in form

def test_edit_tax_item_success(auth_client, app, db):
    with auth_client.session_transaction() as sess:
        user_id = sess['user_id']

    with app.app_context():
        auth_client.post(url_for('add_tax_item'), data={
            'description': 'Original Tax Desc', 'amount': '120',
            'date': '2023-02-11', 'deduction_type': 'Old Type'
        })
        item = TaxItem.query.filter_by(user_id=user_id, description='Original Tax Desc').first()
        assert item is not None
        original_item_id = item.id

        response = auth_client.post(url_for('edit_tax_item', item_id=original_item_id), data={
            'description': 'Updated Tax Desc', 'amount': '220',
            'date': '2023-02-12', 'deduction_type': 'New Type'
        }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Tax item updated successfully!" in response.data
    with app.app_context():
        updated_item = db.session.get(TaxItem, original_item_id) # Updated to db.session.get
        assert updated_item.description == 'Updated Tax Desc'
        assert updated_item.amount == 220
        assert updated_item.deduction_type == 'New Type'
        assert updated_item.date == datetime.date(2023, 2, 12)

def test_edit_tax_item_wrong_user(auth_client, client, app, db):
    with auth_client.session_transaction() as sess:
        user1_id = sess['user_id']

    with app.app_context():
        auth_client.post(url_for('add_tax_item'), data={
            'description': 'User1 Tax Item', 'amount': '70', 'date': '2023-03-10', 'deduction_type': 'U1Deduct'
        })
        item_user1 = TaxItem.query.filter_by(user_id=user1_id, description='User1 Tax Item').first()
        assert item_user1 is not None

    with app.app_context(): # Register and login second user
        client.post(url_for('register'), data={'username': 'tax_user2', 'email': 'tax_user2@example.com', 'password': 'password2'})
        client.post(url_for('login'), data={'email': 'tax_user2@example.com', 'password': 'password2'})

    with app.app_context():
        response = client.get(url_for('edit_tax_item', item_id=item_user1.id), follow_redirects=True)
    assert response.status_code == 200
    assert b"You are not authorized to edit this tax item." in response.data
    assert b"Gestione Tasse" in response.data # Redirected to taxes page, check heading

    with app.app_context():
        response = client.post(url_for('edit_tax_item', item_id=item_user1.id), data={
            'description': 'Hacked Tax Desc', 'amount': '1000', 'date': '2023-03-10', 'deduction_type': 'HackType'
        }, follow_redirects=True)
    assert response.status_code == 200
    assert b"You are not authorized to edit this tax item." in response.data
    with app.app_context():
        item_still_user1 = db.session.get(TaxItem, item_user1.id) # Updated to db.session.get
        assert item_still_user1.description == 'User1 Tax Item'
        assert item_still_user1.amount == 70

def test_delete_tax_item_success(auth_client, app, db):
    with auth_client.session_transaction() as sess:
        user_id = sess['user_id']

    with app.app_context():
        auth_client.post(url_for('add_tax_item'), data={
            'description': 'Tax Item To Delete', 'amount': '15', 'date': '2023-03-11', 'deduction_type': 'Temp'
        })
        item = TaxItem.query.filter_by(user_id=user_id, description='Tax Item To Delete').first()
        assert item is not None
        item_id_to_delete = item.id

        response = auth_client.post(url_for('delete_tax_item', item_id=item_id_to_delete), follow_redirects=True)
    assert response.status_code == 200
    assert b"Tax item deleted successfully!" in response.data
    with app.app_context():
        deleted_item = db.session.get(TaxItem, item_id_to_delete) # Updated to db.session.get
        assert deleted_item is None

def test_delete_tax_item_wrong_user(auth_client, client, app, db):
    with auth_client.session_transaction() as sess:
        user1_id = sess['user_id']
    with app.app_context():
        auth_client.post(url_for('add_tax_item'), data={
            'description': 'U1 Tax Del', 'amount': '25', 'date': '2023-03-12', 'deduction_type': 'U1DelType'
        })
        item_user1 = TaxItem.query.filter_by(user_id=user1_id, description='U1 Tax Del').first()
        assert item_user1 is not None

    with app.app_context(): # Register and login second user
        client.post(url_for('register'), data={'username': 'tax_user3', 'email': 'tax_user3@example.com', 'password': 'password3'})
        client.post(url_for('login'), data={'email': 'tax_user3@example.com', 'password': 'password3'})

    with app.app_context():
        response = client.post(url_for('delete_tax_item', item_id=item_user1.id), follow_redirects=True)
    assert response.status_code == 200
    assert b"You are not authorized to delete this tax item." in response.data
    with app.app_context():
        item_still_exists = db.session.get(TaxItem, item_user1.id) # Updated to db.session.get
        assert item_still_exists is not None
