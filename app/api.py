# app/api.py

import os
from flask import Blueprint, jsonify, request
from . import services

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/appointment_details/<appointment_id>')
def appointment_details(appointment_id):
    """
    API que busca "ao vivo" os detalhes completos de um agendamento.
    """
    selected_date = request.args.get('date')
    patient_id = request.args.get('patientId')

    if not all([selected_date, patient_id, appointment_id]):
        return jsonify({'error': 'Dados insuficientes para a busca.'}), 400

    try:
        # Reutiliza o login e a sessão do services.py para fazer a nova chamada
        with services.requests.Session() as s:
            s.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'X-Requested-With': 'XMLHttpRequest'
            })
            
            # Faz o login para obter uma sessão válida
            services._login_and_get_units(
                s,
                username=os.getenv("USUARIO_ODONTO"),
                password=os.getenv("SENHA_ODONTO"),
                target_unit_name='AmorSaúde São João del Rei' # Pode ser pego da sessão no futuro
            )
            
            # Chama a nova função para buscar os detalhes completos
            full_details = services.fetch_full_appointment_details(
                session=s,
                appointment_id=appointment_id,
                patient_id=patient_id,
                selected_date=selected_date
            )
        
        if full_details and not full_details.get('error'):
            # Mescla os dados do agendamento original (que tem o nome do paciente) com os detalhes
            original_appointment = services.fetch_single_appointment_details(
                username=os.getenv("USUARIO_ODONTO"),
                password=os.getenv("SENHA_ODONTO"),
                target_unit_name='AmorSaúde São João del Rei',
                selected_date_str=selected_date,
                appointment_id_to_find=appointment_id
            )
            if original_appointment:
                full_details['original_data'] = original_appointment

            return jsonify(full_details)
        else:
            return jsonify({'error': 'Detalhes do agendamento não encontrados.'}), 404

    except Exception as e:
        print(f"Erro na API de detalhes: {e}")
        return jsonify({'error': 'Ocorreu um erro interno ao buscar os detalhes.'}), 500