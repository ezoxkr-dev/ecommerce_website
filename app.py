from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
from psycopg2.errors import UniqueViolation as IntegrityError
import requests
import smtplib
from email.mime.text import MIMEText
import random
import string
import secrets
from datetime import datetime, timedelta
from flask_wtf.csrf import CSRFProtect
import bleach
import os
import random
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32) # Stronger unique key
csrf = CSRFProtect(app)

# Session Hardening
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False, # Set to True if using HTTPS
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2)
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_CHAT_IDS = [cid.strip() for cid in TELEGRAM_CHAT_ID.split(',')] if TELEGRAM_CHAT_ID else []
# SMTP Configuration for Admin Notifications (Sender & Receiver)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
ADMIN_SMTP_USER = os.getenv("ADMIN_SMTP_USER", "")
ADMIN_SMTP_PASS = os.getenv("ADMIN_SMTP_PASS", "")

# SMTP Configuration for Customer Emails (Sender)
CUSTOMER_SMTP_USER = os.getenv("CUSTOMER_SMTP_USER", "")
CUSTOMER_SMTP_PASS = os.getenv("CUSTOMER_SMTP_PASS", "") # <-- ADD GADGET.EZOX APP PASSWORD HERE

# Cloudflare Turnstile Configuration
TURNSTILE_SITEKEY = os.getenv("TURNSTILE_SITEKEY", "")
TURNSTILE_SECRET = os.getenv("TURNSTILE_SECRET", "")

def verify_turnstile(token):
    if not token:
        return False
    try:
        response = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={'secret': TURNSTILE_SECRET, 'response': token}
        )
        return response.json().get('success', False)
    except:
        return False

class DBConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, vars=None):
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Convert sqlite ? to postgres %s
        query = query.replace('?', '%s')
        cur.execute(query, vars)
        return cur

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    return DBConnectionWrapper(conn)

def send_telegram_notice(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        # Combine static targets with the primary chat ID
        targets = [
            {"chat_id": "-1003968649736", "message_thread_id": 1},
            {"chat_id": "-1003968649736", "message_thread_id": 2}
        ]
        # Add all primary chat IDs parsed from .env
        for cid in TELEGRAM_CHAT_IDS:
            if cid:
                targets.append({"chat_id": cid})
        for target in targets:
            payload = {
                "chat_id": target["chat_id"],
                "text": message
            }
            if "message_thread_id" in target:
                payload["message_thread_id"] = target["message_thread_id"]
            
            requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram Error:", e)

def send_email_notice(subject, body, to_email=None):
    is_to_admin = (to_email is None)
    if is_to_admin:
        to_email = ADMIN_EMAIL
        sender_email = ADMIN_SMTP_USER
        sender_pass = ADMIN_SMTP_PASS
    else:
        sender_email = CUSTOMER_SMTP_USER
        sender_pass = CUSTOMER_SMTP_PASS
        if not sender_pass:
            print("Email Error: CUSTOMER_SMTP_PASS is not set. Cannot send email to customer.")
            return

    try:
        # Always replace newlines with <br> so emails preserve the formatting from the textarea
        body_html = body.replace('\n', '<br>')
        msg = MIMEText(body_html, 'html')
        msg['Subject'] = subject
        msg['From'] = f"Ezox Store <{sender_email}>"
        msg['To'] = to_email
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_pass)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Email Error:", e)

# Security Headers Middleware
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Content Security Policy (Basic)
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com https://code.jquery.com https://cdn.datatables.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.datatables.net; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; frame-src 'self' https://challenges.cloudflare.com https://www.youtube.com; img-src 'self' data:;"
    return response

import re

def auto_buttonize(text):
    if not text: return ""
    if '<a ' in text.lower():
        return text  # Skip auto-formatting if admin already provided HTML links
        
    url_pattern = re.compile(r'(https?://[^\s<"\'>]+)')
    def repl(match):
        url = match.group(1)
        if 't.me' in url:
            return f'<a href="{url}" class="btn btn-sm-inline btn-primary btn-telegram" target="_blank"><i class="fa-brands fa-telegram"></i> Telegram</a>'
        elif 'discord' in url:
            return f'<a href="{url}" class="btn btn-sm-inline btn-primary btn-discord" target="_blank"><i class="fa-brands fa-discord"></i> Discord</a>'
        else:
            return f'<a href="{url}" class="btn btn-sm-inline btn-primary" target="_blank"><i class="fa-solid fa-download"></i> Download</a>'
    return url_pattern.sub(repl, text)

@app.template_filter('sanitize')
def sanitize_html(text):
    if not text:
        return ""
    text = auto_buttonize(text)
    text = text.replace('\n', '<br>')
    allowed_tags = ['b', 'i', 'u', 'strong', 'em', 'p', 'br', 'span', 'a']
    allowed_attrs = {
        'a': ['href', 'class', 'target'],
        'i': ['class'],
        'span': ['class']
    }
    return bleach.clean(text, tags=allowed_tags, attributes=allowed_attrs, strip=True)

@app.route('/')
def index():
    images_dir = os.path.join(app.root_path, 'static', 'images')
    images = []
    if os.path.exists(images_dir):
        for f in os.listdir(images_dir):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                images.append(f"images/{f}")
                
    return render_template('index.html', gallery_images=images)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        turnstile_response = request.form.get('cf-turnstile-response')
        if not verify_turnstile(turnstile_response):
            flash('CAPTCHA verification failed.', 'error')
            return redirect(url_for('register'))

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        hashed_pw = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                         (username, email, hashed_pw))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            flash('Username or email already exists.', 'error')
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        turnstile_response = request.form.get('cf-turnstile-response')
        if not verify_turnstile(turnstile_response):
            flash('CAPTCHA verification failed.', 'error')
            return redirect(url_for('login'))

        username = request.form['username']
        password = request.form['password']
        
        # Simple Rate Limiting check
        attempts = session.get('login_attempts', 0)
        if attempts >= 5:
            last_attempt = session.get('last_attempt_time')
            if last_attempt:
                last_time = datetime.fromisoformat(last_attempt)
                if datetime.now() - last_time < timedelta(minutes=15):
                    flash('Too many failed attempts. Please wait 15 minutes.', 'error')
                    return redirect(url_for('login'))
                else:
                    session['login_attempts'] = 0 # Reset after timeout
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['login_attempts'] = 0 # Reset on success
            flash('Logged in successfully!', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin'))
            return redirect(url_for('dashboard'))
        else:
            session['login_attempts'] = attempts + 1
            session['last_attempt_time'] = datetime.now().isoformat()
            flash('Invalid credentials.', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user:
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(hours=1)
            conn.execute('UPDATE users SET reset_token = ?, reset_expiry = ? WHERE id = ?', (token, expiry, user['id']))
            conn.commit()
            
            reset_url = url_for('reset_password', token=token, _external=True)
            body = f"Click the link to reset your password: {reset_url}"
            send_email_notice("Password Reset Request", body, to_email=email)
            print(f"Password reset link: {reset_url}")
            
        conn.close()
        flash('If your email is registered, a password reset link has been sent.', 'info')
        return redirect(url_for('login'))
        
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE reset_token = ?', (token,)).fetchone()
    
    if not user:
        conn.close()
        flash('Invalid reset token.', 'error')
        return redirect(url_for('forgot_password'))
        
    if isinstance(user['reset_expiry'], str):
        expiry_time = datetime.strptime(user['reset_expiry'].split('.')[0], '%Y-%m-%d %H:%M:%S')
    else:
        expiry_time = user['reset_expiry']

    if expiry_time < datetime.now():
        conn.close()
        flash('Expired reset token.', 'error')
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        password = request.form['password']
        hashed_pw = generate_password_hash(password)
        
        conn.execute('UPDATE users SET password_hash = ?, reset_token = NULL, reset_expiry = NULL WHERE id = ?', (hashed_pw, user['id']))
        conn.commit()
        conn.close()
        
        flash('Your password has been updated! You can now login.', 'success')
        return redirect(url_for('login'))
        
    conn.close()
    return render_template('reset_password.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC', (session['user_id'],)).fetchall()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    return render_template('dashboard.html', orders=orders, user=user)

@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    orders = conn.execute('SELECT orders.*, users.username FROM orders JOIN users ON orders.user_id = users.id ORDER BY orders.created_at DESC').fetchall()
    conn.close()
    
    ratings = [o['rating'] for o in orders if o['rating'] is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

    metrics = {
        'total_users': len(users),
        'total_orders': len(orders),
        'pending_orders': sum(1 for o in orders if o['status'] == 'Pending'),
        'completed_orders': sum(1 for o in orders if o['status'] == 'Completed'),
        'avg_rating': round(avg_rating, 1)
    }
    
    return render_template('admin.html', users=users, orders=orders, metrics=metrics)

@app.route('/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('index'))
        
    new_status = request.form.get('status')
    admin_message = request.form.get('admin_message', '').strip()

    if new_status in ['Pending', 'Completed', 'Rejected']:
        conn = get_db_connection()
        order = conn.execute('SELECT orders.*, users.email FROM orders JOIN users ON orders.user_id = users.id WHERE orders.id = ?', (order_id,)).fetchone()
        
        if order:
            if new_status == 'Completed':
                conn.execute('UPDATE orders SET status = ?, admin_message = ? WHERE id = ?', (new_status, admin_message, order_id))
                # Always send email on completion, use a default if message is empty
                email_body = admin_message if admin_message else "Your order has been marked as completed. Please check your dashboard for details."
                send_email_notice(f"Your order is completed. Order ID : {order['order_id']}", email_body, to_email=order['email'])
            else:
                conn.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
                
            conn.commit()
            send_telegram_notice(f"⚠️ Order Status Updated\n\nID: {order['order_id']}\nProduct: {order['product']}\nNew Status: {new_status}\n\nCheck Admin Panel for details.")
            flash(f"Order ID {order['order_id']} status updated to {new_status}.", 'success')
        
        conn.close()
    else:
        flash('Invalid status provided.', 'error')
        
    return redirect(url_for('admin'))

@app.route('/submit_review/<int:order_id>', methods=['POST'])
def submit_review(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    rating = request.form.get('rating', type=int)
    review_text = request.form.get('review', '').strip()
    
    if not rating or rating < 1 or rating > 5:
        flash('Invalid rating.', 'error')
        return redirect(url_for('dashboard'))
        
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE id = ? AND user_id = ? AND status = "Completed"', (order_id, session['user_id'])).fetchone()
    
    if not order:
        flash('Order not found or not eligible for review.', 'error')
        conn.close()
        return redirect(url_for('dashboard'))
        
    if order['rating'] is not None:
        flash('You have already reviewed this order.', 'error')
        conn.close()
        return redirect(url_for('dashboard'))
        
    conn.execute('UPDATE orders SET rating = ?, review = ? WHERE id = ?', (rating, review_text, order_id))
    conn.commit()
    conn.close()
    
    flash('Thank you for your review!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('You must be logged in to purchase.', 'error')
        return redirect(url_for('login'))
        
    product = request.args.get('product', 'Ezox Bypass Package')
    
    if request.method == 'POST':
        payment_method = request.form['payment_method']
        code = request.form['code']
        
        # Generate unique order ID
        order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        conn = get_db_connection()
        user_data = conn.execute('SELECT email FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        user_email = user_data['email'] if user_data else 'Unknown Email'
        
        conn.execute('INSERT INTO orders (order_id, user_id, product, payment_method, code) VALUES (?, ?, ?, ?, ?)',
                     (order_id, session['user_id'], product, payment_method, code))
        conn.commit()
        conn.close()
        
        # Notifications
        msg = (
            f"🛒 New Order Received!\n\n"
            f"📦 Order Details:\n"
            f"- Order ID: {order_id}\n"
            f"- Product: {product}\n\n"
            f"👤 Customer Details:\n"
            f"- Username: {session['username']}\n"
            f"- Email: {user_email}\n\n"
            f"💳 Payment Info:\n"
            f"- Method: {payment_method}\n"
            f"- Code/TxHash: {code}"
        )
        send_telegram_notice(msg)
        send_email_notice(f"New Ezox Payment: {order_id}", msg)
        
        flash('Payment submitted! Awaiting admin approval.', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('checkout.html', product=product)

if __name__ == '__main__':
    app.run(port=8000, debug=True)
