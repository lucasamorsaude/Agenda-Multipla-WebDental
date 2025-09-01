# create_user.py
from app import create_app, db # db agora é nosso cliente do Firestore
from app.models import User

# Cria uma instância da aplicação para ter o contexto
app = create_app()

with app.app_context():
    print("Criando/Atualizando usuário admin...")
    
    username = 'admin'
    user_ref = db.collection('users').document(username)
    
    # Cria um novo usuário
    u = User(username=username, role='superadmin') # Define a permissão aqui
    u.set_password('1234') # Defina sua senha
    u.allowed_units_str = "" # Acesso a todas as unidades
    
    # Salva ou atualiza o usuário no Firestore
    user_ref.set(u.to_dict())
    print(f"Usuário '{username}' salvo com a permissão '{u.role}'!")