from flask import Flask, render_template, request, redirect, url_for, session, flash, get_flashed_messages
import sqlite3
import os
import random
import string

app = Flask(__name__)
app.secret_key = 'your_secret_key'

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

    # Apply casing
    if use_upper and use_lower:
        base = base.capitalize()
    elif use_upper:
        base = base.upper()
    elif use_lower:
        base = base.lower()

    return base


# ----- ROUTES -----
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already taken."
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

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
                error = "Incorrect password."
        else:
            error = "User not found. Please register first."
    return render_template('login.html', error=error)

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

        # Save selected options for template
        if use_upper:
            selected_options.append('uppercase')
        if use_lower:
            selected_options.append('lowercase')
        if use_digits:
            selected_options.append('digits')
        if use_symbols:
            selected_options.append('symbols')

        # Generate password
        if memorable_selected:
            password = generate_memorable_password(use_upper, use_lower, use_digits, use_symbols)
        else:
            password = generate_random_password(length, use_upper, use_lower, use_digits, use_symbols)


        # Save to DB
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO passwords (user_id, password) VALUES (?, ?)", (session['user_id'], password))
        conn.commit()
        conn.close()

        # Flash + session store
        flash(password)
        session['memorable_selected'] = memorable_selected
        session['selected_options'] = selected_options

        return redirect(url_for('dashboard'))

    # GET method
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

# ----- MAIN -----
if __name__ == '__main__':
    app.run(debug=True)
