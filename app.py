import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Trek, Booking, StaffProfile, init_admin
from werkzeug.security import generate_password_hash
from api import api_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-tma-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tma.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
app.register_blueprint(api_bp)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    init_admin()

# ─────────────────────────── PUBLIC ROUTES ────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'staff':
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    # Public landing page: show a sample of open treks
    featured_treks = Trek.query.filter_by(status='Open').limit(6).all()
    return render_template('index.html', featured_treks=featured_treks)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if user.status == 'blacklisted':
                flash('Your account has been blacklisted. Contact admin.', 'danger')
                return redirect(url_for('login'))
            if user.status == 'pending':
                flash('Your account is pending admin approval.', 'warning')
                return redirect(url_for('login'))

            login_user(user)
            return redirect(url_for('index'))

        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')  # 'trekker' or 'staff'

        if User.query.filter_by(username=username).first():
            flash('Username already taken. Try a different one.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))

        if role not in ['trekker', 'staff']:
            role = 'trekker'

        status = 'pending' if role == 'staff' else 'approved'
        new_user = User(username=username, email=email, role=role, status=status)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        if role == 'staff':
            flash('Registration successful! Please wait for admin approval before logging in.', 'info')
        else:
            flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ─────────────────────────── HELPERS ─────────────────────────────────────────

def complete_trek_bookings(trek):
    """When a trek is marked Completed, flip its active bookings to Completed
    so they show up as finished trips in each user's history."""
    for booking in trek.bookings:
        if booking.status == 'Booked':
            booking.status = 'Completed'

# ─────────────────────────── ADMIN ROUTES ────────────────────────────────────

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    total_treks = Trek.query.count()
    total_users = User.query.filter_by(role='trekker').count()
    total_staff = User.query.filter_by(role='staff').count()
    total_bookings = Booking.query.count()
    pending_staff = User.query.filter_by(role='staff', status='pending').count()
    open_treks = Trek.query.filter_by(status='Open').count()

    # ---- Chart data (rendered as pure CSS/Bootstrap bars, no JS) ----
    # Popular treks: top 5 by active (Booked) booking count
    all_treks = Trek.query.all()
    trek_booking_counts = [
        (t.name, Booking.query.filter_by(trek_id=t.id, status='Booked').count())
        for t in all_treks
    ]
    popular_treks = sorted(trek_booking_counts, key=lambda x: x[1], reverse=True)[:5]
    popular_max = max([c for _, c in popular_treks], default=0) or 1

    # Bookings grouped by status
    booking_status_counts = {
        s: Booking.query.filter_by(status=s).count()
        for s in ['Booked', 'Completed', 'Cancelled']
    }
    booking_status_max = max(booking_status_counts.values(), default=0) or 1

    # Treks grouped by status
    trek_status_counts = {
        s: Trek.query.filter_by(status=s).count()
        for s in ['Pending', 'Approved', 'Open', 'Closed', 'Started', 'Completed']
    }
    trek_status_max = max(trek_status_counts.values(), default=0) or 1

    return render_template('admin_dashboard.html',
                           total_treks=total_treks, total_users=total_users,
                           total_staff=total_staff, total_bookings=total_bookings,
                           pending_staff=pending_staff, open_treks=open_treks,
                           popular_treks=popular_treks, popular_max=popular_max,
                           booking_status_counts=booking_status_counts,
                           booking_status_max=booking_status_max,
                           trek_status_counts=trek_status_counts,
                           trek_status_max=trek_status_max)

@app.route('/admin/search')
@login_required
def admin_search():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    query = request.args.get('q', '').strip()
    trek_results = []
    user_results = []
    staff_results = []
    if query:
        trek_results = Trek.query.filter(
            Trek.name.ilike(f'%{query}%') | Trek.location.ilike(f'%{query}%')
        ).all()
        user_results = User.query.filter(
            (User.role == 'trekker') &
            (User.username.ilike(f'%{query}%') | User.email.ilike(f'%{query}%'))
        ).all()
        staff_results = User.query.filter(
            (User.role == 'staff') &
            (User.username.ilike(f'%{query}%') | User.email.ilike(f'%{query}%'))
        ).all()
        # Also search by numeric ID if query is a number
        if query.isdigit():
            qid = int(query)
            id_trek = Trek.query.get(qid)
            if id_trek and id_trek not in trek_results:
                trek_results.append(id_trek)
            id_user = User.query.get(qid)
            if id_user and id_user.role == 'trekker' and id_user not in user_results:
                user_results.append(id_user)
            if id_user and id_user.role == 'staff' and id_user not in staff_results:
                staff_results.append(id_user)
    return render_template('admin_search.html', query=query,
                           trek_results=trek_results,
                           user_results=user_results,
                           staff_results=staff_results)

@app.route('/admin/treks', methods=['GET'])
@login_required
def admin_manage_treks():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    search = request.args.get('search', '').strip()
    query = Trek.query
    if search:
        query = query.filter(Trek.name.ilike(f'%{search}%') | Trek.location.ilike(f'%{search}%'))
    treks = query.all()
    assigned_staff_ids = [t.assigned_staff_id for t in Trek.query.filter(Trek.assigned_staff_id.isnot(None)).all()]
    staff_query = User.query.filter_by(role='staff', status='approved')
    if assigned_staff_ids:
        staff_query = staff_query.filter(User.id.notin_(assigned_staff_ids))
    staff_members = staff_query.all()
    return render_template('admin_manage_treks.html', treks=treks,
                           staff_members=staff_members, search=search)

@app.route('/admin/treks/create', methods=['POST'])
@login_required
def admin_create_trek():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    name = request.form.get('name')
    location = request.form.get('location')
    difficulty = request.form.get('difficulty')
    duration = request.form.get('duration')
    total_slots = request.form.get('total_slots')
    description = request.form.get('description', '')
    assigned_staff_id = request.form.get('assigned_staff_id') or None
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

    new_trek = Trek(
        name=name, location=location, difficulty=difficulty,
        duration=int(duration), total_slots=int(total_slots),
        available_slots=int(total_slots), description=description,
        assigned_staff_id=assigned_staff_id,
        start_date=start_date, end_date=end_date
    )
    db.session.add(new_trek)
    db.session.commit()
    flash('Trek created successfully!', 'success')
    return redirect(url_for('admin_manage_treks'))

@app.route('/admin/treks/<int:trek_id>/edit', methods=['POST'])
@login_required
def admin_edit_trek(trek_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    trek = Trek.query.get_or_404(trek_id)
    trek.name = request.form.get('name')
    trek.location = request.form.get('location')
    trek.difficulty = request.form.get('difficulty')
    trek.duration = int(request.form.get('duration'))
    trek.description = request.form.get('description', '')
    new_total_slots = int(request.form.get('total_slots'))
    diff = new_total_slots - trek.total_slots
    trek.total_slots = new_total_slots
    trek.available_slots = max(0, trek.available_slots + diff)
    assigned_staff_id = request.form.get('assigned_staff_id')
    trek.assigned_staff_id = assigned_staff_id if assigned_staff_id else None
    new_status = request.form.get('status')
    if new_status:
        trek.status = new_status
        if new_status == 'Completed':
            complete_trek_bookings(trek)
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    trek.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else trek.start_date
    trek.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else trek.end_date

    db.session.commit()
    flash('Trek updated successfully!', 'success')
    return redirect(url_for('admin_manage_treks'))

@app.route('/admin/treks/<int:trek_id>/set-status', methods=['POST'])
@login_required
def admin_set_trek_status(trek_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    trek = Trek.query.get_or_404(trek_id)
    new_status = request.form.get('status')
    if new_status in ['Pending', 'Approved', 'Open', 'Closed', 'Started', 'Completed']:
        trek.status = new_status
        if new_status == 'Completed':
            complete_trek_bookings(trek)
        db.session.commit()
        flash(f'Trek status changed to {new_status}.', 'success')
    else:
        flash('Invalid status.', 'danger')
    return redirect(url_for('admin_manage_treks'))

@app.route('/admin/treks/<int:trek_id>/delete', methods=['POST'])
@login_required
def admin_delete_trek(trek_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    trek = Trek.query.get_or_404(trek_id)
    # Delete associated bookings first
    Booking.query.filter_by(trek_id=trek_id).delete()
    db.session.delete(trek)
    db.session.commit()
    flash('Trek deleted successfully!', 'success')
    return redirect(url_for('admin_manage_treks'))

@app.route('/admin/users', methods=['GET'])
@login_required
def admin_manage_users():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '')
    query = User.query.filter(User.role != 'admin')
    if search:
        query = query.filter(
            User.username.ilike(f'%{search}%') | User.email.ilike(f'%{search}%')
        )
        if search.isdigit():
            uid = int(search)
            by_id = User.query.get(uid)
            if by_id and by_id.role != 'admin':
                query = User.query.filter(User.id == uid)
    if role_filter in ['trekker', 'staff']:
        query = query.filter(User.role == role_filter)
    users = query.all()
    return render_template('admin_manage_users.html', users=users,
                           search=search, role_filter=role_filter)

@app.route('/admin/users/<int:user_id>/approve', methods=['POST'])
@login_required
def admin_approve_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    user.status = 'approved'
    db.session.commit()
    flash(f'{user.username} approved successfully!', 'success')
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/users/<int:user_id>/blacklist', methods=['POST'])
@login_required
def admin_blacklist_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    user.status = 'blacklisted'
    db.session.commit()
    flash(f'{user.username} has been blacklisted.', 'warning')
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/users/<int:user_id>/unblacklist', methods=['POST'])
@login_required
def admin_unblacklist_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    user.status = 'approved'
    db.session.commit()
    flash(f'{user.username} has been reinstated.', 'success')
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/bookings', methods=['GET'])
@login_required
def admin_manage_bookings():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    trek_filter = request.args.get('trek_id', '')
    query = Booking.query
    if trek_filter and trek_filter.isdigit():
        query = query.filter_by(trek_id=int(trek_filter))
    bookings = query.order_by(Booking.booking_date.desc()).all()
    all_treks = Trek.query.order_by(Trek.name).all()
    return render_template('admin_manage_bookings.html', bookings=bookings,
                           all_treks=all_treks, trek_filter=trek_filter)

# ─────────────────────────── STAFF ROUTES ────────────────────────────────────

@app.route('/staff/dashboard')
@login_required
def staff_dashboard():
    if current_user.role != 'staff':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    assigned_treks = Trek.query.filter_by(assigned_staff_id=current_user.id).all()
    # Count participants per trek
    trek_participant_counts = {
        t.id: Booking.query.filter_by(trek_id=t.id, status='Booked').count()
        for t in assigned_treks
    }
    return render_template('staff_dashboard.html', assigned_treks=assigned_treks,
                           trek_participant_counts=trek_participant_counts)

@app.route('/staff/treks/<int:trek_id>/update', methods=['POST'])
@login_required
def staff_update_trek(trek_id):
    if current_user.role != 'staff':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    trek = Trek.query.get_or_404(trek_id)
    if trek.assigned_staff_id != current_user.id:
        flash('You are not assigned to this trek.', 'danger')
        return redirect(url_for('staff_dashboard'))

    new_slots = request.form.get('available_slots')
    new_status = request.form.get('status')
    if new_slots is not None:
        trek.available_slots = int(new_slots)
    if new_status in ['Open', 'Closed', 'Started', 'Completed']:
        trek.status = new_status
        if new_status == 'Completed':
            complete_trek_bookings(trek)
    db.session.commit()
    flash('Trek updated successfully!', 'success')
    return redirect(url_for('staff_dashboard'))

@app.route('/staff/treks/<int:trek_id>/participants', methods=['GET'])
@login_required
def staff_view_participants(trek_id):
    if current_user.role != 'staff':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    trek = Trek.query.get_or_404(trek_id)
    if trek.assigned_staff_id != current_user.id:
        flash('You are not assigned to this trek.', 'danger')
        return redirect(url_for('staff_dashboard'))
    bookings = Booking.query.filter_by(trek_id=trek.id).all()
    return render_template('staff_participants.html', trek=trek, bookings=bookings)

# ─────────────────────────── USER ROUTES ─────────────────────────────────────

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.role != 'trekker':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    difficulty = request.args.get('difficulty', '')
    location = request.args.get('location', '').strip()
    search = request.args.get('search', '').strip()

    query = Trek.query.filter_by(status='Open')
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if location:
        query = query.filter(Trek.location.ilike(f'%{location}%'))
    if search:
        query = query.filter(Trek.name.ilike(f'%{search}%') | Trek.location.ilike(f'%{search}%'))

    available_treks = query.all()

    # Check which treks the user has already booked
    booked_trek_ids = {
        b.trek_id for b in Booking.query.filter_by(user_id=current_user.id).all()
        if b.status == 'Booked'
    }

    my_bookings = Booking.query.filter_by(user_id=current_user.id)\
                               .order_by(Booking.booking_date.desc()).all()

    return render_template('user_dashboard.html',
                           available_treks=available_treks,
                           my_bookings=my_bookings,
                           booked_trek_ids=booked_trek_ids,
                           difficulty=difficulty, location=location, search=search)

@app.route('/user/treks/<int:trek_id>/book', methods=['POST'])
@login_required
def user_book_trek(trek_id):
    if current_user.role != 'trekker':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    trek = Trek.query.get_or_404(trek_id)

    existing_booking = Booking.query.filter_by(
        user_id=current_user.id, trek_id=trek.id).filter(
        Booking.status != 'Cancelled').first()
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

    flash(f'"{trek.name}" booked successfully! Happy trekking!', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
def user_cancel_booking(booking_id):
    if current_user.role != 'trekker':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('user_dashboard'))

    if booking.status != 'Booked':
        flash('This booking cannot be cancelled.', 'warning')
        return redirect(url_for('user_dashboard'))

    booking.status = 'Cancelled'
    # Restore the slot
    booking.trek.available_slots += 1
    db.session.commit()
    flash('Booking cancelled. Slot has been returned.', 'info')
    return redirect(url_for('user_dashboard'))

@app.route('/user/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    if current_user.role != 'trekker':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        new_email = request.form.get('email', '').strip()
        new_password = request.form.get('password', '').strip()

        # Check uniqueness
        if new_username != current_user.username:
            if User.query.filter_by(username=new_username).first():
                flash('Username already taken.', 'danger')
                return redirect(url_for('user_profile'))
            current_user.username = new_username

        if new_email != current_user.email:
            if User.query.filter_by(email=new_email).first():
                flash('Email already in use.', 'danger')
                return redirect(url_for('user_profile'))
            current_user.email = new_email

        if new_password:
            current_user.set_password(new_password)

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user_profile'))

    booking_count = Booking.query.filter_by(user_id=current_user.id).count()
    return render_template('user_profile.html', booking_count=booking_count)

if __name__ == '__main__':
    app.run(debug=True)
