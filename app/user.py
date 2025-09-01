# app/user.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app.models import User
from app import db, services, os

bp = Blueprint('user', __name__, url_prefix='/user')

@bp.route('/panel')
@login_required
def user_panel():
    # Busca a lista de todas as unidades PRIMEIRO, para podermos usar para tradução
    available_units = {}
    try:
        available_units = services.get_all_available_units(
            os.getenv("USUARIO_ODONTO"),
            os.getenv("SENHA_ODONTO")
        )
    except Exception as e:
        flash(f"Não foi possível carregar a lista de unidades da API: {e}", "warning")

    # Busca todos os usuários do Firestore
    users_ref = db.collection('users').stream()
    users_list = []
    for user in users_ref:
        user_data = user.to_dict()
        # Adiciona o nome do usuário (que é o ID do documento) ao dicionário
        user_data['username'] = user.id 
        users_list.append(user_data)
    
    # --- LÓGICA NOVA PARA PROCESSAR AS UNIDADES ---
    # Para cada usuário, vamos traduzir a string de IDs em uma string de Nomes
    for user_data in users_list:
        allowed_ids_str = user_data.get('allowed_units', '')
        if not allowed_ids_str:
            user_data['unidades_texto'] = "Todas"
        else:
            allowed_ids = {uid.strip() for uid in allowed_ids_str.split(',') if uid.strip()}
            # Pega o nome de cada ID permitido, se ele existir na lista de unidades disponíveis
            unit_names = [available_units.get(uid, "ID Inválido") for uid in allowed_ids]
            user_data['unidades_texto'] = ", ".join(sorted(unit_names))

    return render_template('users.html', users=users_list, available_units=available_units)

@bp.route('/add', methods=['POST'])
@login_required
def add_user():
    # Lógica para adicionar um novo usuário
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')
    # Pega a lista de IDs de unidades selecionadas no formulário
    unidades = request.form.getlist('unidades')
    
    user_ref = db.collection('users').document(username)
    if user_ref.get().exists:
        flash(f"O usuário '{username}' já existe.", 'danger')
        return redirect(url_for('user.user_panel'))

    new_user = User(username=username, role=role)
    new_user.set_password(password)
    new_user.allowed_units_str = ",".join(unidades) # Converte a lista em string

    user_ref.set(new_user.to_dict())
    flash(f"Usuário '{username}' adicionado com sucesso!", 'success')
    return redirect(url_for('user.user_panel'))

@bp.route('/change_password/<username>', methods=['POST'])
@login_required
def change_password(username):
    # Lógica para alterar a senha
    user_to_edit = User.get(username)
    if user_to_edit:
        new_password = request.form.get('password')
        user_to_edit.set_password(new_password)
        db.collection('users').document(username).update({'password_hash': user_to_edit.password_hash})
        flash(f"Senha do usuário '{username}' alterada com sucesso.", 'success')
    else:
        flash("Usuário não encontrado.", 'danger')
    return redirect(url_for('user.user_panel'))

@bp.route('/delete/<username>', methods=['POST'])
@login_required
def delete_user(username):
    # Lógica para deletar um usuário
    if username == current_user.id:
        flash("Você não pode deletar a si mesmo.", 'danger')
        return redirect(url_for('user.user_panel'))
    
    db.collection('users').document(username).delete()
    flash(f"Usuário '{username}' deletado com sucesso.", 'success')
    return redirect(url_for('user.user_panel'))