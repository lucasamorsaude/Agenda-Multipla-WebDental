# app/cache.py

from flask import Blueprint, jsonify, request, session
import firebase_admin
from firebase_admin import firestore

bp = Blueprint('cache', __name__, url_prefix='/cache')

@bp.route('/force_update', methods=['POST'])
def force_update_day_cache_sync():
    """
    Deleta o documento de cache para uma data e unidade específicas no Firestore,
    forçando uma nova busca na próxima vez que a página for carregada.
    """
    try:
        # Pega os dados enviados pelo JavaScript
        selected_date = request.form.get('selected_date_force_update')
        
        # Precisamos do nome da unidade para montar a chave do cache
        unit_name = session.get('target_unit_name')

        if not selected_date or not unit_name:
            return jsonify({'status': 'error', 'message': 'Data ou unidade não fornecida.'}), 400

        # Monta a chave do cache EXATAMENTE como no services.py
        cache_key = f"{unit_name.replace(' ', '_')}_{selected_date}"
        
        # Conecta ao Firestore e deleta o documento
        db = firestore.client()
        doc_ref = db.collection('agendas_cache').document(cache_key)
        doc_ref.delete()
        
        print(f"Cache para a chave '{cache_key}' foi deletado com sucesso.")
        
        return jsonify({'status': 'success', 'message': 'Cache do dia limpo! A página será recarregada.'})

    except Exception as e:
        print(f"Erro ao forçar atualização do cache: {e}")
        return jsonify({'status': 'error', 'message': 'Ocorreu um erro no servidor ao limpar o cache.'}), 500