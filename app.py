from flask import Flask, render_template, request, redirect, url_for, session, flash, get_flashed_messages
import sqlite3
import os
import random
import string
import re
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

# ----- APP SETUP -----
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Load environment variables from .env
load_dotenv()
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
FROM_EMAIL = os.getenv('FROM_EMAIL')

# ----- DATABASE INITIALIZATION -----
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS passwords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        password TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

init_db()

# ----- PASSWORD GENERATORS -----
def generate_random_password(length, use_upper, use_lower, use_digits, use_symbols):
    chars = ''
    if use_upper:
        chars += string.ascii_uppercase
    if use_lower:
        chars += string.ascii_lowercase
    if use_digits:
        chars += string.digits
    if use_symbols:
        chars += string.punctuation

    if not chars:
        return "Please select at least one character type."

    return ''.join(random.choice(chars) for _ in range(length))

def generate_memorable_password(use_upper, use_lower, use_digits, use_symbols):
    adjectives = ['brave', 'happy', 'smart', 'silly', 'cool', 'wild', 'clever', 'fierce']
    nouns = ['tiger', 'mountain', 'river', 'sky', 'ocean', 'robot', 'falcon', 'wizard']
    symbols = '!@#$%&'

    adj = random.choice(adjectives)
    noun = random.choice(nouns)
    number = str(random.randint(10, 99)) if use_digits else ''
    sym = random.choice(symbols) if use_symbols else ''

    base = adj + noun + sym + number

    if use_upper and use_lower:
        base = base.capitalize()
    elif use_upper:
        base = base.upper()
    elif use_lower:
        base = base.lower()

    return base

# ----- EMAIL FUNCTION -----
def send_otp_email(to_email, otp):
    if not SENDGRID_API_KEY or not FROM_EMAIL:
        print("Missing SendGrid config.")
        return False

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject='Your OTP for Password Reset',
        html_content=f'<p>Your OTP is: <strong>{otp}</strong></p>'
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        return True
    except Exception as e:
        print(f"SendGrid error: {e}")
        return False

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_strong_password(password):
    return re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password)


# ----- ROUTES -----
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not is_valid_email(username):
            flash("⚠️ Email address must be in correct format (example: user@gmail.com)")
            return redirect(url_for('register'))

        if not is_strong_password(password):
            flash("⚠️ Password must be at least 8 characters long and include: 1 uppercase letter, 1 lowercase letter, 1 number, and 1 special character.")
            return redirect(url_for('register'))

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("⚠️ This email is already registered. Please login or use another.")
            return redirect(url_for('register'))
        conn.close()
        flash("✅ Registered successfully. Please login.")
        return redirect(url_for('login'))

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not is_valid_email(username):
            flash("⚠️ Please enter a valid email address.")
            return redirect(url_for('login'))

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user:
            if user[1] == password:
                session['user_id'] = user[0]
                session['username'] = username
                return redirect(url_for('dashboard'))
            else:
                flash("⚠️ Incorrect password.")
        else:
            flash("⚠️ User not found. Please register first.")
    return render_template('login.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    generated_password = None
    memorable_selected = False
    selected_options = []

    if request.method == 'POST':
        length = int(request.form.get('length', 12))
        use_upper = 'uppercase' in request.form
        use_lower = 'lowercase' in request.form
        use_digits = 'digits' in request.form
        use_symbols = 'symbols' in request.form
        memorable_selected = 'memorable' in request.form

        if use_upper:
            selected_options.append('uppercase')
        if use_lower:
            selected_options.append('lowercase')
        if use_digits:
            selected_options.append('digits')
        if use_symbols:
            selected_options.append('symbols')

        if memorable_selected:
            password = generate_memorable_password(use_upper, use_lower, use_digits, use_symbols)
        else:
            password = generate_random_password(length, use_upper, use_lower, use_digits, use_symbols)

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO passwords (user_id, password) VALUES (?, ?)", (session['user_id'], password))
        conn.commit()
        conn.close()

        flash(password)
        session['memorable_selected'] = memorable_selected
        session['selected_options'] = selected_options

        return redirect(url_for('dashboard'))

    generated_passwords = get_flashed_messages()
    generated_password = generated_passwords[0] if generated_passwords else None
    memorable_selected = session.pop('memorable_selected', False)
    selected_options = session.pop('selected_options', [])

    return render_template('dashboard.html',
                           username=session['username'],
                           generated_password=generated_password,
                           memorable_selected=memorable_selected,
                           selected_options=selected_options)

@app.route('/view_passwords')
def view_passwords():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, password, created_at FROM passwords WHERE user_id = ?", (session['user_id'],))
    passwords = c.fetchall()
    conn.close()
    return render_template('view_passwords.html', passwords=passwords)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ----- FORGOT PASSWORD FLOW -----
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username'].strip()
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user:
            otp = str(random.randint(100000, 999999))
            session['reset_username'] = username
            session['otp'] = otp
            send_otp_email(username, otp)
            return redirect(url_for('otp_verification'))
        else:
            flash("User not found.")
    return render_template('forgot_password.html')

@app.route('/otp_verification', methods=['GET', 'POST'])
def otp_verification():
    if request.method == 'POST':
        entered_otp = request.form['otp'].strip()
        if entered_otp == session.get('otp'):
            return redirect(url_for('reset_password'))
        else:
            flash("Invalid OTP. Please try again.")
    return render_template('otp_verification.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form['new_password'].strip()
        username = session.get('reset_username')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
        conn.commit()
        conn.close()

        session.pop('reset_username', None)
        session.pop('otp', None)

        flash("Password reset successful. Please login.")
        return redirect(url_for('login'))

    return render_template('reset_password.html')

# ----- MAIN -----
if __name__ == '__main__':
    app.run(debug=True)
