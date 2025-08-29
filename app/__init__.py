import os
from flask import Flask
from dotenv import load_dotenv

def create_app():
    # Carrega as variáveis do arquivo .env
    load_dotenv()
    
    # Cria a instância principal do site
    app = Flask(__name__)
    
    # Configura uma chave de segurança para as 'sessões' do navegador
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

    from . import routes
    app.register_blueprint(routes.bp)

    from . import api
    app.register_blueprint(api.bp)

    from . import cache
    app.register_blueprint(cache.bp)

    return app