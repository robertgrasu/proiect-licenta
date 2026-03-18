        // Se initializeaza socket-ul pentru comunicare cu serverul
        var socket = io('/admin');
        var id_curent_sesiune = null;
        var mesaje_sesiuni_chat = {};

        socket.on('connect', function () {
            console.log('test ... Conectat la camera de admin');
        });
        // Eveniment declansat cand o sesiune este activata si va crea un div de chat cu sesiunea respectiva
        socket.on('session_activated', function (data) {
            var id_sesiune_chat = data.id_sesiune_utilizatori;
            var nume_scurtat = generate_friendly_name(id_sesiune_chat);
            nume_sesiune_chat_prescurtata[id_sesiune_chat] = nume_scurtat;
            if (!document.getElementById(id_sesiune_chat)) {
                creare_div_sesiune(id_sesiune_chat, nume_scurtat);
            }
            if (!mesaje_sesiuni_chat[id_sesiune_chat]) {
                mesaje_sesiuni_chat[id_sesiune_chat] = { messages: [], active: false };
            }
        });
        // Functie pentru preluarea unei sesiuni de chat active
        function preluare_sesiune() {
            if (id_curent_sesiune && mesaje_sesiuni_chat[id_curent_sesiune] && !mesaje_sesiuni_chat[id_curent_sesiune].active) {
                mesaje_sesiuni_chat[id_curent_sesiune].active = true;
                document.getElementById('message').disabled = false;
                document.querySelector('.input-group-append button').disabled = false;
                trimite_mesaj_la_user('Acum vorbesti cu un operator. Cu ce te putem ajuta?');
                document.getElementById('session-title').textContent = 'ID Sesiune: ' + id_curent_sesiune.substring(0, 8);
                document.querySelector('.btn-success').style.display = 'none';
                document.querySelector('.btn-danger').style.display = 'inline-block';

            }
        }
        // Eveniment pentru trimiterea unui mesaj cand se apasa enter
        document.getElementById('message').addEventListener('keypress', function (event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                trimite_mesaj_la_user();
                event.preventDefault();
            }
        });
        // Functie ce creeaza div-ul individualizat pentru fiecare sesiune de chat
        function creare_div_sesiune(id_sesiune_chat) {
            var div_sesiune = document.createElement('div');
            div_sesiune.id = id_sesiune_chat;
            div_sesiune.classList.add('card-sesiune');
            var nume_scurtat = id_sesiune_chat.substring(0, 8);
            div_sesiune.innerHTML = `<strong>ID Sesiune:</strong> ${nume_scurtat}<br><span id='last-msg-${id_sesiune_chat}'></span>`;
            div_sesiune.onclick = function () {
                if (id_curent_sesiune !== id_sesiune_chat) {
                    id_curent_sesiune = id_sesiune_chat;
                    document.getElementById('messages').innerHTML = '';
                    document.getElementById('session-title').textContent = 'Sesiune chat cu ID: ' + nume_scurtat;
                    document.querySelectorAll('.card-sesiune').forEach(div => div.classList.remove('sesiune-activa'));
                    this.classList.add('sesiune-activa');
                    var session = mesaje_sesiuni_chat[id_sesiune_chat];
                    document.getElementById('message').disabled = !session.active;
                    document.querySelector('.input-group-append button').disabled = !session.active;
                    session.messages.forEach(msg => afiseaza_mesaj(msg.text, msg.sender));

                    // Se gestioneaza vizibilitatea butoanelor Preluare si Inchidere
                    if (session.active) {
                        document.querySelector('.btn-success').style.display = 'none';
                        document.querySelector('.btn-danger').style.display = 'inline-block';
                    } else {
                        document.querySelector('.btn-success').style.display = 'inline-block';
                        document.querySelector('.btn-danger').style.display = 'none';
                    }
                }
            };
            document.getElementById('sessions').appendChild(div_sesiune);
            actualizare_div_sidebar(id_sesiune_chat);
        }
        // functie pentru actualizarea div-ului lateral al sesiunii de chat
        function actualizare_div_sidebar(id_sesiune_chat) {
            var lastMsgElement = document.getElementById(`last-msg-${id_sesiune_chat}`);
            if (lastMsgElement && mesaje_sesiuni_chat[id_sesiune_chat] && mesaje_sesiuni_chat[id_sesiune_chat].messages.length > 0) {
                var lastMsg = mesaje_sesiuni_chat[id_sesiune_chat].messages[mesaje_sesiuni_chat[id_sesiune_chat].messages.length - 1];
                lastMsgElement.innerHTML = `<strong>Mesaj user:</strong> ${lastMsg.text} <small>${lastMsg.timestamp}</small>`;
            }
        }
        // eveniment declansat cand o sesiune este inchisa, si va sterge chat-ul respectiv
        socket.on('session_closed', function (data) {
            alert(data.message);
            if (id_curent_sesiune) {
                document.getElementById('messages').innerHTML = '';
                document.getElementById('message').disabled = true;
                document.querySelector('.input-group-append button').disabled = true;
                var div_sesiune = document.getElementById(id_curent_sesiune);
                if (div_sesiune) {
                    div_sesiune.remove();
                }
                id_curent_sesiune = null;
            }
        });

        // Eveniment declansat la primirea unui mesaj de la utilizator, atunci cand se afiseaza in chat mesajele acestuia
        socket.on('mesaj_de_la_utilizator', function (data) {
            var session = mesaje_sesiuni_chat[data.id_sesiune_utilizatori] || (mesaje_sesiuni_chat[data.id_sesiune_utilizatori] = { messages: [], active: false });
            session.messages.push({ sender: 'user', text: data.data, timestamp: new Date().toLocaleTimeString() });
            if (!document.getElementById(data.id_sesiune_utilizatori)) {
                creare_div_sesiune(data.id_sesiune_utilizatori);
            } else {
                actualizare_div_sidebar(data.id_sesiune_utilizatori);
            }
            if (id_curent_sesiune === data.id_sesiune_utilizatori) {
                afiseaza_mesaj(data.data, 'user');
            }
        });
        // Eveniment declansat la deconectarea unui user ce va avea ca rezultat actualizarea cu statusul deconectat si ora in sidebar adica bara laterala
        socket.on('user_disconnected', function (data) {
            var div_sesiune = document.getElementById(data.id_sesiune_utilizatori);
            if (div_sesiune) {
                // console.log(`Utilizatorul ${data.id_sesiune_utilizatori} sa deconectat.`);
                var lastMsgElement = document.getElementById(`last-msg-${data.id_sesiune_utilizatori}`);
                if (lastMsgElement) {
                    lastMsgElement.innerHTML += `<br><em>(deconectat la ${new Date().toLocaleTimeString()})</em>`;
                }
                div_sesiune.classList.add('sesiune-inactiva');

                if (id_curent_sesiune === data.id_sesiune_utilizatori) {
                    document.getElementById('message').disabled = true;
                    document.querySelector('.input-group-append button').disabled = true;
                }
            }
        });
        // functie pentru inchiderea sesiunii de chat
        function inchidere_sesiune() {
            if (id_curent_sesiune && mesaje_sesiuni_chat[id_curent_sesiune] && mesaje_sesiuni_chat[id_curent_sesiune].active) {
                socket.emit('close_session', { id_sesiune_utilizatori: id_curent_sesiune });
                mesaje_sesiuni_chat[id_curent_sesiune].active = false;
                document.getElementById('message').disabled = true;
                document.querySelector('.input-group-append button').disabled = true;
                afiseaza_mesaj('Acest chat a fost inchis de către operator. O zi bună!', 'admin');
                var div_sesiune = document.getElementById(id_curent_sesiune);
                if (div_sesiune) {
                    div_sesiune.remove();
                }
                id_curent_sesiune = null;
                document.querySelector('.btn-success').style.display = 'inline-block';
                document.querySelector('.btn-danger').style.display = 'none';
            }
        }
        // Functie pentru trimiterea unui mesaj catre utilizator
        function trimite_mesaj_la_user(mesaj_custom) {
            var message = document.getElementById('message').value || mesaj_custom;
            if (message.trim()) {
                socket.emit('mesaj_de_la_admin', { id_sesiune_utilizatori: id_curent_sesiune, message: message });
                afiseaza_mesaj(message, 'admin');
                document.getElementById('message').value = '';
                if (!mesaje_sesiuni_chat[id_curent_sesiune].messages) {
                    mesaje_sesiuni_chat[id_curent_sesiune].messages = [];
                }
                mesaje_sesiuni_chat[id_curent_sesiune].messages.push({ text: message, sender: 'admin' });
            }
        }


        // Eveniment declansat la incarcarea initiala a paginii ce are ca efect neaparitia butoanelor de preluare/inchidere chat atunci cand nu este nicio solicitare de chat in asteptare
        document.addEventListener('DOMContentLoaded', function () {
            document.querySelector('.btn-success').style.display = 'none';
            document.querySelector('.btn-danger').style.display = 'none';
        });

        // Functie pentru afisarea mesajelor in fereastra de chat
        function afiseaza_mesaj(message, sender) {
            var wrapper_mesaj = document.createElement('div');
            wrapper_mesaj.classList.add('message');

            var textDiv = document.createElement('div');
            textDiv.classList.add('continut-mesaj');
            textDiv.textContent = message;

            var timp_span = document.createElement('span');
            timp_span.classList.add('timp-msg');
            timp_span.textContent = new Date().toLocaleTimeString();

            if (sender === 'admin') {
                wrapper_mesaj.classList.add('admin');
                textDiv.classList.add('admin');
                timp_span.classList.add('admin');
            } else {
                wrapper_mesaj.classList.add('user');
                var div_iconita = document.createElement('div');
                div_iconita.classList.add('icon-msg');
                wrapper_mesaj.appendChild(div_iconita);
            }

            textDiv.appendChild(timp_span);
            wrapper_mesaj.appendChild(textDiv);
            document.getElementById('messages').appendChild(wrapper_mesaj);
            document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
        }

