from flask import request, jsonify, session, redirect, url_for, render_template
from flask_socketio import emit, join_room, leave_room
from datetime import datetime

sesiune_browser_useri = {}
admin_connected = False
_chatbot = None


def set_chatbot(bot):
    global _chatbot
    _chatbot = bot


def salvare_istoric_chat(id_sesiune_utilizatori, messages):
    filename = f"istoric_msj_{id_sesiune_utilizatori}.txt"
    with open(filename, 'w', encoding='utf-8') as file:
        for message in messages:
            file.write(f"{message['timp']} {message['sender']} said: {message['text']}\n")
    print(f"A fost salvat istoricul chat-ului pentru {id_sesiune_utilizatori}")


def init_socket_events(app, socketio):

    @app.route('/admin_chat')
    def admin():
        if not session.get('status_login_utilizator') or session.get('rol_administrativ') != 'admin':
            return redirect(url_for('autentificare_admin'))
        return render_template('admin.html')

    @app.route('/chat', methods=['POST'])
    def chat():
        global admin_connected
        id_sesiune_utilizatori = request.cookies.get('id_sesiune_utilizatori')
        preluare_intrebare = request.form['question']
        timp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if id_sesiune_utilizatori not in sesiune_browser_useri:
            sesiune_browser_useri[id_sesiune_utilizatori] = {'comutare_mod_chat': False, 'messages': [], 'active': True}
        if 'contor_intrebari_nerecunoscute' not in sesiune_browser_useri[id_sesiune_utilizatori]:
            sesiune_browser_useri[id_sesiune_utilizatori]['contor_intrebari_nerecunoscute'] = 0

        if preluare_intrebare.lower() == 'solicitare interventie admin':
            if admin_connected:
                sesiune_browser_useri[id_sesiune_utilizatori]['comutare_mod_chat'] = True
                sesiune_browser_useri[id_sesiune_utilizatori]['messages'].append({'sender': 'system', 'text': 'Chat pornit', 'timp': timp})
                socketio.emit('session_activated', {'id_sesiune_utilizatori': id_sesiune_utilizatori}, namespace='/admin')
                socketio.emit('admin_chat_active', {'id_sesiune_utilizatori': id_sesiune_utilizatori}, namespace='/')
                socketio.emit('mesaj_de_la_utilizator', {'data': 'Solicitare intervenție admin', 'id_sesiune_utilizatori': id_sesiune_utilizatori}, namespace='/admin')
                return jsonify({'raspuns': 'Modul chat direct activat. Așteptați un operator...'})
            else:
                return jsonify({'raspuns': 'Operatorul nu este disponibil în acest moment. Vă rugăm să încercați mai târziu.'})

        elif preluare_intrebare.lower() == 'anulare interventie admin':
            sesiune_browser_useri[id_sesiune_utilizatori]['comutare_mod_chat'] = False
            socketio.emit('admin_chat_inactive', {'id_sesiune_utilizatori': id_sesiune_utilizatori}, namespace='/')
            return jsonify({'raspuns': 'Solicitarea de intervenție admin a fost anulată. Chat-ul continuă normal.'})

        elif preluare_intrebare.lower() == 'oprire chat':
            sesiune_browser_useri[id_sesiune_utilizatori]['comutare_mod_chat'] = False
            return jsonify({'raspuns': 'Chatul direct cu reprezentatul universitatii a fost oprit.'})

        if sesiune_browser_useri[id_sesiune_utilizatori]['comutare_mod_chat']:
            sesiune_browser_useri[id_sesiune_utilizatori]['messages'].append({'sender': 'user', 'text': preluare_intrebare, 'timp': timp})
            socketio.emit('mesaj_de_la_utilizator', {'data': preluare_intrebare, 'id_sesiune_utilizatori': id_sesiune_utilizatori}, namespace='/admin')
            return '', 200
        else:
            intents = _chatbot.clasificare(preluare_intrebare)
            response = _chatbot.obtine_raspuns(intents, preluare_intrebare)
            if intents[0]['intent'] == 'neintelegere':
                sesiune_browser_useri[id_sesiune_utilizatori]['contor_intrebari_nerecunoscute'] += 1
            else:
                sesiune_browser_useri[id_sesiune_utilizatori]['contor_intrebari_nerecunoscute'] = 0

            if sesiune_browser_useri[id_sesiune_utilizatori]['contor_intrebari_nerecunoscute'] >= 3:
                sesiune_browser_useri[id_sesiune_utilizatori]['contor_intrebari_nerecunoscute'] = 0
                return jsonify({'raspuns': response, 'arata_optiune_chat_live': True})

            return jsonify({'raspuns': response})

    @socketio.on('connect', namespace='/admin')
    def on_admin_connect():
        global admin_connected
        admin_connected = True
        join_room('admin_room')
        print('Administrator conectat la camera admin_room.')

    @socketio.on('disconnect', namespace='/admin')
    def eveniment_deconectare_admin():
        global admin_connected
        admin_connected = False
        leave_room('admin_room')
        print('Admin deconectat')

    @socketio.on('connect')
    def eveniment_conectare_user():
        id_sesiune_utilizatori = request.cookies.get('id_sesiune_utilizatori')
        join_room(id_sesiune_utilizatori)
        print(f"User-ul {id_sesiune_utilizatori} s-a conectat si sa alaturat la camera: {id_sesiune_utilizatori}")

    @socketio.on('disconnect')
    def eveniment_deconectare_user():
        id_sesiune_utilizatori = request.cookies.get('id_sesiune_utilizatori')
        if id_sesiune_utilizatori in sesiune_browser_useri:
            sesiune_browser_useri[id_sesiune_utilizatori]['active'] = False
            print(f"User-ul {id_sesiune_utilizatori} deconectat, sesiune marcata ca fiind inactiva.")
            socketio.emit('user_disconnected', {'id_sesiune_utilizatori': id_sesiune_utilizatori, 'active': False}, namespace='/admin', room='admin_room')

    @socketio.on('mesaj_de_la_admin', namespace='/admin')
    def eveniment_msg_admin(data):
        id_sesiune_utilizatori = data['id_sesiune_utilizatori']
        message = data['message']
        timp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"ADM a trimis mesaj la {id_sesiune_utilizatori} la ora {timp}: {message}")
        emit('mesaj_de_la_admin', {'data': message}, namespace='/', room=id_sesiune_utilizatori)
        if id_sesiune_utilizatori in sesiune_browser_useri:
            sesiune_browser_useri[id_sesiune_utilizatori]['messages'].append({'sender': 'admin', 'text': message, 'timp': timp})

    @socketio.on('close_session', namespace='/admin')
    def inchidere_sesiune(data):
        id_sesiune_utilizatori = data['id_sesiune_utilizatori']
        if id_sesiune_utilizatori in sesiune_browser_useri:
            salvare_istoric_chat(id_sesiune_utilizatori, sesiune_browser_useri[id_sesiune_utilizatori]['messages'])
            sesiune_browser_useri[id_sesiune_utilizatori] = {'comutare_mod_chat': False, 'messages': [], 'active': False}
            emit('session_closed', {'message': 'Aceasta sesiune de chat a fost inchisa de admin.'}, room=id_sesiune_utilizatori, namespace='/')
            print(f"Sesiune inchisa pentru {id_sesiune_utilizatori}")
