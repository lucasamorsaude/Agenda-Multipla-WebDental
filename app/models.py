# app/models.py
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db # db agora é nosso cliente do Firestore

class User(UserMixin):
    def __init__(self, username, password_hash=None, allowed_units_str=None, role='user'): 
        self.id = username # No Firestore, usaremos o username como ID do documento
        self.password_hash = password_hash
        self.allowed_units_str = allowed_units_str
        self.role = role # Adiciona role

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get(user_id):
        doc = db.collection('users').document(user_id).get()
        if not doc.exists:
            return None
        
        user_data = doc.to_dict()
        return User(
            username=user_id,
            password_hash=user_data.get('password_hash'),
            allowed_units_str=user_data.get('allowed_units'),
            role=user_data.get('role', 'user') # Adiciona role
        )

    def to_dict(self):
        return {
            'password_hash': self.password_hash,
            'allowed_units': self.allowed_units_str,
            'role': self.role # Adiciona role
        }