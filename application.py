from flask import Flask, render_template, redirect, url_for, session, request, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import mysql.connector
import os
import re


# -------- APP CONFIG -------- #
application = Flask(__name__)
application.secret_key = 'your_secret_key_here'


# -------- DATABASE CONNECTION -------- #
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='Paronasib@123',
        database='vision_to_voice'
    )


# -------- MAIL CONFIGURATION -------- #
application.config['MAIL_SERVER'] = ''
application.config['MAIL_PORT'] = 
application.config['MAIL_USE_SSL'] = True
application.config['MAIL_USERNAME'] = ''
application.config['MAIL_PASSWORD'] = ''
application.config['MAIL_DEFAULT_SENDER'] = ''


mail = Mail(application)
s = URLSafeTimedSerializer(application.secret_key)


# -------- UPLOAD CONFIG -------- #
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
application.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# -------- IMPORT YOUR MODELS -------- #
from narration_model import extract_images_from_pdf, generate_combined_caption
from audio_generator import generate_audio
from google_drive import upload_to_drive, get_audio_url


# ---------------- ROUTES ---------------- #


@application.route('/')
def landing_page():
    return render_template('landing_page.html')


@application.route('/about_us')
def about_us():
    return render_template('about_us.html')


@application.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        try:
            msg = Message(
                subject=f'Narratoons Contact Form - Message from {name}',
                recipients=['narratoons5@gmail.com'],
                reply_to=email
            )
            
            msg.body = f"""
New Contact Form Submission from Narratoons Website

From: {name}
Email: {email}

Message:
{message}

---
Sent from Narratoons Contact Form
Reply directly to this email to respond to {name}.
"""
            
            mail.send(msg)
            flash('Thank you for contacting us! We will get back to you soon.', 'success')
            return redirect(url_for('contact'))
            
        except Exception as e:
            print(f"Error sending email: {e}")
            flash('Sorry, there was an error sending your message. Please try again later.', 'error')
            return redirect(url_for('contact'))
    
    return render_template('contact.html')


# -------- SIGN IN / SIGN UP / PASSWORD ROUTES -------- #
@application.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!')
            return redirect(url_for('loading'))
        else:
            flash('Invalid username or password')
    return render_template('sign_in.html')


@application.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('sign_up.html')

        hashed_password = generate_password_hash(password)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s,%s,%s)",
                           (username, email, hashed_password))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Account created successfully! Please sign in.')
            return redirect(url_for('sign_in'))
        except mysql.connector.IntegrityError:
            flash('Email or username already exists!')
            return render_template('sign_up.html')
    return render_template('sign_up.html')


@application.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, email FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            try:
                token = s.dumps(email, salt='password-reset-salt')
                reset_link = url_for('reset_password', token=token, _external=True)
                msg = Message(
                    subject="Narratoons Password Reset",
                    recipients=[email],
                    body=f"Hi {user['username']},\n\nClick below to reset your password:\n{reset_link}\n\nThis link is valid for 1 hour."
                )
                mail.send(msg)
                flash('Password reset link has been sent to your email.')
            except Exception as e:
                flash(f"Failed to send email. Error: {str(e)}")
        else:
            flash('If this email exists, a password reset link has been sent.')
    return render_template('forgot-password.html')


@application.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600)
    except Exception:
        flash('The password reset link is invalid or expired.')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash("Passwords do not match.")
            return render_template('reset_password.html', token=token)

        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Password reset successful! Please sign in.")
        return redirect(url_for('sign_in'))

    return render_template('reset_password.html', token=token)


# -------- LOADING & WELCOME -------- #
@application.route('/loading')
def loading():
    if 'user_id' not in session:
        flash('Please sign in to continue.')
        return redirect(url_for('sign_in'))
    return render_template('loading.html')


@application.route('/welcome')
def welcome():
    if 'user_id' not in session:
        flash('Please sign in to continue.')
        return redirect(url_for('sign_in'))
    return render_template('welcome.html', username=session['username'])


# -------- MAIN & UPLOAD -------- #
@application.route('/main')
def main():
    if 'user_id' not in session:
        flash('Please sign in to continue.')
        return redirect(url_for('sign_in'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, title, image_path, audio_path, caption_text 
        FROM comics 
        WHERE user_id = %s
    """, (session['user_id'],))
    comics = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('main.html', username=session['username'], comics=comics)


@application.route('/comic_upload', methods=['GET', 'POST'])
def comic_upload():
    if 'user_id' not in session:
        flash('Please sign in to continue.')
        return redirect(url_for('sign_in'))

    if request.method == 'POST':
        file_name = request.form.get('audioFileName')
        file = request.files.get('audioFile')

        if not file_name or not file:
            flash('Missing file or name')
            return redirect(request.url)

        if not file.filename.lower().endswith('.pdf'):
            flash('Only PDF files allowed')
            return redirect(request.url)

        safe_filename = secure_filename(file.filename)
        save_path = os.path.join(application.static_folder, 'uploads', safe_filename)
        file.save(save_path)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO comics (user_id, title, file_path) VALUES (%s, %s, %s)",
            (session['user_id'], file_name, f'static/uploads/{safe_filename}')
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash('File uploaded successfully!')
        return redirect(url_for('main'))

    return render_template('comic_upload.html')


# -------- COMIC PREVIEW -------- #
@application.route('/comic_preview/<int:comic_id>')
def comic_preview(comic_id):
    if 'user_id' not in session:
        flash('Please sign in to continue.')
        return redirect(url_for('sign_in'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM comics WHERE id = %s AND user_id = %s", (comic_id, session['user_id']))
    comic = cursor.fetchone()
    cursor.close()
    conn.close()

    if not comic:
        flash("Comic not found!")
        return redirect(url_for('main'))

    # Get cleaned text directly from database
    cleaned_text = comic.get('caption_text')
    
    # Remove any remaining speaker tags (in case old data exists)
    if cleaned_text:
        cleaned_text = re.sub(r'\b(NARRATOR|MALE|MALE2|FEMALE|CHILD|OLD_MALE)\s+', '', cleaned_text)

    return render_template('comic_preview.html', 
                         comic=comic, 
                         cleaned_text=cleaned_text)




# -------- COMIC ACTIONS -------- #
@application.route('/favourite/<int:comic_id>', methods=['POST'])
def favourite_comic(comic_id):
    if 'user_id' not in session:
        flash('Please sign in to continue.')
        return redirect(url_for('sign_in'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE comics 
        SET created_at = NOW() 
        WHERE id = %s AND user_id = %s
    """, (comic_id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Comic marked as favourite!", "success")
    return redirect(url_for('comic_preview', comic_id=comic_id))


# -------- CONVERT COMIC TO AUDIO (UPDATED) -------- #
@application.route('/convert_comic/<int:comic_id>', methods=['POST'])
def convert_comic(comic_id):
    if 'user_id' not in session:
        flash('Please sign in to continue.')
        return redirect(url_for('sign_in'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM comics WHERE id = %s AND user_id = %s", (comic_id, session['user_id']))
    comic = cursor.fetchone()

    if not comic:
        cursor.close()
        conn.close()
        flash("Comic not found!")
        return redirect(url_for('main'))

    pdf_path = comic['file_path']
    
    try:
        # Extract images from PDF
        print(f"Processing PDF: {pdf_path}")
        images = extract_images_from_pdf(pdf_path)
        
        # Generate narration text
        narration_text = generate_combined_caption(images)
        
        # Generate audio from narration
        pdf_basename = os.path.basename(pdf_path)
        pdf_name = os.path.splitext(pdf_basename)[0]
        audio_path = generate_audio(narration_text, pdf_name)
        
        # Get the cleaned text (read from the saved cleaned file)
        cleaned_text_filename = f"{pdf_name}_cleaned.txt"
        cleaned_text_path = os.path.join('static', 'output', cleaned_text_filename)
        
        cleaned_text = None
        if os.path.exists(cleaned_text_path):
            with open(cleaned_text_path, 'r', encoding='utf-8') as f:
                cleaned_text = f.read()
        
        # Update database with both audio path AND cleaned text
        cursor.execute(
            "UPDATE comics SET audio_path = %s, caption_text = %s WHERE id = %s",
            (audio_path, cleaned_text, comic_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Comic converted to audio successfully!')
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        cursor.close()
        conn.close()
        flash(f'Error converting comic: {str(e)}')
    
    return redirect(url_for('comic_preview', comic_id=comic_id))

# -------- PLAY AUDIO -------- #
@application.route('/play_audio/<int:comic_id>')
def play_audio(comic_id):
    if 'user_id' not in session:
        flash('Please sign in to continue.')
        return redirect(url_for('sign_in'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT audio_path FROM comics WHERE id=%s AND user_id=%s", (comic_id, session['user_id']))
    comic = cursor.fetchone()
    cursor.close()
    conn.close()

    if not comic or not comic['audio_path']:
        flash("Audio not available!")
        return redirect(url_for('comic_preview', comic_id=comic_id))

    # If it's a Google Drive URL, redirect to it
    if comic['audio_path'].startswith('http'):
        return redirect(comic['audio_path'])
    
    # Otherwise serve from local static/output folder
    return send_from_directory(
        directory=os.path.join(application.static_folder, 'output'),
        path=os.path.basename(comic['audio_path'])
    )


# -------- DELETE COMIC -------- #
@application.route('/delete_comic/<int:comic_id>', methods=['POST'])
def delete_comic(comic_id):
    if 'user_id' not in session:
        flash('Please sign in to continue.')
        return redirect(url_for('sign_in'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM comics WHERE id = %s AND user_id = %s", (comic_id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Comic deleted successfully!")
    return redirect(url_for('main'))


# -------- LOGOUT -------- #
@application.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('sign_in'))


# -------- RUN APP -------- #
if __name__ == '__main__':
    application.run(debug=True)

