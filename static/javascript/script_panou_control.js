                    
                    function actualizare_previzualizare_chat(nume_categorie, questions) {
                        $('#chat-messages-area').empty();
                        displayMessage(`Categorie nouă adăugată: ${nume_categorie}`, 'bot');
                        questions.forEach(question => {
                            displayMessage(`Întrebare: ${question}`, 'bot');
                        });
                    }


                    function adaugare_alta_intrebare() {
                        const questionNumber = $('#container-adaugare-intrebari > div').length + 1;
                        $('#container-adaugare-intrebari').append(`
                        <div class="mb-3" id="grup-intrebari${questionNumber}">
                        <label for="question${questionNumber}" class="form-label">Question:</label>
                        <input type="text" class="form-control" id="question${questionNumber}" required>
                        <button type="button" class="btn btn-danger" onclick="stergere_intrebare('grup-intrebari${questionNumber}')">Remove</button>
                        </div>
                    `);
                    }

                    function stergere_intrebare(id) {
                        $(`#${id}`).remove();
                    }

                    function adaugare_categorie_noua() {
                        const nume_categorie = $('#category-name').val();
                        const intrebari_categorii = [];
                        $('#container-adaugare-intrebari input[type="text"]').each(function () {
                            if ($(this).val()) {
                                intrebari_categorii.push($(this).val());
                            }
                        });

                        const data = {
                            action: 'act_adaugare_categorie',
                            nume_categorie: nume_categorie,
                            intrebari_categorii: intrebari_categorii
                        };

                        $.ajax({
                            type: 'POST',
                            url: '/panou_control',
                            contentType: 'application/json',
                            data: JSON.stringify(data),
                            success: function (response) {
                                if (response.success) {
                                    alert('Categoria de optiuni impreuna cu intrebarile au fost adaugate cu succes!');
                                    $('#modal-adaugare-categorii').modal('hide');
                                    window.location.reload();
                                } else {
                                    alert('Failed to add category: ' + response.message);
                                }
                            },
                            error: function (xhr, status, error) {
                                alert('Error: ' + error.message);
                            }
                        });
                    }

                    function afisare_info_chatbot() {
                        fetch('/get_setting?name=nume_chatbot')
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    $('.info-chatbot span').text(data.value);
                                }
                            });

                        fetch('/get_setting?name=descriere_chatbot')
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    $('.info-chatbot p').text(data.value);
                                }
                            });
                    }


                    function actualizare_setari() {
                        var data = {
                            action: 'actualizare_setari',
                            mesaj_bun_venit: $('#mesaj-bun-venit').val(),
                            mesaj_final: $('#mesaj-final').val(),
                            nume_chatbot: $('#nume-chatbot').val(),
                            descriere_chatbot: $('#descriere_chatbot').val()
                        };
                        postAjax(data);
                    }


                    function adaugare_categorii() {
                        var nume_categorie = prompt("Introdu numele noi categorii:");
                        if (nume_categorie) {
                            var data = { action: 'act_adaugare_categorie', nume_categorie: nume_categorie };
                            postAjax(data);
                        }
                    }


                    function trimite_mesaj_user(message) {
                        var time = new Date().toLocaleTimeString();
                        var html_mesaj_user = '<div class="d-flex justify-content-end mb-4">' +
                            '<div class="user_message_container">' + message +
                            '<span class="msg_time_send">' + time + '</span></div></div>';
                        $("#chat-messages-area").append(html_mesaj_user);
                        actualizare_scroll();
                    }

                    function salvare_modificari_categorii(id_categorie) {
                        var nume_categorie = $(`#collapse${id_categorie} .category-input`).val();
                        var questionsData = [];

                        $(`#collapse${id_categorie} .input-group`).each(function () {
                            var questionId = $(this).data('question-id');
                            var continut_intrebare = $(this).find('.question-input').val();
                            questionsData.push({ question_id: questionId, continut_intrebare: continut_intrebare });
                        });

                        var data = {
                            action: 'act_salvare_modificari_categorii',
                            id_categorie: id_categorie,
                            nume_categorie: nume_categorie,
                            intrebari_categorii: questionsData
                        };

                        $.ajax({
                            type: 'POST',
                            url: '/panou_control',
                            contentType: 'application/json',
                            data: JSON.stringify(data),
                            success: function (response) {
                                if (response.success) {

                                    $(`#heading${id_categorie} .accordion-button`).text(nume_categorie);
                                    alert('Categoria si intrebarile au fost actualizate cu succes!');
                                    window.location.reload();


                                } else {
                                    alert('Nu sau salvat modificarile: ' + response.message);
                                }
                            },
                            error: function (xhr, status, error) {
                                alert('Error: ' + error.message);
                            }
                        });
                    }
                    function actualizare_previzualizare_chat(nume_categorie, questions) {
                        $('#chat-messages-area').empty();
                        trimite_mesaj_chatbot(`Categorie: ${nume_categorie}`);
                        questions.forEach(question => {
                            trimite_mesaj_chatbot(`Question: ${question}`);
                        });
                    }

                    function actualizare_categorie(id_categorie) {
                        var nume_categorie = $(`#heading${id_categorie}`).next('.accordion-collapse').find('.category-input').val();
                        var data = { action: 'act_actualizare_categorie', id_categorie: id_categorie, nume_categorie: nume_categorie };
                        postAjax(data);
                        
                    }

                    function stergere_categorie(id_categorie) {
                        if (confirm("Esti sigur ca vrei sa stergi categoria??")) {
                            var data = { action: 'act_stergere_categorie', id_categorie: id_categorie };
                            postAjax(data);
                        }
                    }

                    function adaugare_intrebare(id_categorie) {
                        var continut_intrebare = prompt("Introdu o nouă întrebare:");
                        if (continut_intrebare) {
                            var data = {
                                action: 'act_adaugare_intrebare',
                                id_categorie: id_categorie,
                                continut_intrebare: continut_intrebare
                            };
                            $.ajax({
                                type: 'POST',
                                url: '/panou_control',
                                contentType: 'application/json',
                                data: JSON.stringify(data),
                                success: function (response) {
                                    if (response.success) {
                                        alert('Întrebare adăugată cu succes!');
                                        var newQuestionHTML = `
                                            <div class="input-group mb-3" data-question-id="${response.question_id}">
                                                <input type="text" class="form-control question-input" value="${continut_intrebare}">
                                                <button class="btn btn-outline-danger btn-spacing" onclick="stergere_intrebare_form(${response.question_id})">Șterge</button>
                                            </div>`;
                                        $(`#questions-container-${id_categorie}`).append(newQuestionHTML);
                                        window.location.reload();
                                    } else {
                                        alert('Eșec la adăugarea întrebării: ' + response.message);
                                    }
                                },
                                error: function (xhr, status, error) {
                                    alert('Error: ' + error.message);
                                }
                            });
                        }
                    }
                    

                    function actualizare_intrebare(questionId) {
                        var continut_intrebare = $(`div[data-question-id="${questionId}"]`).find('.question-input').val();
                        var data = { action: 'act_actualizare_intrebare', question_id: questionId, continut_intrebare: continut_intrebare };
                        postAjax(data);
                    }
                    var categories = {};

                    function trimite_mesaj_chatbot(message) {
                        var time = new Date().toLocaleTimeString();
                        var cache_bust = new Date().getTime();
                        var mesaj_html = `<div class="d-flex justify-content-start mb-4 chatbot-message">
        <div class="img_cont_msg">
            <img src="/static/uploads/user_img.png?${cache_bust}" class="rounded-circle user_img_msg"></div>
        <div class="bot_message_container">${message}<span class="msg_time">${time}</span></div></div>`;
                        $("#chat-messages-area").append(mesaj_html);
                        actualizare_scroll();
                    }
                    function uploadare_imagine() {
                        var fileInput = document.getElementById('chatbot-image');
                        var file = fileInput.files[0];
                        var formData = new FormData();
                        formData.append('image', file);

                        $.ajax({
                            url: '/upload_image',
                            type: 'POST',
                            data: formData,
                            processData: false,
                            contentType: false,
                            success: function (response) {
                                if (response.success) {
                                    alert('Image uploaded successfully!');
                                    var cache_bust = new Date().getTime();

                                    $('.user_img, .user_img_msg').each(function () {
                                        $(this).attr('src', '/static/uploads/user_img.png?' + cache_bust);
                                    });
                                } else {
                                    alert('Esec la uploadarea imaginii: ' + response.message);
                                }
                            },
                            error: function (xhr, status, error) {
                                alert('Error: ' + error.message);
                            }
                        });
                    }

                    function selectare_intrebari_predefinite(question) {
                        trimite_mesaj_user(question);
                        var simulatedAnswer = "Acesta este răspunsul la întrebarea ta: '" + question + "'";
                        setTimeout(() => {
                            trimite_mesaj_chatbot(simulatedAnswer);
                            afisare_optiuni_alte_informatii();
                        }, 1000);
                    }

                    function afisare_optiuni_alte_informatii() {
                        var followUpHtml = '<div>Te mai putem ajuta cu alte informații?</div>' +
                            '<button class="btn btn-success btn-block m-1" onclick="handler_raspuns_da()">Da</button>' +
                            '<button class="btn btn-secondary btn-block m-1" onclick="inchide_conversatie()">Nu</button>';
                        trimite_mesaj_chatbot(followUpHtml);
                    }

                    function handler_raspuns_da() {
                        $(".chatbot-message").last().remove();
                        afisare_categorii();
                    }

                    function inchide_conversatie() {
                        fetch('/get_setting?name=mesaj_final')
                            .then(response => response.json())
                            .then(data => {
                                let goodbyeMessage = data.success ? data.value : "Mulțumim că ai utilizat chatbotul nostru. O zi bună!";
                                trimite_mesaj_chatbot(goodbyeMessage);
                            });
                        $(".chatbot-message").last().remove();
                    }

                    // Functia pentru a prelua setările pe baza numelui
                    function preluare_setari(settingName) {
                        return fetch(`/get_setting?name=${settingName}`)
                            .then(response => response.json())
                            .then(data => data.success ? data.value : null);
                    }
                    // Functie pentru afișarea mesajului de întâmpinare
                    function afiseaza_mesaj_bun_venit() {
                        fetch('/get_setting?name=mesaj_bun_venit')
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    trimite_mesaj_chatbot(data.value);
                                } else {
                                    trimite_mesaj_chatbot("Bun venit la Asistentul Virtual!");
                                }
                            });
                    }
                    function stergere_mesaje_chatbot() {
                        $("#chat-messages-area").empty();
                    }
                    // Funcție pentru actualizarea scroll-ului
                    function actualizare_scroll() {
                        var zona_chat_mesaje = $("#chat-messages-area");
                        zona_chat_mesaje.scrollTop(zona_chat_mesaje.prop("scrollHeight"));
                    }
                    function preluare_categorii_optiuni_db() {
                        $.ajax({
                            url: '/get_categories',
                            method: 'GET',
                            success: function (response) {
                                categories = response;
                                afisare_categorii();
                            },
                            error: function () {
                                trimite_mesaj_chatbot("Eroare la încărcarea categoriilor.");
                            }
                        });
                    }


                    // Funcție pentru încărcarea și afișarea categoriilor dinamic
                    function afisare_categorii() {
                        setTimeout(function () {
                            var categoriesHtml = '<div>Cu ce te pot ajuta? Poti alege unul din subiectele de mai jos, daca intrebarea ta are legatura cu una din aceste categorii sau adreseaza-mi o noua intrebare.</div>';
                            categories.forEach(function (category) {
                                categoriesHtml += '<button class="btn btn-primary m-1 category-btn" onclick="selectare_categorie(\'' + category.name + '\')">' + category.name + '</button>';
                            });

                            trimite_mesaj_chatbot(categoriesHtml);
                        }, 1400);
                    }

                    // Funcție apelată când o categorie este selectată
                    function selectare_categorie(nume_categorie) {
                        trimite_mesaj_user(nume_categorie);
                        var category = categories.find(cat => cat.name === nume_categorie);
                        var questionsHtml = 'Alege una dintre opțiuni:';
                        category.questions.forEach(function (question) {
                            questionsHtml += `<button class="btn btn-primary m-1 question-btn" onclick="selectare_intrebari_predefinite('${question}')">${question}</button>`;
                        });
                        trimite_mesaj_chatbot(questionsHtml);
                    }
                    $(document).ready(function () {
                        afisare_info_chatbot();

                        afiseaza_mesaj_bun_venit();
                        preluare_categorii_optiuni_db();

                        $('#meniu-acordeon-categorii').on('click', '.btn-delete-question', function () {
                            var questionId = $(this).data('question-id');
                            stergere_intrebare_form(questionId);
                        });
                    });

                    function stergere_intrebare_form(questionId) {
                        if (confirm("Esti sigur ca vrei sa stergi această intrebare?")) {
                            var data = { action: 'act_stergere_intrebare', question_id: questionId };
                            $.ajax({
                                type: 'POST',
                                url: '/panou_control',
                                contentType: 'application/json',
                                data: JSON.stringify(data),
                                success: function (response) {
                                    if (response.success) {
                                        alert('Intrebare stearsa cu succes!');
                                        $(`div[data-question-id="${questionId}"]`).remove();
                                    } else {
                                        alert('Failed to delete question: ' + response.message);
                                    }
                                },
                                error: function (xhr, status, error) {
                                    alert('Error: ' + error.message);
                                }
                            });
                        }
                    }

                    function actualizare_scroll() {
                        var chat_container = $("#chat-messages-area");
                        chat_container.animate({ scrollTop: chat_container.prop("scrollHeight") }, 1000);
                    }


                    function postAjax(data) {
                        $.ajax({
                            type: 'POST',
                            url: '/panou_control',
                            contentType: 'application/json',
                            data: JSON.stringify(data),
                            success: function (response) {
                                if (response.success) {
                                    alert('Actualizarea datelor s-a facut cu succes!!!');
                                    window.location.reload();
                                } else {
                                    alert('Esuare operatie! Incearca din nou.');
                                }
                            },
                            error: function () {
                                alert('Eroare: Nu sa putut conecta la server.');
                            }
                        });
                    }