import os
import pickle
import random
import re
import unicodedata
from datetime import datetime
import numpy as np
import pymysql
import spacy
import tensorflow as tf
from flask import Flask, jsonify, make_response, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.layers import Bidirectional, Dense, Dropout, Embedding, LSTM
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.preprocessing.sequence import pad_sequences
import uuid
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
from database import close_conn, get_database_connection, db_config
from routes.ruta_administrare_date import init_app_routes
from routes.ruta_panou_control import init_app_routess
from routes.ruta_login import init_app_router
from routes.socket_events import init_socket_events, set_chatbot

app = Flask(__name__)
app.secret_key = ''

init_app_routes(app)
init_app_routess(app)
init_app_router(app)

nlp = spacy.load("ro_core_news_sm")

def elimina_diacritice(input_str):
    format_nfkd = unicodedata.normalize('NFKD', input_str)
    format_ascii = format_nfkd.encode('ASCII', 'ignore')
    return format_ascii.decode('utf-8')

class PreprocesatorDate:

    def __init__(self, intents_file):
        self.intents_file = intents_file
        self.data = self.incarca_date()
        self.cuvinte, self.categorii_intentii, self.date_antrenament = self.preprocesare_date()

    def incarca_date(self):
        connection = pymysql.connect(**db_config)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM categorii_intentii")
                intents_data = cursor.fetchall()
                data = {'categorii_intentii': []}
                for intent in intents_data:
                    intent_id = intent['id']
                    cursor.execute("SELECT intrebare FROM set_intrebari WHERE id_categorie_intentie=%s", (intent_id,))
                    patterns = [item['intrebare'] for item in cursor.fetchall()]
                    cursor.execute("SELECT raspuns FROM set_raspunsuri WHERE id_categorie_intentie=%s", (intent_id,))
                    responses = [item['raspuns'] for item in cursor.fetchall()]
                    data['categorii_intentii'].append({
                        'tag': intent['tag'],
                        'set_intrebari': patterns,
                        'set_raspunsuri': responses
                    })
        finally:
            connection.close()
        return data

    def preprocesare_date(self):
        cuvinte = []
        categorii_intentii = []
        date_antrenament = []
        for intent in self.data['categorii_intentii']:
            for pattern in intent['set_intrebari']:
                doc = nlp(pattern.lower())
                print(doc)
                text_tokenizat = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
                print(text_tokenizat)
                print("")
                cuvinte.extend(text_tokenizat)
                date_antrenament.append((text_tokenizat, intent['tag']))
                if intent['tag'] not in categorii_intentii:
                    categorii_intentii.append(intent['tag'])

        cuvinte = sorted(list(set(cuvinte)))
        categorii_intentii = sorted(list(set(categorii_intentii)))
        pickle.dump(cuvinte, open('cuvinte.pkl', 'wb'))
        pickle.dump(categorii_intentii, open('categorii_intentii.pkl', 'wb'))
        print(date_antrenament)
        return cuvinte, categorii_intentii, date_antrenament


class AntrenareModelChatbot:

    def __init__(self, cuvinte, categorii_intentii, date_antrenament, force_retrain=False):
        self.model_path = 'model_chatbot.h5'
        self.cuvinte_path = 'chat_cuvinte.pkl'
        self.categorii_intentii_path = 'chat_categorii_intentii.pkl'
        self.lungime_maxima_secventa_path = 'chat_lungime_max.pkl'

        if os.path.exists(self.model_path) and not force_retrain:
            print("Incarcare model salvat.")
            self.incarca_model_si_componente()
        else:
            print("Nu a fost detectat un model salvat! Se va antrena un model nou...")
            self.cuvinte = cuvinte
            self.categorii_intentii = categorii_intentii
            self.date_antrenament = date_antrenament
            self.index_cuvinte = {word: i for i, word in enumerate(cuvinte, 1)}
            self.X_train, self.y_train = self.preprocess_date_antrenament()
            self.model = self.antrenare_model()
            self.salvare_model_si_componente()

    def preprocess_date_antrenament(self):
        X = []
        y = []
        lungime_maxima_secventa = 0
        for doc, intent in self.date_antrenament:
            encoded_doc = [self.index_cuvinte[word] for word in doc if word in self.index_cuvinte]
            X.append(encoded_doc)
            output_row = [0] * len(self.categorii_intentii)
            output_row[self.categorii_intentii.index(intent)] = 1
            y.append(output_row)
            lungime_maxima_secventa = max(lungime_maxima_secventa, len(encoded_doc))
        self.lungime_maxima_secventa = lungime_maxima_secventa
        X_padded = pad_sequences(X, maxlen=self.lungime_maxima_secventa, padding='post')
        return np.array(X_padded), np.array(y)

    def antrenare_model(self):
        vocab_size = len(self.cuvinte) + 1
        embedding_dim = 128

        model = Sequential([
            Embedding(input_dim=vocab_size, output_dim=embedding_dim, input_length=self.lungime_maxima_secventa),
            Bidirectional(LSTM(128, return_sequences=True)),
            Dropout(0.5),
            LSTM(64, return_sequences=True),
            Dropout(0.5),
            LSTM(32),
            Dense(64, activation='relu'),
            Dropout(0.5),
            Dense(len(self.categorii_intentii), activation='softmax')
        ])

        model.compile(loss='categorical_crossentropy', optimizer=Adam(learning_rate=0.001), metrics=['accuracy'])
        oprire_anticipata_antrenare = EarlyStopping(monitor='accuracy', patience=61, verbose=1, mode='max', restore_best_weights=True)
        model.fit(self.X_train, self.y_train, epochs=400, batch_size=8, verbose=1, callbacks=[oprire_anticipata_antrenare])
        return model

    def salvare_model_si_componente(self):
        self.model.save(self.model_path)
        pickle.dump(self.cuvinte, open(self.cuvinte_path, 'wb'))
        pickle.dump(self.categorii_intentii, open(self.categorii_intentii_path, 'wb'))
        pickle.dump(self.lungime_maxima_secventa, open(self.lungime_maxima_secventa_path, 'wb'))
        print("Modelul si componentele chatbot-ului au fost salvate cu succes!.")

    def incarca_model_si_componente(self):
        if os.path.exists(self.model_path):
            from tensorflow import keras
            self.model = keras.models.load_model(self.model_path)
            with open(self.cuvinte_path, 'rb') as f:
                self.cuvinte = pickle.load(f)
            with open(self.categorii_intentii_path, 'rb') as f:
                self.categorii_intentii = pickle.load(f)
            with open(self.lungime_maxima_secventa_path, 'rb') as f:
                self.lungime_maxima_secventa = pickle.load(f)
            self.index_cuvinte = {word: i for i, word in enumerate(self.cuvinte, 1)}
            return True
        return False


class Chatbot:
    def __init__(self, model, cuvinte, categorii_intentii, data, lungime_maxima_secventa, index_cuvinte):
        self.model = model
        self.cuvinte = cuvinte
        self.categorii_intentii = categorii_intentii
        self.data = data
        self.lungime_maxima_secventa = lungime_maxima_secventa
        self.index_cuvinte = index_cuvinte

    @staticmethod
    def curata_text(text):
        return re.sub(r'[^\w\s]', '', text)

    @staticmethod
    def distanta_damerau_levenshtein(sir1, sir2):
        lungime_sir1 = len(sir1) + 1
        lungime_sir2 = len(sir2) + 1
        distanta = [[0 for _ in range(lungime_sir2)] for __ in range(lungime_sir1)]
        for i in range(lungime_sir1):
            distanta[i][0] = i
        for j in range(lungime_sir2):
            distanta[0][j] = j
        for i in range(1, lungime_sir1):
            for j in range(1, lungime_sir2):
                cost_substitutie = 0 if sir1[i - 1] == sir2[j - 1] else 1
                distanta[i][j] = min(distanta[i - 1][j] + 1,
                                    distanta[i][j - 1] + 1,
                                    distanta[i - 1][j - 1] + cost_substitutie)
                if i > 1 and j > 1 and sir1[i - 1] == sir2[j - 2] and sir1[i - 2] == sir2[j - 1]:
                    distanta[i][j] = min(distanta[i][j], distanta[i - 2][j - 2] + cost_substitutie)
        return distanta[-1][-1]

    def vectorizare_text(self, propozitie):
        propozitie_procesata = Chatbot.curata_text(propozitie)
        doc = nlp(propozitie_procesata)
        leme = [token.lemma_ for token in doc]
        sequence = []
        for lemma in leme:
            index_cuvinte = self.index_cuvinte.get(lemma, 0)
            if index_cuvinte:
                sequence.append(index_cuvinte)
        return pad_sequences([sequence], maxlen=self.lungime_maxima_secventa, padding='post')

    def clasificare(self, propozitie):
        if not propozitie.strip():
            return [{'intent': 'neintelegere', 'probability': '1.0'}]

        propozitie_procesata = Chatbot.curata_text(propozitie)
        padded_sequence = self.vectorizare_text(propozitie_procesata)
        predictie = self.model.predict(padded_sequence).flatten()
        index_intentie_prezisa = np.argmax(predictie)
        intentie_prezisa = self.categorii_intentii[index_intentie_prezisa]

        scoruri_lexicale = {}
        for intent in self.data['categorii_intentii']:
            for pattern in intent['set_intrebari']:
                distanta = Chatbot.distanta_damerau_levenshtein(propozitie_procesata, Chatbot.curata_text(pattern))
                scor_similaritate = max(0, len(pattern) - distanta) / len(pattern)
                scoruri_lexicale[intent['tag']] = max(scoruri_lexicale.get(intent['tag'], 0), scor_similaritate)

        max_scor_lexical = max(scoruri_lexicale.values(), default=0)
        cea_mai_buna_intentie_lexicala = max(scoruri_lexicale, key=scoruri_lexicale.get, default=None)

        prag_incredere_model = 0.75
        prag_lexical = 0.61

        if predictie[index_intentie_prezisa] > prag_incredere_model and scoruri_lexicale.get(intentie_prezisa, 0) > prag_lexical:
            print(f"Propoziție de intrare: {propozitie}")
            print(f"Scor predicție model: {predictie[index_intentie_prezisa]}")
            print(f"Intenția prezisă: {intentie_prezisa}")
            return [{'intent': intentie_prezisa, 'probability': str(predictie[index_intentie_prezisa])}]
        elif max_scor_lexical > prag_lexical:
            print(f"Propoziție de intrare: {propozitie}")
            print(f"Scor similaritate lexicală: {max_scor_lexical}")
            print(f"Intenția prezisă: {cea_mai_buna_intentie_lexicala}")
            return [{'intent': cea_mai_buna_intentie_lexicala, 'probability': str(max_scor_lexical)}]
        else:
            print(f"Propoziție de intrare: {propozitie}")
            print(f"Nu s-a putut stabili o intenție clară.")
            return [{'intent': 'neintelegere', 'probability': '1.0'}]

    def obtine_raspuns(self, lista_intentii, question):
        if not lista_intentii or lista_intentii[0]['intent'] == 'neintelegere':
            self.salvare_intrebari_neraspunse(question)
            return "Îmi pare rău, nu am înțeles. Poți încerca să spui altfel?"
        tag = lista_intentii[0]['intent']
        for intentie in self.data['categorii_intentii']:
            if intentie['tag'] == tag:
                return random.choice(intentie['set_raspunsuri'])
        self.salvare_intrebari_neraspunse(question)
        return "Nu am găsit un răspuns adecvat."

    def salvare_intrebari_neraspunse(self, question):
        try:
            connection = get_database_connection()
            with connection.cursor() as cursor:
                sql = "INSERT INTO intrebari_fara_raspuns (question, timestamp) VALUES (%s, %s)"
                cursor.execute(sql, (question, datetime.now()))
                connection.commit()
        except Exception as e:
            print(f"Eroare la salvare intrebari neraspunse: {e}")
        finally:
            close_conn(connection)


@app.route('/retrain', methods=['POST'])
def reantrenare_model():
    try:
        preprocessor = PreprocesatorDate(db_config)
        cuvinte, categorii_intentii, date_antrenament = preprocessor.cuvinte, preprocessor.categorii_intentii, preprocessor.date_antrenament
        trainer = AntrenareModelChatbot(cuvinte, categorii_intentii, date_antrenament, force_retrain=True)
        chatbot = Chatbot(trainer.model, cuvinte, categorii_intentii, preprocessor.data, trainer.lungime_maxima_secventa, trainer.index_cuvinte)
        set_chatbot(chatbot)
        return jsonify({'message': 'Model reantrenat cu succes!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/intrebari_fara_raspuns')
def pag_intrebari_fara_raspuns():
    if not session.get('status_login_utilizator') or session.get('rol_administrativ') != 'admin':
        return redirect(url_for('autentificare_admin'))
    return render_template('intrebari_fara_raspuns.html')


@app.route('/get_intrebari_fara_raspuns', methods=['GET'])
def interogare_intrebari_fara_raspuns():
    try:
        connection = get_database_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM intrebari_fara_raspuns ORDER BY timestamp DESC")
            intrebari_fara_raspuns = cursor.fetchall()
        return jsonify(intrebari_fara_raspuns)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        close_conn(connection)


@app.route('/stergere_intrebari_fara_raspuns', methods=['POST'])
def stergere_intrebari_fara_raspuns():
    try:
        ids = request.form.getlist('ids[]')
        connection = get_database_connection()
        with connection.cursor() as cursor:
            sql = "DELETE FROM intrebari_fara_raspuns WHERE id IN (%s)" % ','.join(['%s'] * len(ids))
            cursor.execute(sql, ids)
            connection.commit()
        return jsonify({'message': 'Întrebările au fost șterse cu succes!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        close_conn(connection)


@app.route('/')
def home():
    id_sesiune_utilizatori = request.cookies.get('id_sesiune_utilizatori')
    if not id_sesiune_utilizatori:
        id_sesiune_utilizatori = str(uuid.uuid4())
        response = make_response(render_template('index.html'))
        response.set_cookie('id_sesiune_utilizatori', id_sesiune_utilizatori)
        print(f"Sesiune noua creata: {id_sesiune_utilizatori}")
        return response
    print(f"Sesiune existenta care a fost accesata: {id_sesiune_utilizatori}")
    return render_template('index.html')


socketio = SocketIO(app, cors_allowed_origins="*")
init_socket_events(app, socketio)

print("Inițializare chatbot...")
try:
    preprocessor = PreprocesatorDate(db_config)
    cuvinte, categorii_intentii, date_antrenament = preprocessor.cuvinte, preprocessor.categorii_intentii, preprocessor.date_antrenament
    trainer = AntrenareModelChatbot(cuvinte, categorii_intentii, date_antrenament)
    chatbot = Chatbot(trainer.model, cuvinte, categorii_intentii, preprocessor.data, trainer.lungime_maxima_secventa, trainer.index_cuvinte)
    set_chatbot(chatbot)
    print("Chatbot inițializat cu succes!")
except Exception as e:
    print(f"Eroare la inițializarea chatbot-ului: {e}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)
