# app/services.py

import os
import requests
from datetime import datetime, timedelta, timezone
import firebase_admin
from firebase_admin import credentials, firestore
import json

# --- INICIALIZAÇÃO E CONSTANTES (sem alterações) ---
cred_path = os.path.join(os.path.dirname(__file__), '..', 'chave_firebase.json')
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
db = firestore.client()
CACHE_DURATION_MINUTES = 480
URL_LOGIN_PAGE = "https://sistema.webdentalsolucoes.io/index.php"
URL_GET_UNITS = "https://sistema.webdentalsolucoes.io/index_ajax.php"
URL_API_BASE = "https://apislave.webdentalsolucoes.io/api/"
CD_FILIAL = "275"
CHAVE_USUARIO = "L27500020240108110613"

def _login_and_get_units(session, username, password, target_unit_name):
    # ... (esta função continua a mesma) ...
    print("[DEBUG] ETAPA 1.1: Acessando página de login inicial...")
    session.get(URL_LOGIN_PAGE)
    print("[DEBUG] ETAPA 1.2: Buscando lista de unidades...")
    payload_units = {'ajax': 'true', 'usuario': username, 'senha': password, 'bd': 'clinicatodos'}
    response_units = session.post(URL_GET_UNITS, data=payload_units)
    response_units.raise_for_status()
    units_data = response_units.json()
    all_units = {u['value']: u['name'].encode('latin1').decode('unicode_escape') for u in units_data}
    target_unit_id = next((uid for uid, name in all_units.items() if name == target_unit_name), None)
    if not target_unit_id:
        raise ValueError(f"ERRO: Unidade '{target_unit_name}' não encontrada.")
    print("[DEBUG] ETAPA 1.3: Fazendo login final na unidade...")
    payload_login = {'banco': 'clinicatodos', 'usuario': username, 'senha': password, 'unidade_login': target_unit_id, 'btn_entrar': ''}
    response_login = session.post(URL_LOGIN_PAGE, data=payload_login)
    response_login.raise_for_status()
    if "login" in response_login.url:
        raise ConnectionError("ERRO: Falha na autenticação final.")
    return target_unit_id, all_units

def _build_dynamic_schedule(work_shifts, booked_appointments, medico_chave):
    # ... (esta função continua a mesma) ...
    final_schedule = []
    if not work_shifts:
        return final_schedule
    work_shifts.sort(key=lambda x: x.get('horario_inicio', ''))
    booked_slots_map = {slot['hora_agenda']: slot for slot in booked_appointments}
    default_duration = int(work_shifts[0].get('duracao', 15))
    for shift in work_shifts:
        try:
            start_time_obj = datetime.strptime(shift['horario_inicio'], '%H:%M:%S').time()
            end_time_obj = datetime.strptime(shift['horario_fim'], '%H:%M:%S').time()
            current_time = datetime.combine(datetime.today(), start_time_obj)
            end_time = datetime.combine(datetime.today(), end_time_obj)
            while current_time < end_time:
                time_str = current_time.strftime('%H:%M')
                appointment = booked_slots_map.get(time_str)
                if appointment:
                    final_schedule.append(appointment)
                    duration = int(appointment.get('duracao_agenda', default_duration))
                    current_time += timedelta(minutes=duration)
                else:
                    final_schedule.append({'hora_agenda': time_str, 'situacao': 'Disponível', 'nome': '', 'chave': f"vago_{medico_chave}_{time_str}", 'cd_paciente': None})
                    current_time += timedelta(minutes=default_duration)
        except (ValueError, TypeError) as e:
            print(f"Aviso: Ignorando turno com formato inválido. Erro: {e}")
            continue
    return final_schedule

def get_webdental_data(username, password, target_unit_name, selected_date_str):
    # ... (lógica de cache continua a mesma) ...
    cache_key = f"{target_unit_name.replace(' ', '_')}_{selected_date_str}"
    doc_ref = db.collection('agendas_cache').document(cache_key)
    cached_doc = doc_ref.get()
    if cached_doc.exists:
        cached_data = cached_doc.to_dict()
        cached_timestamp = cached_data.get('timestamp')
        if datetime.now(timezone.utc) - cached_timestamp < timedelta(minutes=CACHE_DURATION_MINUTES):
            print(f"Dados encontrados no cache para {cache_key}! Retornando dados salvos.")
            return cached_data
    
    print(f"Cache não encontrado ou expirado para {cache_key}. Buscando dados na API...")
    
    selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d')
    with requests.Session() as s:
        s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        print("\n[DEBUG] ETAPA 1: TENTANDO FAZER LOGIN...")
        unit_id, all_units = _login_and_get_units(s, username, password, target_unit_name)
        print("[DEBUG] ETAPA 1 CONCLUÍDA: Login realizado com sucesso.")

        data_formatada_br = selected_date.strftime("%d/%m/%Y")
        data_formatada_sys = selected_date.strftime("%Y-%m-%d")
        dia_semana = selected_date.isoweekday() % 7 + 1
        
        payload_medicos = {"dia_semana": dia_semana, "data_a": data_formatada_br, "data_a_formt": data_formatada_sys, "data_c": data_formatada_br, "cd_filial": CD_FILIAL, "chaveUsuario": CHAVE_USUARIO, "data_Hoje": data_formatada_br, "data_Hoje_System": data_formatada_sys, "rotaAcao": "AgendaAbrir", "unidade": unit_id}
        
        medicos = []
        try:
            response_medicos = s.post(f"{URL_API_BASE}GetSelectMedicos", json=payload_medicos)
            medicos_data = response_medicos.json()
            medicos_list = medicos_data.get('dados', [])
            medicos_list.sort(key=lambda x: x.get('nm_prestador', '').strip())
            medicos = medicos_list
        except requests.exceptions.JSONDecodeError:
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("!!! ERRO FATAL NA ETAPA 2: BUSCA DE PROFISSIONAIS !!!")
            print(f"!!! A API retornou algo que não é JSON. Resposta: {response_medicos.text[:500]}")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            raise # Para o processo aqui e mostra o erro
        
        all_professionals_schedule = {}
        for medico in medicos:
            medico_chave = medico['chave']
            medico_nome = medico['nm_prestador'].strip()

            payload_horarios = {"cd_prestador": medico_chave, "data_fim": data_formatada_sys}
            turnos_de_trabalho = []
            try:
                response_horarios = s.post(f"{URL_API_BASE}getCadeirasPrestador", json=payload_horarios)
                horarios_data = response_horarios.json()
                turnos_de_trabalho = [t for t in horarios_data if t.get('data_inicio') == data_formatada_sys]
            except requests.exceptions.JSONDecodeError:
                print(f"  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print(f"  !!! ERRO FATAL NA ETAPA 3.1: BUSCA DE HORÁRIOS para {medico_nome} !!!")
                print(f"  !!! A API retornou algo que não é JSON. Resposta: {response_horarios.text[:500]}")
                print(f"  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                continue # Pula para o próximo médico
            
            payload_agenda = {"cadeira": {"cadeira": 4, "cadeiraValue": 1, "cadeiraValueSelect": 0}, "cd_filial": CD_FILIAL, "chaveUsuario": CHAVE_USUARIO, "data_Hoje": data_formatada_br, "data_Hoje_System": data_formatada_sys, "data_a": data_formatada_br, "data_a_formt": data_formatada_sys, "data_c": data_formatada_br, "dia_semana": dia_semana, "filial": int(CD_FILIAL), "medico": medico_chave, "medicosChave": [m['chave'] for m in medicos], "rotaAcao": "agendaSelecDr", "unidade": unit_id}
            
            agendamentos = []
            try:
                response_agenda = s.post(f"{URL_API_BASE}GetAgendaDia", json=payload_agenda)
                agenda_data = response_agenda.json()
                agendamentos = sorted(agenda_data.get('dados', []), key=lambda x: x.get('hora_agenda', ''))
            except requests.exceptions.JSONDecodeError:
                print(f"  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print(f"  !!! ERRO FATAL NA ETAPA 3.2: BUSCA DE AGENDAMENTOS para {medico_nome} !!!")
                print(f"  !!! A API retornou algo que não é JSON. Resposta: {response_agenda.text[:500]}")
                print(f"  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                # Continua mesmo com erro, para a agenda do médico aparecer vazia
            
            final_schedule_slots = _build_dynamic_schedule(turnos_de_trabalho, agendamentos, medico_chave)
            all_professionals_schedule[medico_nome] = {'id': medico_chave, 'horarios': final_schedule_slots}
        
        fresh_data = {"agendas_completas": all_professionals_schedule, "unidades": all_units}
        current_timestamp = datetime.now(timezone.utc)
        data_to_cache_and_return = {'timestamp': current_timestamp, 'data': fresh_data}
        doc_ref.set(data_to_cache_and_return)
        print("\n[DEBUG] ETAPA 4: Novos dados salvos no cache.")
        return data_to_cache_and_return

# --- FUNÇÃO QUE FALTAVA ADICIONADA AQUI ---
def fetch_single_appointment_details(username, password, target_unit_name, selected_date_str, appointment_id_to_find):
    """
    Busca a agenda completa de um dia e retorna apenas o dicionário
    do agendamento específico que estamos procurando.
    """
    # Reutiliza nossa função principal para pegar todos os dados do dia
    full_data = get_webdental_data(username, password, target_unit_name, selected_date_str)
    
    # Extrai a lista de todos os horários de todos os profissionais
    all_slots = [
        slot 
        for professional_agenda in full_data.get('agendas_completas', {}).values()
        for slot in professional_agenda.get('horarios', [])
    ]
    
    # Procura o agendamento específico pelo ID (chave)
    found_appointment = next((slot for slot in all_slots if slot.get('chave') == appointment_id_to_find), None)
    
    return found_appointment

def fetch_full_appointment_details(session, appointment_id, patient_id, selected_date, funcionario_id="L43000020250424094808"):
    """
    Busca os detalhes completos de um agendamento usando a nova API 'GetDadosConultaCompleta'.
    """
    print(f"Buscando detalhes completos para o agendamento: {appointment_id}")

    payload = {
        "chave_agenda": appointment_id,
        "paciente": patient_id,
        "data_agenda": selected_date,
        "funcionario": funcionario_id
    }

    response = session.post(f"{URL_API_BASE}GetDadosConultaCompleta", json=payload)
    response.raise_for_status()
    
    return response.json()