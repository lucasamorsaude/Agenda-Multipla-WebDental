# app/superadmin.py

import os
from flask import Blueprint, render_template, request, session
from flask_login import login_required, current_user
from datetime import datetime
import pandas as pd
from . import services

bp = Blueprint('superadmin', __name__, url_prefix='/superadmin')

def is_superadmin():
    """Função de verificação para garantir que apenas superadmins acessem."""
    return current_user.is_authenticated and current_user.role == 'superadmin'

@bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if not is_superadmin():
        return "Acesso negado.", 403

    selected_date = request.form.get('selected_date', datetime.now().strftime('%Y-%m-%d'))
    
    global_summary = {}
    units_stats = []

    if request.method == 'POST':
        try:
            # Pega a lista de todas as unidades disponíveis
            all_units = services.get_all_available_units(
                os.getenv("USUARIO_ODONTO"),
                os.getenv("SENHA_ODONTO")
            )

            all_dfs = []
            # Loop para buscar os dados de cada unidade
            for unit_id, unit_name in all_units.items():
                result = services.get_webdental_data(
                    username=os.getenv("USUARIO_ODONTO"),
                    password=os.getenv("SENHA_ODONTO"),
                    target_unit_name=unit_name,
                    selected_date_str=selected_date
                )
                
                agendas = result['data']['agendas_completas']
                all_appointments = [slot for data in agendas.values() for slot in data['horarios']]
                
                if all_appointments:
                    df = pd.DataFrame(all_appointments)
                    df['unit_name'] = unit_name # Adiciona o nome da unidade para agrupar depois
                    all_dfs.append(df)
            
            # Concatena os dados de todas as unidades em um único DataFrame
            if all_dfs:
                full_df = pd.concat(all_dfs, ignore_index=True)
                
                # Mapeamento de status
                status_map = {"O": "Atendido (Obs)","B": "Compareceu","E": "Pagamento Realizado","R": "Confirmado","A": "Atendido com procedimento",None: "Agendado"}
                full_df['status_legivel'] = full_df.apply(
                    lambda row: "Faltou" if row.get('faltou') == 'F' else status_map.get(row['situacao'], "Disponível" if row.get('situacao') == "Disponível" else f"Status '{row.get('situacao')}'"),
                    axis=1
                )
                df_ocupados = full_df[full_df['status_legivel'] != 'Disponível']
                status_atendido = ['Atendido (Obs)', 'Atendido com procedimento', 'Pagamento Realizado']
                
                # Calcula métricas globais
                total_agendado_global = len(df_ocupados)
                total_atendidos_global = len(df_ocupados[df_ocupados['status_legivel'].isin(status_atendido)])
                total_confirmado_global = len(df_ocupados[df_ocupados['status_legivel'] == 'Confirmado'])
                total_slots_global = len(full_df)

                global_summary = {
                    'total_agendado_geral': total_agendado_global,
                    'total_atendidos_global': total_atendidos_global,
                    'taxa_confirmacao_global': f"{(total_confirmado_global / total_agendado_global * 100):.0f}%" if total_agendado_global > 0 else "0%",
                    'taxa_ocupacao_global': f"{(total_agendado_global / total_slots_global * 100):.0f}%" if total_slots_global > 0 else "0%",
                    'taxa_conversao_global': f"{(total_atendidos_global / total_agendado_global * 100):.0f}%" if total_agendado_global > 0 else "0%"
                }

                # Calcula métricas por unidade
                for unit_name, group in full_df.groupby('unit_name'):
                    group_ocupados = group[group['status_legivel'] != 'Disponível']
                    agendados = len(group_ocupados)
                    atendidos = len(group_ocupados[group_ocupados['status_legivel'].isin(status_atendido)])
                    confirmados = len(group_ocupados[group_ocupados['status_legivel'] == 'Confirmado'])
                    faltosos = len(group_ocupados[group_ocupados['status_legivel'] == 'Faltou'])
                    total_slots = len(group)

                    units_stats.append({
                        'name': unit_name,
                        'agendados': agendados,
                        'atendidos': atendidos,
                        'confirmacao_numeric': (confirmados / agendados * 100) if agendados > 0 else 0,
                        'confirmacao': f"{(confirmados / agendados * 100):.0f}%" if agendados > 0 else "0%",
                        'nao_compareceu': faltosos,
                        'ocupacao_numeric': (agendados / total_slots * 100) if total_slots > 0 else 0,
                        'ocupacao': f"{(agendados / total_slots * 100):.0f}%" if total_slots > 0 else "0%",
                        'conversao_numeric': (atendidos / agendados * 100) if agendados > 0 else 0,
                        'conversao': f"{(atendidos / agendados * 100):.0f}%" if agendados > 0 else "0%"
                    })
                
        except Exception as e:
            print(f"Erro no dashboard superadmin: {e}")

    return render_template('superadmin_dashboard.html', 
                           selected_date=selected_date, 
                           global_summary=global_summary, 
                           units_stats=units_stats)