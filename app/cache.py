# app/cache.py

from flask import Blueprint, jsonify, request, session
import firebase_admin
from firebase_admin import firestore

bp = Blueprint('cache', __name__, url_prefix='/cache')

@bp.route('/force_update', methods=['POST'])
def force_update_day_cache_sync():
    """
    Deleta o documento de cache para uma data e unidade específicas no Firestore.
    """
    try:
        selected_date = request.form.get('selected_date_force_update')
        unit_id = request.form.get('unit_id') # O JS agora envia o unit_id
        
        # Usa a lista de unidades da sessão para encontrar o nome correspondente ao ID
        unidades_na_sessao = session.get('unidades', {})
        unit_name = unidades_na_sessao.get(unit_id)

        if not selected_date or not unit_name:
            return jsonify({'status': 'error', 'message': 'Data ou unidade inválida.'}), 400

        cache_key = f"{unit_name.replace(' ', '_')}_{selected_date}"
        
        db = firestore.client()
        doc_ref = db.collection('agendas_cache').document(cache_key)
        doc_ref.delete()
        
        print(f"Cache para a chave '{cache_key}' foi deletado com sucesso.")
        
        return jsonify({'status': 'success', 'message': f'Cache para {unit_name} limpo!'})

    except Exception as e:
        print(f"Erro ao forçar atualização do cache: {e}")
        return jsonify({'status': 'error', 'message': 'Ocorreu um erro no servidor ao limpar o cache.'}), 500