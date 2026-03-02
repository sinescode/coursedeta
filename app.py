import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re
import html

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///education.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    course_resources = db.relationship('CourseResource', backref='subject', lazy=True, cascade='all, delete-orphan')

class CourseResource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    videos = db.relationship('Video', backref='course_resource', lazy=True, cascade='all, delete-orphan')
    pdfs = db.relationship('PDF', backref='course_resource', lazy=True, cascade='all, delete-orphan')

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    course_resource_id = db.Column(db.Integer, db.ForeignKey('course_resource.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PDF(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    course_resource_id = db.Column(db.Integer, db.ForeignKey('course_resource.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password_hash = db.Column(db.String(200), nullable=False)

# Helper function to extract YouTube URL from iframe
def extract_youtube_url(iframe_code):
    # Pattern to match src attribute in iframe
    pattern = r'src=["\']([^"\']+)["\']'
    match = re.search(pattern, iframe_code)
    
    if match:
        url = match.group(1)
        # Extract video ID from various YouTube URL formats
        video_id = None
        
        # Pattern for youtube.com/embed/VIDEO_ID
        embed_match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]+)', url)
        if embed_match:
            video_id = embed_match.group(1)
        
        # Pattern for youtu.be/VIDEO_ID
        short_match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
        if short_match:
            video_id = short_match.group(1)
        
        # Pattern for watch?v=VIDEO_ID
        watch_match = re.search(r'[?&]v=([a-zA-Z0-9_-]+)', url)
        if watch_match:
            video_id = watch_match.group(1)
        
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
    
    # If no iframe pattern found, return original input (might already be a URL)
    return iframe_code.strip()

# Initialize admin password (change 'admin123' to your preferred password)
def init_admin():
    with app.app_context():
        db.create_all()
        if not Admin.query.first():
            admin = Admin(password_hash=generate_password_hash('admin123'))
            db.session.add(admin)
            db.session.commit()

# Routes
@app.route('/')
def home():
    subjects = Subject.query.all()
    return render_template('home.html', subjects=subjects)

@app.route('/subject/<int:subject_id>')
def subject_detail(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    return render_template('subject_detail.html', subject=subject)

@app.route('/course-resource/<int:resource_id>')
def course_resource_detail(resource_id):
    resource = CourseResource.query.get_or_404(resource_id)
    return render_template('resource_detail.html', resource=resource)

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        admin = Admin.query.first()
        
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid password!', 'danger')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    subjects = Subject.query.all()
    return render_template('admin/dashboard.html', subjects=subjects)

# Subject CRUD
@app.route('/admin/subject/add', methods=['POST'])
def add_subject():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    name = request.form['name']
    description = request.form.get('description', '')
    
    subject = Subject(name=name, description=description)
    db.session.add(subject)
    db.session.commit()
    
    flash('Subject added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/subject/edit/<int:id>', methods=['POST'])
def edit_subject(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    subject = Subject.query.get_or_404(id)
    subject.name = request.form['name']
    subject.description = request.form.get('description', '')
    db.session.commit()
    
    flash('Subject updated successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/subject/delete/<int:id>')
def delete_subject(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    subject = Subject.query.get_or_404(id)
    db.session.delete(subject)
    db.session.commit()
    
    flash('Subject deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# Course Resource CRUD
@app.route('/admin/resource/add', methods=['POST'])
def add_resource():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    title = request.form['title']
    subject_id = request.form['subject_id']
    
    resource = CourseResource(title=title, subject_id=subject_id)
    db.session.add(resource)
    db.session.commit()
    
    flash('Course Resource added successfully!', 'success')
    return redirect(url_for('admin_manage_resources', subject_id=subject_id))

@app.route('/admin/resources/<int:subject_id>')
def admin_manage_resources(subject_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    subject = Subject.query.get_or_404(subject_id)
    return render_template('admin/resources.html', subject=subject)

@app.route('/admin/resource/edit/<int:id>', methods=['POST'])
def edit_resource(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    resource = CourseResource.query.get_or_404(id)
    resource.title = request.form['title']
    db.session.commit()
    
    flash('Course Resource updated successfully!', 'success')
    return redirect(url_for('admin_manage_resources', subject_id=resource.subject_id))

@app.route('/admin/resource/delete/<int:id>')
def delete_resource(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    resource = CourseResource.query.get_or_404(id)
    subject_id = resource.subject_id
    db.session.delete(resource)
    db.session.commit()
    
    flash('Course Resource deleted successfully!', 'success')
    return redirect(url_for('admin_manage_resources', subject_id=subject_id))

# Video CRUD
@app.route('/admin/video/add', methods=['POST'])
def add_video():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    title = request.form['title']
    url_input = request.form['url']
    resource_id = request.form['resource_id']
    
    # Convert iframe to YouTube URL
    clean_url = extract_youtube_url(url_input)
    
    video = Video(title=title, url=clean_url, course_resource_id=resource_id)
    db.session.add(video)
    db.session.commit()
    
    flash('Video added successfully!', 'success')
    return redirect(url_for('admin_manage_content', resource_id=resource_id))

@app.route('/admin/content/<int:resource_id>')
def admin_manage_content(resource_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    resource = CourseResource.query.get_or_404(resource_id)
    return render_template('admin/content.html', resource=resource)

@app.route('/admin/video/edit/<int:id>', methods=['POST'])
def edit_video(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    video = Video.query.get_or_404(id)
    video.title = request.form['title']
    url_input = request.form['url']
    video.url = extract_youtube_url(url_input)
    db.session.commit()
    
    flash('Video updated successfully!', 'success')
    return redirect(url_for('admin_manage_content', resource_id=video.course_resource_id))

@app.route('/admin/video/delete/<int:id>')
def delete_video(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    video = Video.query.get_or_404(id)
    resource_id = video.course_resource_id
    db.session.delete(video)
    db.session.commit()
    
    flash('Video deleted successfully!', 'success')
    return redirect(url_for('admin_manage_content', resource_id=resource_id))

# PDF CRUD
@app.route('/admin/pdf/add', methods=['POST'])
def add_pdf():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    title = request.form['title']
    url = request.form['url']
    resource_id = request.form['resource_id']
    
    pdf = PDF(title=title, url=url, course_resource_id=resource_id)
    db.session.add(pdf)
    db.session.commit()
    
    flash('PDF added successfully!', 'success')
    return redirect(url_for('admin_manage_content', resource_id=resource_id))

@app.route('/admin/pdf/edit/<int:id>', methods=['POST'])
def edit_pdf(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    pdf = PDF.query.get_or_404(id)
    pdf.title = request.form['title']
    pdf.url = request.form['url']
    db.session.commit()
    
    flash('PDF updated successfully!', 'success')
    return redirect(url_for('admin_manage_content', resource_id=pdf.course_resource_id))

@app.route('/admin/pdf/delete/<int:id>')
def delete_pdf(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    pdf = PDF.query.get_or_404(id)
    resource_id = pdf.course_resource_id
    db.session.delete(pdf)
    db.session.commit()
    
    flash('PDF deleted successfully!', 'success')
    return redirect(url_for('admin_manage_content', resource_id=resource_id))

if __name__ == '__main__':
    init_admin()
    app.run(debug=True, port=5000)
