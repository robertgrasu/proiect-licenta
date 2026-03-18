from flask import render_template, request, redirect, url_for, jsonify, session
from database import get_database_connection, close_conn
import requests
from threading import Thread
from itertools import zip_longest
from flask import g


def reantrenare_model_in_background():
    try:
        response = requests.post('http://localhost:5001/retrain')
        print("Incepe antrenare chatbot:", response.status_code)
    except Exception as e:
        print("Eroare in timpul antrenarii:", str(e))

def declanseaza_reantrenare():
    thread = Thread(target=reantrenare_model_in_background)
    thread.start()

def init_app_routes(app):

    @app.route('/administrare_date', methods=['GET'])
    @app.route('/administrare_date/<int:pagina>', methods=['GET'])
    def index(pagina=1):
        if not session.get('status_login_utilizator') or session.get('rol_administrativ') != 'admin':
            return redirect(url_for('autentificare_admin'))

        intrebari_per_pagina = request.args.get('length', 10, type=int)
        deplasare = (pagina - 1) * intrebari_per_pagina

        conn = get_database_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT DISTINCT i.id AS id_categorie_intentie
            FROM categorii_intentii i
            ORDER BY i.id
            LIMIT %s OFFSET %s
            """, (intrebari_per_pagina, deplasare))
            categorii_intentii_per_pagina = cursor.fetchall()
            id_categorii_intentii = [rand_rezultat['id_categorie_intentie'] for rand_rezultat in categorii_intentii_per_pagina]
            print(categorii_intentii_per_pagina)
            if not id_categorii_intentii:
                return render_template('intents.html', categorii_intentii=[], pagini_totale=0, pagina_curenta=pagina)

            cursor.execute("""
            SELECT i.id AS id_categorie_intentie, i.tag, p.id AS id_intrebare, p.intrebare, r.id AS id_raspuns, r.raspuns
            FROM categorii_intentii i
            LEFT JOIN set_intrebari p ON i.id = p.id_categorie_intentie
            LEFT JOIN set_raspunsuri r ON i.id = r.id_categorie_intentie
            WHERE i.id IN (%s)
            ORDER BY i.id, p.id, r.id
            """ % ','.join(['%s'] * len(id_categorii_intentii)), tuple(id_categorii_intentii))
            date_db = cursor.fetchall()
            print(date_db)
            cursor.execute("SELECT COUNT(*) FROM categorii_intentii")
            total_categorii_intentii = cursor.fetchone()['COUNT(*)']

        categorii_intentii = {}
        for rand_rezultat in date_db:
            id_categorie_intentie = rand_rezultat['id_categorie_intentie']
            if id_categorie_intentie not in categorii_intentii:
                categorii_intentii[id_categorie_intentie] = {
                    'id': id_categorie_intentie,
                    'tag': rand_rezultat['tag'],
                    'set_intrebari': [],
                    'set_raspunsuri': []
                }

            if {'id': rand_rezultat['id_intrebare'], 'intrebare': rand_rezultat['intrebare']} not in categorii_intentii[id_categorie_intentie]['set_intrebari'] and rand_rezultat['intrebare']:
                categorii_intentii[id_categorie_intentie]['set_intrebari'].append({'id': rand_rezultat['id_intrebare'], 'intrebare': rand_rezultat['intrebare']})

            if {'id': rand_rezultat['id_raspuns'], 'raspuns': rand_rezultat['raspuns']} not in categorii_intentii[id_categorie_intentie]['set_raspunsuri'] and rand_rezultat['raspuns']:
                categorii_intentii[id_categorie_intentie]['set_raspunsuri'].append({'id': rand_rezultat['id_raspuns'], 'raspuns': rand_rezultat['raspuns']})

        pagini_totale = (total_categorii_intentii + intrebari_per_pagina - 1) // intrebari_per_pagina

        return render_template('intents.html', categorii_intentii=list(categorii_intentii.values()), pagini_totale=pagini_totale, pagina_curenta=pagina)


    @app.route('/interogare_baza_date')
    def interogare_baza_date():
        interogare_baza_de_date = request.args.get('q', '').strip()
        if not interogare_baza_de_date:
            return redirect(url_for('index'))

        cautare_cuvinte_cheie = f'\\b{interogare_baza_de_date}\\b'
        conn = get_database_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT DISTINCT i.id
            FROM categorii_intentii i
            LEFT JOIN set_intrebari p ON i.id = p.id_categorie_intentie
            LEFT JOIN set_raspunsuri r ON i.id = r.id_categorie_intentie
            WHERE i.tag REGEXP %s OR p.intrebare REGEXP %s OR r.raspuns REGEXP %s
            ORDER BY i.id
            """, (cautare_cuvinte_cheie, cautare_cuvinte_cheie, cautare_cuvinte_cheie))
            id_categorii_intentii = [rand_rezultat['id'] for rand_rezultat in cursor.fetchall()]

            if not id_categorii_intentii:
                return render_template('intents.html', categorii_intentii=[], pagini_totale=0, pagina_curenta=1)

            cursor.execute("""
            SELECT i.id AS id_categorie_intentie, i.tag, p.id AS id_intrebare, p.intrebare, r.id AS id_raspuns, r.raspuns
            FROM categorii_intentii i
            LEFT JOIN set_intrebari p ON i.id = p.id_categorie_intentie
            LEFT JOIN set_raspunsuri r ON i.id = r.id_categorie_intentie
            WHERE i.id IN (%s)
            ORDER BY i.id, p.id, r.id
            """ % ','.join(['%s'] * len(id_categorii_intentii)), tuple(id_categorii_intentii))
            date_db = cursor.fetchall()

        categorii_intentii = {}
        for rand_rezultat in date_db:
            id_categorie_intentie = rand_rezultat['id_categorie_intentie']
            if id_categorie_intentie not in categorii_intentii:
                categorii_intentii[id_categorie_intentie] = {
                    'id': id_categorie_intentie,
                    'tag': rand_rezultat['tag'],
                    'set_intrebari': [],
                    'set_raspunsuri': []
                }

            if {'id': rand_rezultat['id_intrebare'], 'intrebare': rand_rezultat['intrebare']} not in categorii_intentii[id_categorie_intentie]['set_intrebari'] and rand_rezultat['intrebare']:
                categorii_intentii[id_categorie_intentie]['set_intrebari'].append({'id': rand_rezultat['id_intrebare'], 'intrebare': rand_rezultat['intrebare']})

            if {'id': rand_rezultat['id_raspuns'], 'raspuns': rand_rezultat['raspuns']} not in categorii_intentii[id_categorie_intentie]['set_raspunsuri'] and rand_rezultat['raspuns']:
                categorii_intentii[id_categorie_intentie]['set_raspunsuri'].append({'id': rand_rezultat['id_raspuns'], 'raspuns': rand_rezultat['raspuns']})

        return render_template('intents.html', categorii_intentii=list(categorii_intentii.values()), pagini_totale=1, pagina_curenta=1)


    @app.route('/add_intent', methods=['POST'])
    def add_intent():
        tag = request.form['tag']
        patterns = request.form.getlist('seturi_intrebari_formular[]')
        responses = request.form.getlist('set_raspunsuri_formular[]')
        connection = get_database_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO categorii_intentii (tag) VALUES (%s)", (tag,))
                id_categorie_intentie = cursor.lastrowid

                for intrebari in patterns:
                    if intrebari:
                        cursor.execute("INSERT INTO set_intrebari (id_categorie_intentie, intrebare) VALUES (%s, %s)", (id_categorie_intentie, intrebari))

                for response in responses:
                    if response:
                        cursor.execute("INSERT INTO set_raspunsuri (id_categorie_intentie, raspuns) VALUES (%s, %s)", (id_categorie_intentie, response))

                connection.commit()
                declanseaza_reantrenare()

        except Exception as e:
            connection.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500

        finally:
            connection.close()

        return jsonify({'id': id_categorie_intentie, 'tag': tag, 'patterns': patterns, 'responses': responses})


    @app.route('/update_intent', methods=['POST'])
    def update_intent():
        id_categorie_intentie = request.form['intent_id']
        tag = request.form['tag']
        id_intrebare_formular = request.form.getlist('id_intrebare_formular[]')
        seturi_intrebari_formular = request.form.getlist('seturi_intrebari_formular[]')
        id_raspunsuri_formular = request.form.getlist('id_raspunsuri_formular[]')
        set_raspunsuri_formular = request.form.getlist('set_raspunsuri_formular[]')
        conn = get_database_connection()
        try:
            with conn.cursor() as cursor:
                if tag:
                    cursor.execute("UPDATE categorii_intentii SET tag=%s WHERE id=%s", (tag, id_categorie_intentie))

                id_existente_intrebari = set()
                if id_intrebare_formular:
                    cursor.execute("SELECT id FROM set_intrebari WHERE id_categorie_intentie=%s", (id_categorie_intentie,))
                    id_existente_intrebari = {rand_rezultat['id'] for rand_rezultat in cursor.fetchall()}

                for id_intrebare, intrebari in zip_longest(id_intrebare_formular, seturi_intrebari_formular, fillvalue=None):
                    if id_intrebare and id_intrebare in id_existente_intrebari:
                        cursor.execute("UPDATE set_intrebari SET intrebare=%s WHERE id=%s AND id_categorie_intentie=%s", (intrebari, id_intrebare, id_categorie_intentie))
                    elif intrebari:
                        cursor.execute("INSERT INTO set_intrebari (id_categorie_intentie, intrebare) VALUES (%s, %s)", (id_categorie_intentie, intrebari))

                for id_intrebare in id_existente_intrebari:
                    if id_intrebare not in id_intrebare_formular:
                        cursor.execute("DELETE FROM set_intrebari WHERE id=%s", (id_intrebare,))

                existing_response_ids = set()
                if id_raspunsuri_formular:
                    cursor.execute("SELECT id FROM set_raspunsuri WHERE id_categorie_intentie=%s", (id_categorie_intentie,))
                    existing_response_ids = {rand_rezultat['id'] for rand_rezultat in cursor.fetchall()}

                for id_raspuns, raspuns in zip_longest(id_raspunsuri_formular, set_raspunsuri_formular, fillvalue=None):
                    if id_raspuns and id_raspuns in existing_response_ids:
                        cursor.execute("UPDATE set_raspunsuri SET raspuns=%s WHERE id=%s AND id_categorie_intentie=%s", (raspuns, id_raspuns, id_categorie_intentie))
                    elif raspuns:
                        cursor.execute("INSERT INTO set_raspunsuri (id_categorie_intentie, raspuns) VALUES (%s, %s)", (id_categorie_intentie, raspuns))

                for id_raspuns in existing_response_ids:
                    if id_raspuns not in id_raspunsuri_formular:
                        cursor.execute("DELETE FROM set_raspunsuri WHERE id=%s", (id_raspuns,))

                conn.commit()
                declanseaza_reantrenare()
            return jsonify({'status': 'success'})

        except Exception as e:
            conn.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500
        finally:
            conn.close()


    @app.route('/delete_intent/<int:id>', methods=['POST'])
    def delete_intent(id):
        connection = get_database_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM set_intrebari WHERE id_categorie_intentie=%s", (id,))
                cursor.execute("DELETE FROM set_raspunsuri WHERE id_categorie_intentie=%s", (id,))
                cursor.execute("DELETE FROM categorii_intentii WHERE id=%s", (id,))
                connection.commit()
                print(f"intentie stearsa cu ID: {id}")
        finally:
            connection.close()
        return redirect(url_for('index'))


    @app.route('/administrare_date_operator', methods=['GET'])
    @app.route('/administrare_date_operator/<int:pagina>', methods=['GET'])
    def index_operator(pagina=1):
        if not session.get('status_login_utilizator') or session.get('rol_administrativ') != 'operator':
            return redirect(url_for('autentificare_admin'))

        intrebari_per_pagina = request.args.get('length', 10, type=int)
        deplasare = (pagina - 1) * intrebari_per_pagina

        conn = get_database_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT DISTINCT i.id AS id_categorie_intentie
            FROM categorii_intentii i
            ORDER BY i.id
            LIMIT %s OFFSET %s
            """, (intrebari_per_pagina, deplasare))
            categorii_intentii_per_pagina = cursor.fetchall()
            id_categorii_intentii = [rand_rezultat['id_categorie_intentie'] for rand_rezultat in categorii_intentii_per_pagina]
            print(categorii_intentii_per_pagina)
            if not id_categorii_intentii:
                return render_template('intents.html', categorii_intentii=[], pagini_totale=0, pagina_curenta=pagina)

            cursor.execute("""
            SELECT i.id AS id_categorie_intentie, i.tag, p.id AS id_intrebare, p.intrebare, r.id AS id_raspuns, r.raspuns
            FROM categorii_intentii i
            LEFT JOIN set_intrebari p ON i.id = p.id_categorie_intentie
            LEFT JOIN set_raspunsuri r ON i.id = r.id_categorie_intentie
            WHERE i.id IN (%s)
            ORDER BY i.id, p.id, r.id
            """ % ','.join(['%s'] * len(id_categorii_intentii)), tuple(id_categorii_intentii))
            date_db = cursor.fetchall()
            print(date_db)
            cursor.execute("SELECT COUNT(*) FROM categorii_intentii")
            total_categorii_intentii = cursor.fetchone()['COUNT(*)']

        categorii_intentii = {}
        for rand_rezultat in date_db:
            id_categorie_intentie = rand_rezultat['id_categorie_intentie']
            if id_categorie_intentie not in categorii_intentii:
                categorii_intentii[id_categorie_intentie] = {
                    'id': id_categorie_intentie,
                    'tag': rand_rezultat['tag'],
                    'set_intrebari': [],
                    'set_raspunsuri': []
                }

            if {'id': rand_rezultat['id_intrebare'], 'intrebare': rand_rezultat['intrebare']} not in categorii_intentii[id_categorie_intentie]['set_intrebari'] and rand_rezultat['intrebare']:
                categorii_intentii[id_categorie_intentie]['set_intrebari'].append({'id': rand_rezultat['id_intrebare'], 'intrebare': rand_rezultat['intrebare']})

            if {'id': rand_rezultat['id_raspuns'], 'raspuns': rand_rezultat['raspuns']} not in categorii_intentii[id_categorie_intentie]['set_raspunsuri'] and rand_rezultat['raspuns']:
                categorii_intentii[id_categorie_intentie]['set_raspunsuri'].append({'id': rand_rezultat['id_raspuns'], 'raspuns': rand_rezultat['raspuns']})

        pagini_totale = (total_categorii_intentii + intrebari_per_pagina - 1) // intrebari_per_pagina

        return render_template('intents_operator.html', categorii_intentii=list(categorii_intentii.values()), pagini_totale=pagini_totale, pagina_curenta=pagina)


    @app.teardown_appcontext
    def close_database_connection(exception):
        close_conn(exception)
