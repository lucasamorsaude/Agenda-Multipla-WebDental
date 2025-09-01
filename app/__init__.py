# app/__init__.py

import os
from flask import Flask
from dotenv import load_dotenv
from flask_login import LoginManager
import firebase_admin
from firebase_admin import credentials, firestore

# --- INICIALIZAÇÃO DO FIREBASE ---
cred_path = os.path.join(os.path.dirname(__file__), '..', 'chave_firebase.json') # <-- Verifique se o nome do seu arquivo é esse
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

# Pega uma instância do cliente do Firestore para ser usada em todo o app
db = firestore.client()

# --- INICIALIZAÇÃO DO FLASK-LOGIN ---
login = LoginManager()

def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

    login.init_app(app)

    from . import routes, api, cache, auth, user
    
    # 2. Registra todos os blueprints na aplicação
    app.register_blueprint(routes.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(cache.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(user.bp) 



    login.login_view = 'auth.login'
    login.login_message = "Por favor, faça login para acessar esta página."
    login.login_message_category = "info"

    return app

from app.models import User

@login.user_loader
def load_user(user_id):
    """Função que o Flask-Login usa para carregar um usuário a cada requisição."""
    return User.get(user_id)