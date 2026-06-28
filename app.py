import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Trek, Booking, StaffProfile, init_admin
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-tma-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tma.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    init_admin()

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'staff':
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if user.status == 'blacklisted':
                flash('Your account has been blacklisted.')
                return redirect(url_for('login'))
            if user.status == 'pending':
                flash('Your account is pending admin approval.')
                return redirect(url_for('login'))
                
            login_user(user)
            return redirect(url_for('index'))
            
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role') # 'trekker' or 'staff'
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))
            
        status = 'pending' if role == 'staff' else 'approved'
        if role not in ['trekker', 'staff']:
            role = 'trekker'
            
        new_user = User(username=username, email=email, role=role, status=status)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        if role == 'staff':
            flash('Registration successful. Please wait for admin approval.')
        else:
            flash('Registration successful. You can now login.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return 'Unauthorized', 403
    return render_template('admin_dashboard.html')

@app.route('/staff/dashboard')
@login_required
def staff_dashboard():
    if current_user.role != 'staff':
        return 'Unauthorized', 403
    return render_template('staff_dashboard.html')

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.role != 'trekker':
        return 'Unauthorized', 403
    return render_template('user_dashboard.html')

if __name__ == '__main__':
    app.run(debug=True)
