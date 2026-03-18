from flask import render_template, request, redirect, url_for, jsonify, session
import os
from database import create_connection


def init_app_routess(app):

    @app.route('/panou_control', methods=['GET', 'POST'])
    def control_panel():
        if not session.get('status_login_utilizator') or session.get('rol_administrativ') != 'admin':
            return redirect(url_for('autentificare_admin'))

        connection = create_connection()
        cursor = connection.cursor()

        if request.method == 'POST':
            data = request.get_json()
            action = data.get('action')

            try:
                if action == 'actualizare_setari':
                    cursor.execute("UPDATE setari_chatbot SET value = %s WHERE name = %s", (data['mesaj_bun_venit'], 'mesaj_bun_venit'))
                    cursor.execute("UPDATE setari_chatbot SET value = %s WHERE name = %s", (data['mesaj_final'], 'mesaj_final'))
                    cursor.execute("UPDATE setari_chatbot SET value = %s WHERE name = %s", (data['nume_chatbot'], 'nume_chatbot'))
                    cursor.execute("UPDATE setari_chatbot SET value = %s WHERE name = %s", (data['descriere_chatbot'], 'descriere_chatbot'))

                elif action == 'act_adaugare_categorie':
                    nume_categorie = data['nume_categorie']
                    intrebari_categorii = data.get('intrebari_categorii', [])
                    cursor.execute("INSERT INTO categorii_optiuni (name) VALUES (%s)", (nume_categorie,))
                    id_categorie = cursor.lastrowid
                    for continut_intrebare in intrebari_categorii:
                        if continut_intrebare:
                            cursor.execute("INSERT INTO intrebari_categorii (content, id_categorie) VALUES (%s, %s)", (continut_intrebare, id_categorie))
                    connection.commit()
                    return jsonify(success=True)

                elif action == 'act_actualizare_categorie':
                    if 'nume_categorie' not in data or 'id_categorie' not in data:
                        return jsonify(success=False, message="Missing category name or category ID.")
                    cursor.execute("UPDATE categorii_optiuni SET name = %s WHERE id = %s", (data['nume_categorie'], data['id_categorie']))

                elif action == 'act_stergere_categorie':
                    cursor.execute("DELETE FROM intrebari_categorii WHERE id_categorie = %s", (data['id_categorie'],))
                    cursor.execute("DELETE FROM categorii_optiuni WHERE id = %s", (data['id_categorie'],))
                    connection.commit()
                    return jsonify(success=True)

                elif action == 'act_salvare_modificari_categorii':
                    id_categorie = data['id_categorie']
                    nume_categorie = data['nume_categorie']
                    intrebari_categorii = data['intrebari_categorii']

                    try:
                        cursor.execute("UPDATE categorii_optiuni SET name = %s WHERE id = %s", (nume_categorie, id_categorie))

                        for question in intrebari_categorii:
                            cursor.execute("UPDATE intrebari_categorii SET content = %s WHERE id = %s", (question['continut_intrebare'], question['question_id']))

                        connection.commit()
                        return jsonify(success=True)
                    except Exception as e:
                        connection.rollback()
                        return jsonify(success=False, message=str(e))

                elif action == 'act_adaugare_intrebare':
                    cursor.execute("INSERT INTO intrebari_categorii (content, id_categorie) VALUES (%s, %s)", (data['continut_intrebare'], data['id_categorie']))

                elif action == 'act_actualizare_intrebare':
                    cursor.execute("UPDATE intrebari_categorii SET content = %s WHERE id = %s", (data['continut_intrebare'], data['question_id']))

                elif action == 'act_stergere_intrebare':
                    cursor.execute("DELETE FROM intrebari_categorii WHERE id = %s", (data['question_id'],))

                connection.commit()
                return jsonify(success=True)
            except KeyError as e:
                return jsonify(success=False, message=f"Missing key: {e}")

        cursor.execute("SELECT name, value FROM setari_chatbot")
        setari_chatbot = dict(cursor.fetchall())

        cursor.execute("SELECT id, name FROM categorii_optiuni")
        categorii_optiuni = [{'id': id, 'name': name} for id, name in cursor.fetchall()]

        cursor.execute("SELECT id, content, id_categorie FROM intrebari_categorii")
        intrebari_categorii = [{'id': id, 'content': content, 'id_categorie': id_categorie} for id, content, id_categorie in cursor.fetchall()]

        cursor.close()
        connection.close()

        return render_template('control_panel.html', setari_chatbot=setari_chatbot, categorii_optiuni=categorii_optiuni, intrebari_categorii=intrebari_categorii)


    @app.route('/upload_image', methods=['POST'])
    def upload_image():
        if 'image' in request.files:
            file = request.files['image']
            filename = 'user_img.png'
            path = os.path.join(app.static_folder, 'uploads', filename)
            file.save(path)
            return jsonify(success=True, message="Imagine uploadata cu succes!")
        return jsonify(success=False, message="Eroare! Nicio imagine uploadata!")


    @app.route('/get_categories')
    def get_categories():
        connection = create_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("SELECT id, name FROM categorii_optiuni ORDER BY id")
            categories = cursor.fetchall()
            categories_list = []

            for cat in categories:
                id_categorie, category_name = cat
                cursor.execute("SELECT content FROM intrebari_categorii WHERE id_categorie = %s ORDER BY id", (id_categorie,))
                questions = [question[0] for question in cursor.fetchall()]

                categories_list.append({"name": category_name, "questions": questions})

            return jsonify(categories_list)
        except Exception as e:
            print("A apărut o eroare:", e)
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()
            connection.close()


    @app.route('/get_setting')
    def get_setting():
        setting_name = request.args.get('name')
        connection = create_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("SELECT value FROM setari_chatbot WHERE name = %s", (setting_name,))
            result = cursor.fetchone()
            if result:
                return jsonify(success=True, value=result[0])
            return jsonify(success=False, message="Setting not found.")
        except Exception as e:
            return jsonify(success=False, message=str(e))
        finally:
            cursor.close()
            connection.close()
