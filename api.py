from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, Trek, User, Booking

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Helper to check auth for APIs (or we can just use @login_required)
# For a full REST API, token auth is better, but since this is integrated with Flask-Login,
# we'll use @login_required which relies on session cookies.

# 1. Treks API
@api_bp.route('/treks', methods=['GET'])
def get_treks():
    difficulty = request.args.get('difficulty')
    status = request.args.get('status')
    
    query = Trek.query
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if status:
        query = query.filter_by(status=status)
        
    treks = query.all()
    result = [{
        'id': t.id, 'name': t.name, 'location': t.location, 
        'difficulty': t.difficulty, 'duration': t.duration,
        'available_slots': t.available_slots, 'total_slots': t.total_slots,
        'status': t.status, 'assigned_staff_id': t.assigned_staff_id
    } for t in treks]
    
    return jsonify(result), 200

@api_bp.route('/treks/<int:trek_id>', methods=['GET'])
def get_trek(trek_id):
    trek = Trek.query.get(trek_id)
    if not trek:
        return jsonify({'error': 'Trek not found'}), 404
        
    return jsonify({
        'id': trek.id, 'name': trek.name, 'location': trek.location, 
        'difficulty': trek.difficulty, 'duration': trek.duration,
        'available_slots': trek.available_slots, 'total_slots': trek.total_slots,
        'status': trek.status, 'assigned_staff_id': trek.assigned_staff_id
    }), 200

@api_bp.route('/treks', methods=['POST'])
@login_required
def create_trek():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON payload provided'}), 400
        
    new_trek = Trek(
        name=data.get('name'),
        location=data.get('location'),
        difficulty=data.get('difficulty'),
        duration=data.get('duration'),
        total_slots=data.get('total_slots'),
        available_slots=data.get('total_slots'),
        status=data.get('status', 'Pending')
    )
    db.session.add(new_trek)
    db.session.commit()
    return jsonify({'message': 'Trek created', 'id': new_trek.id}), 201

@api_bp.route('/treks/<int:trek_id>', methods=['PUT'])
@login_required
def update_trek(trek_id):
    trek = Trek.query.get(trek_id)
    if not trek:
        return jsonify({'error': 'Trek not found'}), 404
        
    if current_user.role not in ['admin', 'staff']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    if current_user.role == 'staff' and trek.assigned_staff_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    
    if current_user.role == 'admin':
        if 'name' in data: trek.name = data['name']
        if 'location' in data: trek.location = data['location']
        if 'difficulty' in data: trek.difficulty = data['difficulty']
        if 'duration' in data: trek.duration = data['duration']
        if 'total_slots' in data: 
            diff = data['total_slots'] - trek.total_slots
            trek.total_slots = data['total_slots']
            trek.available_slots += diff
            
    if 'available_slots' in data: trek.available_slots = data['available_slots']
    if 'status' in data: trek.status = data['status']
    
    db.session.commit()
    return jsonify({'message': 'Trek updated successfully'}), 200

@api_bp.route('/treks/<int:trek_id>', methods=['DELETE'])
@login_required
def delete_trek(trek_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    trek = Trek.query.get(trek_id)
    if not trek:
        return jsonify({'error': 'Trek not found'}), 404
        
    db.session.delete(trek)
    db.session.commit()
    return '', 204

# 2. Users API
@api_bp.route('/users', methods=['GET'])
@login_required
def get_users():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    users = User.query.all()
    result = [{
        'id': u.id, 'username': u.username, 'email': u.email,
        'role': u.role, 'status': u.status
    } for u in users]
    
    return jsonify(result), 200

@api_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    if current_user.role != 'admin' and current_user.id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    return jsonify({
        'id': user.id, 'username': user.username, 'email': user.email,
        'role': user.role, 'status': user.status
    }), 200

# 3. Bookings API
@api_bp.route('/bookings', methods=['GET'])
@login_required
def get_bookings():
    if current_user.role == 'trekker':
        bookings = Booking.query.filter_by(user_id=current_user.id).all()
    elif current_user.role == 'staff':
        trek_id = request.args.get('trek_id')
        if trek_id:
            bookings = Booking.query.join(Trek).filter(Trek.id==trek_id, Trek.assigned_staff_id==current_user.id).all()
        else:
            bookings = Booking.query.join(Trek).filter(Trek.assigned_staff_id==current_user.id).all()
    else: # admin
        bookings = Booking.query.all()
        
    result = [{
        'id': b.id, 'user_id': b.user_id, 'trek_id': b.trek_id,
        'booking_date': b.booking_date.isoformat(), 'status': b.status
    } for b in bookings]
    
    return jsonify(result), 200

@api_bp.route('/bookings', methods=['POST'])
@login_required
def create_booking():
    if current_user.role != 'trekker':
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    trek_id = data.get('trek_id')
    if not trek_id:
        return jsonify({'error': 'trek_id required'}), 400
        
    trek = Trek.query.get(trek_id)
    if not trek or trek.status != 'Open' or trek.available_slots <= 0:
        return jsonify({'error': 'Trek unavailable'}), 400
        
    if Booking.query.filter_by(user_id=current_user.id, trek_id=trek.id).first():
        return jsonify({'error': 'Already booked'}), 400
        
    booking = Booking(user_id=current_user.id, trek_id=trek.id)
    trek.available_slots -= 1
    db.session.add(booking)
    db.session.commit()
    
    return jsonify({'message': 'Booking successful', 'id': booking.id}), 201

@api_bp.route('/bookings/<int:booking_id>', methods=['PUT'])
@login_required
def update_booking(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404
        
    data = request.get_json()
    status = data.get('status')
    if not status:
        return jsonify({'error': 'status required'}), 400
        
    if current_user.role == 'trekker' and booking.user_id == current_user.id:
        if status == 'Cancelled':
            booking.status = 'Cancelled'
            # return slot
            booking.trek.available_slots += 1
            db.session.commit()
            return jsonify({'message': 'Booking cancelled'}), 200
        return jsonify({'error': 'Unauthorized status update'}), 403
        
    if current_user.role == 'admin' or (current_user.role == 'staff' and booking.trek.assigned_staff_id == current_user.id):
        booking.status = status
        db.session.commit()
        return jsonify({'message': 'Booking updated'}), 200
        
    return jsonify({'error': 'Unauthorized'}), 403
