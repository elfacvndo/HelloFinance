import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import func
import datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev_secret_key' # IMPORTANT: Change this for production!

# Configure SQLAlchemy
# Construct the absolute path to the database file
db_path = os.path.join(app.instance_path, 'project.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'income' or 'expense'
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.date.today)

    user = db.relationship('User', backref=db.backref('transactions', lazy=True))

class TaxItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    deduction_type = db.Column(db.String(100))

    user = db.relationship('User', backref=db.backref('tax_items', lazy=True))

# --- Authentication Helper & Hooks ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def load_logged_in_user():
    app.logger.info("--- load_logged_in_user ---")
    user_id = session.get('user_id')
    app.logger.info(f"user_id from session: {user_id}")
    if user_id is None:
        g.user = None
        app.logger.info("g.user set to None (user_id was None).")
    else:
        app.logger.info(f"Attempting to fetch user with id: {user_id}")
        try:
            retrieved_user = db.session.get(User, user_id)
            app.logger.info(f"User fetched from DB: {retrieved_user}")
            g.user = retrieved_user
        except Exception as e:
            app.logger.error(f"Error fetching user from DB in load_logged_in_user: {e}", exc_info=True)
            g.user = None # Ensure g.user is None if there's an error
    app.logger.info(f"g.user is now: {g.user}")

# --- Routes ---
@app.route('/')
@login_required
def index():
    app.logger.info(f"Simplified index route entered. g.user is: {g.user}, username: {g.user.username if g.user and hasattr(g.user, 'username') else 'No g.user or user has no username'}")

    # All data calculation logic is commented out as per the subtask.
    # # g.user is available thanks to load_logged_in_user
    # # filter_type = request.args.get('filter', 'all') # 'all', 'income', 'expense'

    # # # Default to transactions view / main dashboard view
    # # query = Transaction.query.filter_by(user_id=g.user.id)
    # # if filter_type == 'income':
    # #     query = query.filter_by(type='income')
    # # elif filter_type == 'expense':
    # #     query = query.filter_by(type='expense')

    # # transactions = query.order_by(Transaction.date.desc()).all()

    # # # TODO Future: Call AI insights and forecast functions here to display on dashboard.
    # # # Example:
    # # # if g.user: # Ensure user is logged in
    # # #     insights_message = get_spending_insights_ai(g.user.id)
    # # #     forecast_message = forecast_spending_ai(g.user.id)
    # # #     # Pass insights and forecast to the template:
    # # #     # return render_template('index.html', transactions=transactions, current_filter=filter_type,
    # # #     #                        insights=insights_message, forecast=forecast_message)

    # # app.logger.debug(f"User: {g.user.username if g.user else 'No User'} accessing dashboard")
    # # app.logger.debug(f"Filter type: {filter_type}")

    # # # Calculate available balance
    # # total_income = db.session.query(func.sum(Transaction.amount)).filter(Transaction.user_id == g.user.id, Transaction.type == 'income').scalar() or 0.0
    # # total_expenses = db.session.query(func.sum(Transaction.amount)).filter(Transaction.user_id == g.user.id, Transaction.type == 'expense').scalar() or 0.0
    # # available_balance = total_income - total_expenses

    # # # Calculate today's total expenses
    # # today = datetime.date.today()
    # # todays_expenses_query = db.session.query(func.sum(Transaction.amount)).filter(
    # #     Transaction.user_id == g.user.id,
    # #     Transaction.type == 'expense',
    # #     Transaction.date == today
    # # )
    # # todays_total_expenses = todays_expenses_query.scalar() or 0.0

    # # # Fetch last 4 recent transactions for the specific section in the dashboard
    # # recent_transactions = Transaction.query.filter_by(user_id=g.user.id)\
    # #     .order_by(Transaction.date.desc(), Transaction.id.desc())\
    # #     .limit(4).all()

    # # app.logger.debug(f"Available Balance: {available_balance}")
    # # app.logger.debug(f"Today's Total Expenses: {todays_total_expenses}")
    # # app.logger.debug(f"Number of transactions for main list (filtered): {len(transactions)}")
    # # app.logger.debug(f"Number of recent_transactions: {len(recent_transactions)}")

    # # # Prepare context for original template (or for minimal_test.html if it uses them)
    # # template_context = {
    # #     'transactions': transactions,
    # #     'recent_transactions': recent_transactions,
    # #     'current_filter': filter_type,
    # #     'available_balance': available_balance,
    # #     'todays_total_expenses': todays_total_expenses
    # # }

    try:
        app.logger.info("Attempting to render MAIN index.html with simplified context...")
        html_output = render_template('index.html',  # Changed to index.html
                                      g=g,
                                      test_variable="Dashboard with minimal context") # Updated test_variable
        app.logger.info("render_template('index.html') with simplified context called successfully.") # Updated log
        return html_output
    except Exception as e:
        app.logger.error(f"Exception during render_template for MAIN index.html (simplified context): {e}", exc_info=True)
        raise

@app.route('/transactions_all')
@login_required
def transactions_all_page():
    filter_type = request.args.get('filter', 'all')
    query = Transaction.query.filter_by(user_id=g.user.id)

    if filter_type == 'income':
        query = query.filter_by(type='income')
    elif filter_type == 'expense':
        query = query.filter_by(type='expense')

    all_user_transactions = query.order_by(Transaction.date.desc(), Transaction.id.desc()).all()

    # Group transactions
    grouped_transactions = {
        "Oggi": [],
        "Ieri": [],
        "Older": []
    }
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    for tx in all_user_transactions:
        if tx.date == today:
            grouped_transactions["Oggi"].append(tx)
        elif tx.date == yesterday:
            grouped_transactions["Ieri"].append(tx)
        else:
            grouped_transactions["Older"].append(tx)

    return render_template('transactions_list.html',
                           grouped_transactions=grouped_transactions,
                           current_filter=filter_type)

@app.route('/profile')
@login_required
def profile_page():
    # g.user is available due to @app.before_request
    return render_template('profile.html')

@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        type = request.form.get('type')
        category = request.form.get('category')
        description = request.form.get('description')
        amount_str = request.form.get('amount')
        date_str = request.form.get('date')

        if not all([type, category, amount_str, date_str]):
            flash('All fields except description are required.', 'danger')
            return redirect(url_for('add_transaction'))

        try:
            amount = float(amount_str)
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid amount or date format.', 'danger')
            return redirect(url_for('add_transaction'))

        new_transaction = Transaction(
            user_id=g.user.id,
            type=type,
            category=category,
            description=description,
            amount=amount,
            date=date_obj
        )
        db.session.add(new_transaction)
        db.session.commit()

        # TODO Future: Call AI categorization here, especially if category is generic or empty.
        # Example:
        # if not new_transaction.category or \
        #    new_transaction.category.lower() in ['other', 'uncategorized', 'general', 'miscellaneous']:
        #     suggested_category = categorize_transaction_ai(new_transaction.description)
        #     if suggested_category != "Uncategorized":
        #         new_transaction.category = suggested_category
        #         # Optionally, flash a message to the user about the auto-categorization
        #         # flash(f"We've categorized this transaction as '{suggested_category}'. You can change it if needed.", "info")
        #         db.session.commit() # Commit the category change
        #         print(f"AI suggested category '{suggested_category}' for description '{new_transaction.description}' and amount {new_transaction.amount}")

        flash('Transaction added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('add_transaction.html', today_date=datetime.date.today().strftime('%Y-%m-%d'))

@app.route('/edit_transaction/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)

    if transaction.user_id != g.user.id:
        flash('You are not authorized to edit this transaction.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        type = request.form.get('type')
        category = request.form.get('category')
        description = request.form.get('description')
        amount_str = request.form.get('amount')
        date_str = request.form.get('date')

        if not all([type, category, amount_str, date_str]):
            flash('All fields except description are required.', 'danger')
            return redirect(url_for('edit_transaction', transaction_id=transaction_id))

        try:
            amount = float(amount_str)
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid amount or date format.', 'danger')
            return redirect(url_for('edit_transaction', transaction_id=transaction_id))

        transaction.type = type
        transaction.category = category
        transaction.description = description
        transaction.amount = amount
        transaction.date = date_obj

        db.session.commit()
        flash('Transaction updated successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('edit_transaction.html', transaction=transaction)

@app.route('/delete_transaction/<int:transaction_id>', methods=['POST']) # Should be POST for safety
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != g.user.id:
        flash('You are not authorized to delete this transaction.', 'danger')
        return redirect(url_for('index'))

    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted successfully!', 'success')
    return redirect(url_for('index'))

# --- AI Feature Placeholders ---
def categorize_transaction_ai(transaction_description: str) -> str:
    """
    Placeholder for AI-powered transaction categorization.
    Eventually, this would call an AI service or model.
    """
    print(f"AI Mode: Categorizing transaction: '{transaction_description}'")
    # Simple keyword-based categorization for placeholder
    if "coffee" in transaction_description.lower() or \
       "starbucks" in transaction_description.lower() or \
       "cafe" in transaction_description.lower():
        return "Food & Drink"
    if "grocery" in transaction_description.lower() or \
       "supermarket" in transaction_description.lower():
        return "Groceries"
    if "gas" in transaction_description.lower() or \
       "petrol" in transaction_description.lower():
        return "Transport"
    # print("AI Mode: Defaulting to 'Uncategorized'")
    return "Uncategorized" # Default fallback

def get_spending_insights_ai(user_id: int) -> str:
    """
    Placeholder for AI-powered spending insights.
    """
    # In a real scenario, this would query user's transactions and generate insights.
    print(f"AI Mode: Generating spending insights for user_id: {user_id}")
    # Example: Fetch total spending for the month
    # total_spent_this_month = db.session.query(func.sum(Transaction.amount))\
    #     .filter(Transaction.user_id == user_id,\
    #             Transaction.type == 'expense',\
    #             func.strftime('%Y-%m', Transaction.date) == datetime.date.today().strftime('%Y-%m'))\
    #     .scalar()
    # if total_spent_this_month:
    #     return f"You've spent ${total_spent_this_month:.2f} this month. Consider reviewing your budget."
    return "AI spending insights are not yet implemented. Check back later!"

def forecast_spending_ai(user_id: int) -> str:
    """
    Placeholder for AI-powered spending forecast.
    """
    print(f"AI Mode: Generating spending forecast for user_id: {user_id}")
    return "AI spending forecast is not yet implemented. Future updates will include this feature!"

# --- Tax Item Routes ---
@app.route('/taxes', methods=['GET'])
@login_required
def taxes():
    tax_items = TaxItem.query.filter_by(user_id=g.user.id).order_by(TaxItem.date.desc()).all()
    return render_template('taxes.html', tax_items=tax_items, today_date=datetime.date.today().strftime('%Y-%m-%d'))

@app.route('/add_tax_item', methods=['POST'])
@login_required
def add_tax_item():
    description = request.form.get('description')
    amount_str = request.form.get('amount')
    date_str = request.form.get('date')
    deduction_type = request.form.get('deduction_type')

    if not all([description, amount_str, date_str]):
        flash('Description, Amount, and Date are required for tax items.', 'danger')
        return redirect(url_for('taxes'))

    try:
        amount = float(amount_str)
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid amount or date format for tax item.', 'danger')
        return redirect(url_for('taxes'))

    new_tax_item = TaxItem(
        user_id=g.user.id,
        description=description,
        amount=amount,
        date=date_obj,
        deduction_type=deduction_type
    )
    db.session.add(new_tax_item)
    db.session.commit()
    flash('Tax item added successfully!', 'success')
    return redirect(url_for('taxes'))

@app.route('/edit_tax_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_tax_item(item_id):
    item = TaxItem.query.get_or_404(item_id)

    if item.user_id != g.user.id:
        flash('You are not authorized to edit this tax item.', 'danger')
        return redirect(url_for('taxes'))

    if request.method == 'POST':
        description = request.form.get('description')
        amount_str = request.form.get('amount')
        date_str = request.form.get('date')
        deduction_type = request.form.get('deduction_type')

        if not all([description, amount_str, date_str]):
            flash('Description, Amount, and Date are required.', 'danger')
            return redirect(url_for('edit_tax_item', item_id=item_id))

        try:
            amount = float(amount_str)
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid amount or date format.', 'danger')
            return redirect(url_for('edit_tax_item', item_id=item_id))

        item.description = description
        item.amount = amount
        item.date = date_obj
        item.deduction_type = deduction_type

        db.session.commit()
        flash('Tax item updated successfully!', 'success')
        return redirect(url_for('taxes'))

    return render_template('edit_tax_item.html', item=item)

@app.route('/delete_tax_item/<int:item_id>', methods=['POST'])
@login_required
def delete_tax_item(item_id):
    item = TaxItem.query.get_or_404(item_id)
    if item.user_id != g.user.id:
        flash('You are not authorized to delete this tax item.', 'danger')
        return redirect(url_for('taxes'))

    db.session.delete(item)
    db.session.commit()
    flash('Tax item deleted successfully!', 'success')
    return redirect(url_for('taxes'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except IntegrityError: # Specific error for unique constraint violation
            db.session.rollback()
            flash('Username or email already exists.', 'danger')
        except Exception as e: # Catch other potential db errors
            db.session.rollback()
            flash(f'An error occurred during registration: {str(e)}', 'danger')
        return redirect(url_for('register')) # Redirect back to register page on error
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return redirect(url_for('login'))

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            app.logger.info("Login successful. Clearing session...")
            # session.clear() # Standard practice to clear session before login
            # app.logger.info("Session cleared.") # session.clear() might be too aggressive if other keys are needed.
                                            # For now, only user_id is set by this app.
                                            # If other session keys were used (e.g. CSRF token if forms had it),
                                            # clearing specific keys is safer: session.pop('user_id', None), session.pop('_csrf_token', None) etc.
                                            # Given current app, clearing user_id if it exists is sufficient.
            session.pop('user_id', None) # Clear previous user_id just in case, though usually new login overwrites.

            app.logger.info(f"Setting user_id in session: {user.id}")
            session['user_id'] = user.id
            app.logger.info(f"Session user_id set to: {session.get('user_id')}")

            app.logger.info("Setting session.permanent = True")
            session.permanent = True # Example: Make session permanent (cookie based)
            app.logger.info(f"Session permanent is: {session.permanent}")

            flash('Login successful!', 'success')
            index_url = url_for('index')
            app.logger.info(f"Redirecting to index page at {index_url}...")
            return redirect(index_url)
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None) # or session.clear() if you want to remove everything
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

def init_db():
    # Instance directory creation is now handled in the main block more robustly.
    # This function assumes the directory exists.
    with app.app_context(): # Essential for db operations
        db.create_all()
    print("Database tables created successfully.")

if __name__ == '__main__':
    # Ensure instance path exists before any db operation.
    # app.instance_path gives the absolute path to the instance folder.
    instance_folder_path = app.instance_path
    if not os.path.exists(instance_folder_path):
        try:
            os.makedirs(instance_folder_path)
            print(f"Created instance directory: {instance_folder_path}")
        except OSError as e:
            print(f"Error creating instance directory {instance_folder_path}: {e}")
            exit(1) # Exit if instance folder creation fails

    # db_path is globally defined using app.instance_path, so it's absolute.
    # We check for the existence of the database file at this absolute path.
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}, initializing...")
        init_db()
    else:
        print(f"Database found at {db_path}.")

    app.run(debug=True, host='0.0.0.0', port=8080)
