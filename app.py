#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

db = SQLAlchemy(app)

# Models
class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    appointments = db.relationship('Appointment', backref='client', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }

class Service(db.Model):
    __tablename__ = 'services'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer, default=60)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    appointments = db.relationship('Appointment', backref='service', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'duration_minutes': self.duration_minutes,
            'price': self.price,
            'created_at': self.created_at.isoformat()
        }

class Appointment(db.Model):
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default='scheduled')  # scheduled, completed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'client_id': self.client_id,
            'client_name': self.client.name,
            'service_id': self.service_id,
            'service_name': self.service.name,
            'scheduled_at': self.scheduled_at.isoformat(),
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }

# Routes
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()}), 200

# Clients API
@app.route('/api/clients', methods=['GET', 'POST'])
def clients_handler():
    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        clients = Client.query.paginate(page=page, per_page=per_page)
        return jsonify({
            'data': [client.to_dict() for client in clients.items],
            'total': clients.total,
            'pages': clients.pages,
            'current_page': page
        }), 200
    
    elif request.method == 'POST':
        data = request.get_json()
        
        if not data or not data.get('name') or not data.get('phone'):
            return jsonify({'error': 'Не указаны обязательные поля'}), 400
        
        existing = Client.query.filter_by(phone=data['phone']).first()
        if existing:
            return jsonify({'error': 'Клиент с этим номером телефона уже существует'}), 409
        
        client = Client(
            name=data['name'],
            phone=data['phone'],
            email=data.get('email')
        )
        db.session.add(client)
        db.session.commit()
        
        return jsonify(client.to_dict()), 201

@app.route('/api/clients/<int:client_id>', methods=['GET', 'PUT', 'DELETE'])
def client_detail(client_id):
    client = Client.query.get_or_404(client_id)
    
    if request.method == 'GET':
        return jsonify(client.to_dict()), 200
    
    elif request.method == 'PUT':
        data = request.get_json()
        client.name = data.get('name', client.name)
        client.email = data.get('email', client.email)
        db.session.commit()
        return jsonify(client.to_dict()), 200
    
    elif request.method == 'DELETE':
        db.session.delete(client)
        db.session.commit()
        return '', 204

# Services API
@app.route('/api/services', methods=['GET', 'POST'])
def services_handler():
    if request.method == 'GET':
        services = Service.query.all()
        return jsonify([service.to_dict() for service in services]), 200
    
    elif request.method == 'POST':
        data = request.get_json()
        
        if not data or not data.get('name') or not data.get('price'):
            return jsonify({'error': 'Не указаны обязательные поля'}), 400
        
        service = Service(
            name=data['name'],
            description=data.get('description'),
            duration_minutes=data.get('duration_minutes', 60),
            price=data['price']
        )
        db.session.add(service)
        db.session.commit()
        
        return jsonify(service.to_dict()), 201

@app.route('/api/services/<int:service_id>', methods=['GET', 'PUT', 'DELETE'])
def service_detail(service_id):
    service = Service.query.get_or_404(service_id)
    
    if request.method == 'GET':
        return jsonify(service.to_dict()), 200
    
    elif request.method == 'PUT':
        data = request.get_json()
        service.name = data.get('name', service.name)
        service.description = data.get('description', service.description)
        service.duration_minutes = data.get('duration_minutes', service.duration_minutes)
        service.price = data.get('price', service.price)
        db.session.commit()
        return jsonify(service.to_dict()), 200
    
    elif request.method == 'DELETE':
        db.session.delete(service)
        db.session.commit()
        return '', 204

# Appointments API
@app.route('/api/appointments', methods=['GET', 'POST'])
def appointments_handler():
    if request.method == 'GET':
        client_id = request.args.get('client_id', type=int)
        status = request.args.get('status')
        
        query = Appointment.query
        if client_id:
            query = query.filter_by(client_id=client_id)
        if status:
            query = query.filter_by(status=status)
        
        appointments = query.order_by(Appointment.scheduled_at).all()
        return jsonify([appointment.to_dict() for appointment in appointments]), 200
    
    elif request.method == 'POST':
        data = request.get_json()
        
        required_fields = ['client_id', 'service_id', 'scheduled_at']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'Не указаны обязательные поля'}), 400
        
        client = Client.query.get(data['client_id'])
        service = Service.query.get(data['service_id'])
        
        if not client or not service:
            return jsonify({'error': 'Клиент или сервис не найдены'}), 404
        
        appointment = Appointment(
            client_id=data['client_id'],
            service_id=data['service_id'],
            scheduled_at=datetime.fromisoformat(data['scheduled_at']),
            notes=data.get('notes')
        )
        db.session.add(appointment)
        db.session.commit()
        
        return jsonify(appointment.to_dict()), 201

@app.route('/api/appointments/<int:appointment_id>', methods=['GET', 'PUT', 'DELETE'])
def appointment_detail(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if request.method == 'GET':
        return jsonify(appointment.to_dict()), 200
    
    elif request.method == 'PUT':
        data = request.get_json()
        if 'status' in data:
            appointment.status = data['status']
        if 'notes' in data:
            appointment.notes = data['notes']
        if 'scheduled_at' in data:
            appointment.scheduled_at = datetime.fromisoformat(data['scheduled_at'])
        db.session.commit()
        return jsonify(appointment.to_dict()), 200
    
    elif request.method == 'DELETE':
        db.session.delete(appointment)
        db.session.commit()
        return '', 204

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Не найдено'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
