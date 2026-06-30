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
    total_treks = Trek.query.count()
    total_users = User.query.filter_by(role='trekker').count()
    total_staff = User.query.filter_by(role='staff').count()
    total_bookings = Booking.query.count()
    return render_template('admin_dashboard.html', total_treks=total_treks, 
                           total_users=total_users, total_staff=total_staff, 
                           total_bookings=total_bookings)

@app.route('/admin/treks', methods=['GET'])
@login_required
def admin_manage_treks():
    if current_user.role != 'admin':
        return 'Unauthorized', 403
    treks = Trek.query.all()
    staff_members = User.query.filter_by(role='staff', status='approved').all()
    return render_template('admin_manage_treks.html', treks=treks, staff_members=staff_members)

@app.route('/admin/treks/create', methods=['POST'])
@login_required
def admin_create_trek():
    if current_user.role != 'admin':
        return 'Unauthorized', 403
    name = request.form.get('name')
    location = request.form.get('location')
    difficulty = request.form.get('difficulty')
    duration = request.form.get('duration')
    total_slots = request.form.get('total_slots')
    assigned_staff_id = request.form.get('assigned_staff_id')
    if not assigned_staff_id:
        assigned_staff_id = None
        
    new_trek = Trek(
        name=name, location=location, difficulty=difficulty, 
        duration=int(duration), total_slots=int(total_slots), 
        available_slots=int(total_slots), assigned_staff_id=assigned_staff_id
    )
    db.session.add(new_trek)
    db.session.commit()
    flash('Trek created successfully!')
    return redirect(url_for('admin_manage_treks'))

@app.route('/admin/treks/<int:trek_id>/edit', methods=['POST'])
@login_required
def admin_edit_trek(trek_id):
    if current_user.role != 'admin':
        return 'Unauthorized', 403
    trek = Trek.query.get_or_404(trek_id)
    trek.name = request.form.get('name')
    trek.location = request.form.get('location')
    trek.difficulty = request.form.get('difficulty')
    trek.duration = int(request.form.get('duration'))
    new_total_slots = int(request.form.get('total_slots'))
    diff = new_total_slots - trek.total_slots
    trek.total_slots = new_total_slots
    trek.available_slots += diff
    assigned_staff_id = request.form.get('assigned_staff_id')
    trek.assigned_staff_id = assigned_staff_id if assigned_staff_id else None
    
    db.session.commit()
    flash('Trek updated successfully!')
    return redirect(url_for('admin_manage_treks'))

@app.route('/admin/treks/<int:trek_id>/delete', methods=['POST'])
@login_required
def admin_delete_trek(trek_id):
    if current_user.role != 'admin':
        return 'Unauthorized', 403
    trek = Trek.query.get_or_404(trek_id)
    db.session.delete(trek)
    db.session.commit()
    flash('Trek deleted successfully!')
    return redirect(url_for('admin_manage_treks'))

@app.route('/admin/users', methods=['GET'])
@login_required
def admin_manage_users():
    if current_user.role != 'admin':
        return 'Unauthorized', 403
    users = User.query.filter(User.role != 'admin').all()
    return render_template('admin_manage_users.html', users=users)

@app.route('/admin/users/<int:user_id>/approve', methods=['POST'])
@login_required
def admin_approve_user(user_id):
    if current_user.role != 'admin':
        return 'Unauthorized', 403
    user = User.query.get_or_404(user_id)
    user.status = 'approved'
    db.session.commit()
    flash(f'User {user.username} approved successfully!')
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/users/<int:user_id>/blacklist', methods=['POST'])
@login_required
def admin_blacklist_user(user_id):
    if current_user.role != 'admin':
        return 'Unauthorized', 403
    user = User.query.get_or_404(user_id)
    user.status = 'blacklisted'
    db.session.commit()
    flash(f'User {user.username} blacklisted successfully!')
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/bookings', methods=['GET'])
@login_required
def admin_manage_bookings():
    if current_user.role != 'admin':
        return 'Unauthorized', 403
    bookings = Booking.query.all()
    return render_template('admin_manage_bookings.html', bookings=bookings)

@app.route('/staff/dashboard')
@login_required
def staff_dashboard():
    if current_user.role != 'staff':
        return 'Unauthorized', 403
    assigned_treks = Trek.query.filter_by(assigned_staff_id=current_user.id).all()
    return render_template('staff_dashboard.html', assigned_treks=assigned_treks)

@app.route('/staff/treks/<int:trek_id>/update', methods=['POST'])
@login_required
def staff_update_trek(trek_id):
    if current_user.role != 'staff':
        return 'Unauthorized', 403
    trek = Trek.query.get_or_404(trek_id)
    if trek.assigned_staff_id != current_user.id:
        return 'Unauthorized', 403
        
    trek.available_slots = int(request.form.get('available_slots'))
    trek.status = request.form.get('status')
    db.session.commit()
    flash('Trek updated successfully!')
    return redirect(url_for('staff_dashboard'))

@app.route('/staff/treks/<int:trek_id>/participants', methods=['GET'])
@login_required
def staff_view_participants(trek_id):
    if current_user.role != 'staff':
        return 'Unauthorized', 403
    trek = Trek.query.get_or_404(trek_id)
    if trek.assigned_staff_id != current_user.id:
        return 'Unauthorized', 403
    bookings = Booking.query.filter_by(trek_id=trek.id).all()
    return render_template('staff_participants.html', trek=trek, bookings=bookings)

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.role != 'trekker':
        return 'Unauthorized', 403
    
    difficulty = request.args.get('difficulty')
    location = request.args.get('location')
    
    query = Trek.query.filter_by(status='Open')
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if location:
        query = query.filter(Trek.location.ilike(f'%{location}%'))
        
    available_treks = query.all()
    my_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_date.desc()).all()
    
    return render_template('user_dashboard.html', available_treks=available_treks, my_bookings=my_bookings)

@app.route('/user/treks/<int:trek_id>/book', methods=['POST'])
@login_required
def user_book_trek(trek_id):
    if current_user.role != 'trekker':
        return 'Unauthorized', 403
        
    trek = Trek.query.get_or_404(trek_id)
    
    existing_booking = Booking.query.filter_by(user_id=current_user.id, trek_id=trek.id).first()
    if existing_booking:
        flash('You have already booked this trek.', 'warning')
        return redirect(url_for('user_dashboard'))
        
    if trek.status != 'Open':
        flash('This trek is not open for booking.', 'danger')
        return redirect(url_for('user_dashboard'))
        
    if trek.available_slots <= 0:
        flash('No slots available for this trek.', 'danger')
        return redirect(url_for('user_dashboard'))
        
    new_booking = Booking(user_id=current_user.id, trek_id=trek.id, status='Booked')
    trek.available_slots -= 1
    db.session.add(new_booking)
    db.session.commit()
    
    flash('Trek booked successfully!', 'success')
    return redirect(url_for('user_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
