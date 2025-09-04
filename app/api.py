# app/api.py

import os
from flask import Blueprint, jsonify, request, session
from flask_login import login_user, logout_user, current_user, login_required
from . import services

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/appointment_details/<appointment_id>')
def appointment_details(appointment_id):
    selected_date = request.args.get('date')
    patient_id = request.args.get('patientId')

    if not all([selected_date, patient_id, appointment_id]):
        return jsonify({'error': 'Dados insuficientes para a busca.'}), 400

    try:
        # --- MUDANÇA AQUI: Usa a nova função de busca "ao vivo" ---
        live_data = services.get_webdental_data_live(
            username=os.getenv("USUARIO_ODONTO"),
            password=os.getenv("SENHA_ODONTO"),
            target_unit_name=session.get('target_unit_name'),
            selected_date_str=selected_date
        )

        all_slots = [
            slot for prof_agenda in live_data['agendas_completas'].values()
            for slot in prof_agenda['horarios']
        ]
        
        
        appointment = next((appt for appt in all_slots if appt.get('chave') == appointment_id), None)
        
        if appointment:
            # O resto da lógica para buscar detalhes completos continua a mesma
            with services.requests.Session() as s:
                services._login_and_get_units(s, os.getenv("USUARIO_ODONTO"), os.getenv("SENHA_ODONTO"), session.get('target_unit_name'))
                
                full_details = services.fetch_full_appointment_details(
                    session=s,
                    appointment_id=appointment_id,
                    patient_id=appointment.get('cd_paciente'),
                    selected_date=selected_date
                )
                
                full_details['original_data'] = appointment
                return jsonify(full_details)
        else:
            # Se mesmo na busca ao vivo não achou, o agendamento realmente não existe.
            return jsonify({'error': 'Agendamento não encontrado para esta data (mesmo em busca ao vivo).'}), 404

    except Exception as e:
        print(f"Erro na API de detalhes: {e}")
        return jsonify({'error': 'Ocorreu um erro interno ao buscar os detalhes.'}), 500
    

@bp.route('/my_units')
@login_required
def my_units_api():
    """Retorna a lista de unidades permitidas para o usuário logado."""
    # Para o superadmin, session['unidades'] terá todas as unidades
    if 'unidades' in session:
        # Formata os dados no formato que o JavaScript espera: [{'id': ..., 'name': ...}]
        units_list = [{'id': uid, 'name': name} for uid, name in session['unidades'].items()]
        return jsonify(units_list)
    return jsonify([])