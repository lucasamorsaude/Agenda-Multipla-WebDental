# app/routes.py

import os
from flask import Blueprint, render_template, session, request, redirect, url_for
from datetime import datetime
import pandas as pd
from . import services 

bp = Blueprint('main', __name__)

@bp.route('/', methods=['GET', 'POST'])
def index():
    agendas = None
    summary_metrics = {}
    table_headers, table_index, table_body = [], [], []
    last_updated_formatted = None
    selected_date = request.form.get('selected_date', datetime.now().strftime('%Y-%m-%d'))
    
    if 'target_unit_name' not in session:
        session['target_unit_name'] = 'AmorSaúde São João del Rei'

    status_styles = {
        'Confirmado': 'background-color: #cdf2f7; color: #3a929e; border-left: 5px solid #3a929e;',
        'Agendado':   'background-color: #e7e7e7; color: #696969; border-left: 5px solid #696969;',
        'Faltou':     'background-color: #f8d7da; color: #842029; border-left: 5px solid #dc3545;',
        'Compareceu': 'background-color: #fae896cc; color: #5f4e01cc; border-left: 5px solid #5f4e01cc;',
        'Atendido (Obs)': 'background-color: #a3eba3c2; color: #036e03f1; border-left: 5px solid #036e03f1;',
        'Pagamento Realizado': 'background-color: #ffc58b; color: #a05000; border-left: 5px solid #a05000;',
        'Atendido com procedimento': 'background-color: #ccd8f1; color: #04c; border-left: 5px solid #04c;',
        'Disponível': 'background-color: #f8f9fa; color: #6c757d; border-left: 5px solid #6c757d; border-style: dashed;',
        'Compromisso':'background-color: #c0c0c0; color: #5a5a5a; border-left: 5px solid #5a5a5a;', # NOVA COR
        'default':    'background-color: #e9ecef; border-left: 5px solid #adb5bd;'
    }
    
    # Define a duração padrão de um slot (em minutos)
    default_duration = 15

    try:
        api_data = services.get_webdental_data(
            username=os.getenv("USUARIO_ODONTO"),
            password=os.getenv("SENHA_ODONTO"),
            target_unit_name=session['target_unit_name'],
            selected_date_str=selected_date
        )
        
        session['unidades'] = api_data['unidades']
        for unit_id, unit_name in api_data['unidades'].items():
            if unit_name == session['target_unit_name']:
                session['selected_unit_id'] = unit_id
                break

        agendas = api_data['agendas_completas']
        
        all_appointments_for_df = []
        status_map = {
            "O": "Atendido (Obs)", "B": "Compareceu",
            "E": "Pagamento Realizado", "R": "Confirmado", "A": "Atendido com procedimento", None: "Agendado"
        }

        for prof_nome, agenda_data in agendas.items():
            for slot in agenda_data['horarios']:
                status_bruto = slot.get('situacao')
                if slot.get('cd_paciente') == 'COMPROMISSO':
                    status_legivel = 'Compromisso'
                    paciente = 'Compromisso'
                else:
                    status_legivel = "Faltou" if slot.get('faltou') == 'F' else status_map.get(status_bruto, "Disponível" if status_bruto == "Disponível" else f"Status '{status_bruto}'")
                    paciente = slot.get('nome', '')

                slot['status'] = status_legivel
                slot['formatedHour'] = slot.get('hora_agenda', '')
                slot['patient'] = paciente
                slot['observation'] = slot.get('observacao', '')
                slot['appointmentId'] = slot.get('chave', '')
                slot['patientId'] = slot.get('cd_paciente', '')
                slot['duration'] = int(slot.get('duracao_agenda', default_duration))
                slot['profissional_nome'] = prof_nome
                all_appointments_for_df.append(slot)

        if all_appointments_for_df:
            df = pd.DataFrame(all_appointments_for_df)
            df_ocupados = df[df['status'] != 'Disponível']
            
            if not df_ocupados.empty:
                summary_table = pd.crosstab(df_ocupados['status'], df_ocupados['profissional_nome'])
                summary_table['Total'] = summary_table.sum(axis=1)
                table_headers = summary_table.columns.tolist()
                table_index = summary_table.index.tolist()
                table_body = summary_table.values.tolist()

        last_updated_formatted = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    except Exception as e:
        print(f"Ocorreu um erro ao buscar ou processar os dados: {e}")
        # Futuramente, podemos passar uma mensagem de erro para o template aqui
        
    return render_template('index.html', 
                           selected_date=selected_date,
                           last_updated_formatted=last_updated_formatted,
                           summary_metrics={},
                           agendas=agendas,
                           table_headers=table_headers,
                           table_index=table_index,
                           table_body=table_body,
                           conversion_data_for_selected_day={},
                           status_styles=status_styles,
                           default_duration=default_duration,
                           profissionais_stats_confirmacao=[],
                           profissionais_stats_ocupacao=[],
                           profissionais_stats_conversao=[],
                           agenda_url_template="http://exemplo.com/{}/{}")

@bp.route('/switch_unit/<direction>')
def switch_unit(direction):
    if 'unidades' in session and len(session['unidades']) > 1:
        unit_ids = list(session['unidades'].keys())
        current_id = session.get('selected_unit_id')
        try:
            current_index = unit_ids.index(current_id)
        except ValueError:
            current_index = 0
        if direction == 'next':
            next_index = (current_index + 1) % len(unit_ids)
        else:
            next_index = (current_index - 1 + len(unit_ids)) % len(unit_ids)
        new_unit_id = unit_ids[next_index]
        session['selected_unit_id'] = new_unit_id
        session['target_unit_name'] = session['unidades'][new_unit_id]
    return redirect(url_for('main.index'))