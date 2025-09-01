# app/auth.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User
from datetime import datetime
import os
from . import services # Precisamos dos serviços para buscar as unidades

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.select_unit'))
    
    if request.method == 'POST':
        # Etapa 1: Pega os dados do formulário
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Etapa 2: Busca o usuário no banco de dados (Firestore)
        user = User.get(username)
        
        # Etapa 3: Verificação de segurança CRÍTICA
        # Se o usuário não existe OU a senha está errada...
        if user is None or not user.check_password(password):
            flash('Usuário ou senha inválidos', 'danger')
            return redirect(url_for('auth.login')) # ...PARA TUDO e volta pro login.
        
        # Etapa 4: Se passou na verificação, loga o usuário na sessão do Flask
        login_user(user, remember=True)
        
        # Etapa 5: Busca as unidades permitidas e redireciona para a tela de seleção
        try:
            all_units = services.get_all_available_units(os.getenv("USUARIO_ODONTO"), os.getenv("SENHA_ODONTO"))
            allowed_ids_str = user.allowed_units_str or ""
            allowed_ids = {uid.strip() for uid in allowed_ids_str.split(',') if uid.strip()}
            
            if allowed_ids:
                permitted_units = {uid: name for uid, name in all_units.items() if uid in allowed_ids}
            else:
                permitted_units = all_units

            session['unidades'] = permitted_units
            session['username'] = user.id
            session['role'] = user.role # Salva a permissão do usuário na sessão

            return redirect(url_for('auth.select_unit'))

        except Exception as e:
            # Se o login estiver certo mas a API da WebDental falhar, desloga o usuário e mostra um erro.
            logout_user()
            flash(f"Login bem-sucedido, mas erro ao buscar unidades da API: {e}", 'danger')
            return redirect(url_for('auth.login'))
            
    return render_template('login.html')

@bp.route('/logout')
def logout():
    logout_user()
    #session.clear()
    flash('Você saiu com sucesso.', 'success')
    return redirect(url_for('auth.login'))

@bp.route('/select_unit')
@login_required
def select_unit():
    """Mostra a tela de seleção de unidade."""
    if not session.get('unidades'):
        # Se por algum motivo as unidades não estiverem na sessão, força o relogin
        return redirect(url_for('auth.login'))
    return render_template('select_unit.html')

@bp.route('/set_unit/<unit_id>')
@login_required
def set_unit(unit_id):
    """Define a unidade escolhida e redireciona para o dashboard."""
    if 'unidades' in session and unit_id in session['unidades']:
        session['selected_unit_id'] = unit_id
        session['target_unit_name'] = session['unidades'][unit_id]
        # Redireciona para o dashboard já com a data de hoje para carregar a agenda
        return redirect(url_for('main.index', selected_date=datetime.now().strftime('%Y-%m-%d')))
    
    flash('Unidade inválida ou não permitida.', 'danger')
    return redirect(url_for('auth.select_unit'))