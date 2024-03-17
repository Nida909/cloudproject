from flask import Flask, render_template, send_file, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
import os
import humanize
import shutil
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from datetime import date
from sqlalchemy.orm import joinedload

app = Flask(__name__, template_folder="templates")
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///file_storage.db'
app.config['UPLOAD_FOLDER'] = 'uploaded'
app.config['DIRECTORY_FOLDER'] = 'directories'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
migrate = Migrate(app, db)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  

    directories = db.relationship('Directory', backref='user', lazy=True)
    files = db.relationship('File', backref='user', lazy=True)
class Directory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_identifier = db.Column(db.String(50), nullable=False)  

    files = db.relationship('File', backref='directory', lazy=True)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    directory_id = db.Column(db.Integer, db.ForeignKey('directory.id'), nullable=False)
    size = db.Column(db.Integer, nullable=False)  
    def __init__(self, filename, user_id, directory_id, size):
        self.filename = filename
        self.user_id = user_id
        self.directory_id = directory_id
        self.size = size
class DailyUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    upload_usage = db.Column(db.Integer, default=0)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
def calculate_storage_used_by_user(user_id):
    user = User.query.get(user_id)
    total_storage_used = sum(file.size for file in user.files)
    return total_storage_used

def calculate_storage_used_by_user(user_id):
    user = User.query.get(user_id)
    total_storage_used = sum(file.size for file in user.files)
    return total_storage_used
@app.before_request
def reset_daily_upload():
    if current_user.is_authenticated:
        today = date.today()
        daily_upload = DailyUpload.query.filter_by(user_id=current_user.id, date=today).first()
        if not daily_upload:
            daily_upload = DailyUpload(user_id=current_user.id, date=today)
            db.session.add(daily_upload)
            db.session.commit()
        elif daily_upload.date < today:
            daily_upload.upload_usage = 0
            daily_upload.date = today
            db.session.commit()

@app.route('/list_users')
@login_required
def list_users():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))

    users = User.query.all()

    user_file_sizes = {}
    for user in users:
        user_file_sizes[user.id] = db.session.query(func.sum(File.size)).filter(File.user_id == user.id).scalar() or 0

    return render_template('list_users.html', users=users, user_file_sizes=user_file_sizes)


@app.route('/create_admin', methods=['GET'])
def create_admin():
    if request.remote_addr != '127.0.0.1':
        return 'Unauthorized', 403  
    
    admin = User.query.filter_by(username='admin').first()
    if admin:
        return 'Admin account already exists', 400
    
    admin = User(username='admin', password='admin', is_admin=True)
    db.session.add(admin)
    db.session.commit()
    
    return 'Admin account created successfully', 200

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('mylist'))
    return render_template('index.html')
@app.route('/delete_file/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    file_to_delete = File.query.get(file_id)
    if file_to_delete:
        directory_name_with_identifier = request.args.get('folder')  # Get folder name with identifier from the request args
        print("Directory name with identifier:", directory_name_with_identifier)
        parts = directory_name_with_identifier.split('_')
        print("Parts:", parts)
        if len(parts) == 2:
            directory_name, user_identifier = parts
            print("Directory name:", directory_name)
            print("User identifier:", user_identifier)
            file_path = os.path.join(app.config['DIRECTORY_FOLDER'], directory_name_with_identifier, file_to_delete.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            db.session.delete(file_to_delete)
            db.session.commit()
            flash('File deleted successfully.', 'success')
        else:
            flash('Invalid directory name.', 'error')
    else:
        flash('File not found.', 'error')
    return redirect(url_for('mylist'))


@app.route('/download_file/<path:folder>/<filename>')
@login_required
def download_file(folder, filename):
    directory_name, user_identifier = folder.split('_')  
    directory_name_with_identifier = f"{directory_name}_{user_identifier}"
    directory_path = os.path.join(app.config['DIRECTORY_FOLDER'], directory_name_with_identifier)
    file_path = os.path.join(directory_path, filename)
    if os.path.exists(file_path):
        return send_from_directory(directory_path, filename, as_attachment=True)
    else:
        flash('File not found.', 'error')
        return redirect(url_for('mylist'))



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('register'))
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            flash('Login successful.', 'success')
            if user.is_admin:
                return redirect(url_for('list_users'))
            else:
                return redirect(url_for('mylist'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    if request.method == 'POST':
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))
def calculate_total_storage_used(user_id):
    total_storage_used = 0
    user_files = File.query.filter_by(user_id=user_id).all()
    for file in user_files:
        if file.size is not None: 
            total_storage_used += file.size
    return total_storage_used

@app.route('/mylist')
@login_required
def mylist():
    directories = current_user.directories
    total_storage_used = calculate_total_storage_used(current_user.id)
    remaining_storage = 10 * 1024 * 1024 - total_storage_used
    total_storage_used_mb = humanize.naturalsize(total_storage_used, binary=True)
    remaining_storage_mb = humanize.naturalsize(remaining_storage, binary=True)
    return render_template('mylist.html', directories=directories, total_storage_used=total_storage_used_mb, remaining_storage=remaining_storage_mb)

@app.route('/create_folder', methods=['POST'])
@login_required
def create_folder():
    folder_name = request.form['folder_name']
    user_id = current_user.id
    user_identifier = current_user.username 
    directory_name = f"{folder_name}_{user_identifier}"  

    existing_directory = Directory.query.filter_by(name=folder_name, user_id=user_id).first()
    if existing_directory:
        flash('You already have a folder with this name.', 'error')
        return redirect(url_for('mylist'))

    directory_path = os.path.join(app.config['DIRECTORY_FOLDER'], directory_name)
    os.makedirs(directory_path)
    directory = Directory(name=folder_name, user_id=user_id, user_identifier=user_identifier)
    db.session.add(directory)
    db.session.commit()
    flash('Folder created successfully.', 'success')
    return redirect(url_for('mylist'))

def get_user_storage_used(user_id):
    return 0  
def calculate_storage_used_by_user(user_id):
    return get_user_storage_used(user_id)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        user_id = current_user.id
        remaining_storage = 10 * 1024 * 1024 - calculate_total_storage_used(user_id)
        today = date.today()
        daily_upload = DailyUpload.query.filter_by(user_id=user_id, date=today).first()
        if not daily_upload:
            daily_upload = DailyUpload(user_id=user_id, date=today)
            db.session.add(daily_upload)
        if daily_upload.upload_usage >= 25 * 1024 * 1024:
            flash('Daily upload bandwidth limit exceeded.', 'error')
            return redirect(url_for('mylist'))

        directory_name = request.form['directory']
        file = request.files['file']
        filename = secure_filename(file.filename)
        file_size = len(file.read())

        if file_size > remaining_storage:
            flash('File size exceeds the remaining storage limit.', 'error')
            return redirect(url_for('mylist'))

        if daily_upload.upload_usage + file_size > 25 * 1024 * 1024:
            flash('Daily upload bandwidth limit exceeded.', 'error')
            return redirect(url_for('mylist'))

        daily_upload.upload_usage += file_size
        db.session.commit()

        directory_name_with_identifier = f"{directory_name}_{current_user.username}"

        directory_path = os.path.join(app.config['DIRECTORY_FOLDER'], directory_name_with_identifier)
        if not os.path.exists(directory_path):
            flash('Selected folder does not exist.', 'error')
            return redirect(url_for('mylist'))

        file.seek(0)  
        file.save(os.path.join(directory_path, filename))
        
        directory = Directory.query.filter_by(name=directory_name, user_id=current_user.id).first()
        if not directory:
            directory = Directory(name=directory_name_with_identifier, user_id=current_user.id)
            db.session.add(directory)
            db.session.commit()

        new_file = File(filename=filename, user_id=current_user.id, directory_id=directory.id, size=file_size)
        db.session.add(new_file)
        db.session.commit()
        flash('File uploaded successfully.', 'success')
        return redirect(url_for('mylist'))

    return render_template('upload.html', directories=current_user.directories)

@app.route('/delete_directory/<int:directory_id>', methods=['POST'])
@login_required
def delete_directory(directory_id):
    directory = Directory.query.get(directory_id)
    if directory:
        for file in directory.files:
            file_path = os.path.join(app.config['DIRECTORY_FOLDER'], directory.name, file.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            db.session.delete(file)

        db.session.delete(directory)
        db.session.commit()
        
        directory_name_with_identifier = f"{directory.name}_{current_user.username}"
        directory_path = os.path.join(app.config['DIRECTORY_FOLDER'], directory_name_with_identifier)
        shutil.rmtree(directory_path)

        flash('Directory and all files inside it deleted successfully.', 'success')
    else:
        flash('Directory not found.', 'error')
    return redirect(url_for('mylist'))



@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        try:
            for directory in user.directories:
                directory_path = os.path.join(app.config['DIRECTORY_FOLDER'], f"{directory.name}_{user.username}")
                if os.path.exists(directory_path):
                    shutil.rmtree(directory_path)
                for file in directory.files:
                    db.session.delete(file)
                db.session.delete(directory)
            db.session.delete(user)
            db.session.commit()
            flash('User deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while deleting the user.', 'error')
            print(str(e))
    else:
        flash('User not found.', 'error')
    return redirect(url_for('list_users'))

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        flash('You are not authorized to access this page.', 'error')
        return redirect(url_for('list_users'))
    
    user = User.query.get(user_id)
    if user:
        if request.method == 'POST':
            user.username = request.form['username']
            user.password = request.form['password']
            db.session.commit()
            flash('User details updated successfully.', 'success')
            return redirect(url_for('list_users'))
        return render_template('edit_user.html', user=user)
    else:
        flash('User not found.', 'error')
        return redirect(url_for('list_users'))
if __name__ == '__main__':
    app.run(debug=True)
