from flask import render_template, request, redirect, url_for, jsonify, session, make_response
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from threading import Thread
from database import create_connection


def init_app_router(app):
    app.config.update(MAIL_SERVER='', MAIL_PORT=587, MAIL_USE_TLS=True, MAIL_USERNAME='', MAIL_PASSWORD='')
    mail = Mail(app)

    def trimitere_email_asincron(app, msg):
        with app.app_context():
            mail.send(msg)

    def trimitere_email(subject, recipient, nume_utilizator, email, rol_administrativ, parola=None):
        print("Trimitere email...")
        html_body = render_template('template_email.html', nume_utilizator=nume_utilizator, email=email, rol_administrativ=rol_administrativ, parola=parola)
        msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[recipient])
        msg.html = html_body
        print(f"S-a trimis emailul la {recipient} cu parola {parola}")
        Thread(target=trimitere_email_asincron, args=(app, msg)).start()

    @app.route('/test_email')
    def test_email():
        try:
            trimitere_email(
                subject='Test Email',
                recipient='',
                nume_utilizator='Test User',
                email='',
                rol_administrativ='user',
                parola=''
            )
            return "Email trimis cu succes!"
        except Exception as e:
            return str(e)

    @app.route('/logare_admin', methods=['GET', 'POST'])
    def autentificare_admin():
        if request.method == 'POST':
            adresa_email_utilizator = request.form['adresa_email']
            parola_utilizator = request.form['parola']
            retine_parola = 'retine_parola' in request.form
            con_bd = create_connection()
            try:
                with con_bd.cursor() as cursor:
                    cursor.execute("SELECT * FROM utilizatori WHERE email=%s", (adresa_email_utilizator,))
                    utilizator = cursor.fetchone()
                    if utilizator and check_password_hash(utilizator[3], parola_utilizator):
                        session['status_login_utilizator'] = True
                        session['adresa_email'] = utilizator[1]
                        session['rol_administrativ'] = utilizator[4]

                        if utilizator[4] == 'admin':
                            return redirect(url_for('dashboard'))
                        elif utilizator[4] == 'operator':
                            return redirect(url_for('dashboard_operator'))
                        else:
                            return render_template('login.html', error="Rol necunoscut")
                    else:
                        return render_template('login.html', error="Utilizator sau parolă invalidă")
            finally:
                con_bd.close()
        else:
            cookie_sesiune = request.cookies.get('cookie_sesiune')
            if cookie_sesiune:
                con_bd = create_connection()
                try:
                    with con_bd.cursor() as cursor:
                        cursor.execute("SELECT * FROM utilizatori WHERE email=%s", (cookie_sesiune,))
                        utilizator = cursor.fetchone()
                        if utilizator:
                            session['status_login_utilizator'] = True
                            session['adresa_email'] = utilizator[1]
                            session['rol_administrativ'] = utilizator[4]
                            if utilizator[4] == 'admin':
                                return redirect(url_for('dashboard'))
                            elif utilizator[4] == 'operator':
                                return redirect(url_for('dashboard_operator'))
                finally:
                    con_bd.close()
        return render_template('login.html')

    @app.route('/dashboard_operator')
    def dashboard_operator():
        if not session.get('status_login_utilizator') or session.get('rol_administrativ') != 'operator':
            return redirect(url_for('autentificare_admin'))
        return render_template('dashboard_operator.html', role=session['rol_administrativ'])

    @app.route('/admin_chat_operator')
    def admin_operator():
        if not session.get('status_login_utilizator') or session.get('rol_administrativ') != 'operator':
            return redirect(url_for('autentificare_admin'))
        return render_template('admin_operator.html')

    @app.route('/intrebari_fara_raspuns_operator')
    def pag_intrebari_fara_raspuns_operator():
        if not session.get('status_login_utilizator') or session.get('rol_administrativ') != 'operator':
            return redirect(url_for('autentificare_admin'))
        return render_template('intrebari_fara_raspuns_operator.html')

    @app.route('/delogare')
    def logout():
        session.pop('status_login_utilizator', None)
        session.pop('adresa_email', None)
        session.pop('rol_administrativ', None)
        raspuns_autentificare = make_response(redirect(url_for('autentificare_admin')))
        raspuns_autentificare.delete_cookie('cookie_sesiune')
        return raspuns_autentificare

    @app.route('/dashboard')
    def dashboard():
        if not session.get('status_login_utilizator'):
            return redirect(url_for('autentificare_admin'))
        return render_template('dashboard.html', role=session['rol_administrativ'])

    @app.route('/administrare_utilizatori')
    def administrare_utilizatori():
        if not session.get('status_login_utilizator') or session.get('rol_administrativ') != 'admin':
            return redirect(url_for('autentificare_admin'))
        con_bd = create_connection()
        try:
            with con_bd.cursor() as cursor:
                cursor.execute("SELECT id, nume_utilizator, email, rol_administrativ FROM utilizatori")
                utilizatori = cursor.fetchall()
        finally:
            con_bd.close()
        return render_template('manage_users.html', utilizatori=utilizatori)

    @app.route('/adaugare_utilizatori', methods=['POST'])
    def adaugare_utilizatori():
        if not session.get('status_login_utilizator') or session.get('rol_administrativ') != 'admin':
            return jsonify({'status': 'unauthorized'})
        data = request.get_json()
        nume_utilizator = data['nume_utilizator']
        email = data['email']
        parola = generate_password_hash(data['parola'], method='pbkdf2:sha256')
        rol_administrativ = data['rol_administrativ']
        solicitare_trimitere_email = data.get('solicitare_trimitere_email', False)
        con_bd = create_connection()
        try:
            with con_bd.cursor() as cursor:
                cursor.execute("SELECT * FROM utilizatori WHERE email=%s", (email,))
                if cursor.fetchone():
                    return jsonify({'status': 'error', 'message': 'Email deja existent'})

                cursor.execute("INSERT INTO utilizatori (nume_utilizator, email, parola, rol_administrativ) VALUES (%s, %s, %s, %s)", (nume_utilizator, email, parola, rol_administrativ))
                con_bd.commit()

                if solicitare_trimitere_email:
                    trimitere_email(
                        subject='Datele contului de utilizator',
                        recipient=email,
                        nume_utilizator=nume_utilizator,
                        email=email,
                        rol_administrativ=rol_administrativ,
                        parola=data["parola"]
                    )
        finally:
            con_bd.close()
        return jsonify({'status': 'success'})

    @app.route('/actualizare_utilizatori', methods=['POST'])
    def update_user():
        if not session.get('status_login_utilizator') or session.get('rol_administrativ') != 'admin':
            return jsonify({'status': 'Sesiune neautorizata! Nu ai permisiunea sa faci modificari in tabele!!!!!'})
        data = request.get_json()
        app.logger.info("Date primite pentru actualizare utilizator: %s", data)

        id_utilizator = data['id']
        nume_utilizator = data['username']
        email = data['email']
        parola = generate_password_hash(data['parola'], method='pbkdf2:sha256') if 'parola' in data and data['parola'] else None
        rol_administrativ = data['role']
        solicitare_trimitere_email = data.get('solicitare_trimitere_email', False)

        con_bd = create_connection()
        try:
            with con_bd.cursor() as cursor:
                if parola:
                    cursor.execute("UPDATE utilizatori SET nume_utilizator=%s, email=%s, parola=%s, rol_administrativ=%s WHERE id=%s",
                                (nume_utilizator, email, parola, rol_administrativ, id_utilizator))
                else:
                    cursor.execute("UPDATE utilizatori SET nume_utilizator=%s, email=%s, rol_administrativ=%s WHERE id=%s",
                                (nume_utilizator, email, rol_administrativ, id_utilizator))

                con_bd.commit()

                if solicitare_trimitere_email:
                    email_body = f'Username: {nume_utilizator}\nRol: {rol_administrativ}'
                    if parola:
                        email_body += f'\nParola: {data["parola"]}'
                    trimitere_email(
                        subject='Datele contului actualizate',
                        recipient=email,
                        nume_utilizator=nume_utilizator,
                        email=email,
                        rol_administrativ=rol_administrativ,
                        parola=data.get("parola")
                    )
                    app.logger.info("Email de actualizare trimis către %s", email)
                else:
                    app.logger.info("Trimiterea emailului nu a fost solicitată.")
        except Exception as e:
            app.logger.error("Eroare la actualizarea utilizatorului: %s", str(e))
            return jsonify({'status': 'error', 'message': str(e)})
        finally:
            con_bd.close()

        return jsonify({'status': 'success'})

    @app.route('/stergere_utilizator', methods=['POST'])
    def delete_user():
        if not session.get('status_login_utilizator') or session.get('rol_administrativ') != 'admin':
            return jsonify({'status': 'Sesiune neautorizata! Nu ai permisiunea sa faci modificari in tabele!!!!!'})
        data = request.get_json()
        user_id = data['id']
        con_bd = create_connection()
        try:
            with con_bd.cursor() as cursor:
                cursor.execute("DELETE FROM utilizatori WHERE id=%s", (user_id,))
                con_bd.commit()
        finally:
            con_bd.close()
        return jsonify({'status': 'success'})
