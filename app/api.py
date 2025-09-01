# app/api.py

import os
from flask import Blueprint, jsonify, request
from . import services

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/appointment_details/<appointment_id>')
def appointment_details(appointment_id):
    selected_date = request.args.get('date')
    if not selected_date:
        return jsonify({'error': 'A data é necessária.'}), 400

    try:
        # A nova lógica busca todos os dados do dia e depois filtra
        full_day_data = services.get_webdental_data(
            username=os.getenv("USUARIO_ODONTO"),
            password=os.getenv("SENHA_ODONTO"),
            target_unit_name='AmorSaúde São João del Rei', # Pode ser pego da sessão no futuro
            selected_date_str=selected_date
        )

        all_slots = [
            slot for prof_agenda in full_day_data['data']['agendas_completas'].values()
            for slot in prof_agenda['horarios']
        ]
        
        appointment = next((appt for appt in all_slots if appt.get('chave') == appointment_id), None)
        
        if appointment:
            # Agora chamamos a API de detalhes completos aqui
            with services.requests.Session() as s:
                services._login_and_get_units(s, os.getenv("USUARIO_ODONTO"), os.getenv("SENHA_ODONTO"), 'AmorSaúde São João del Rei')
                
                full_details = services.fetch_full_appointment_details(
                    session=s,
                    appointment_id=appointment_id,
                    patient_id=appointment.get('cd_paciente'),
                    selected_date=selected_date
                )
                
                # Mescla os dados para garantir que temos tudo
                full_details['original_data'] = appointment
                return jsonify(full_details)
        else:
            return jsonify({'error': 'Agendamento não encontrado para esta data.'}), 404

    except Exception as e:
        print(f"Erro na API de detalhes: {e}")
        return jsonify({'error': 'Ocorreu um erro interno ao buscar os detalhes.'}), 500