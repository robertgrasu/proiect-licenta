var chatAdminActive = false;

// Functie care actualizeaza pozitia de scroll a containerului astfel incat sa se afiseze cel mai recent mesaj din chat
// function update_scroll() {
//   var chat_container = $("#chat-messages-area");
//   chat_container.animate({ scrollTop: chat_container.prop("scrollHeight") }, 1000);
// }
function update_scroll() {
    setTimeout(function () {
        var chat_container = $("#chat-messages-area");
        chat_container.scrollTop(chat_container.prop("scrollHeight"));
    }, 50);
}
//Functie care identifica adresele URL dintr-un text si le transforma in link-uri clicabile
function transformare_link(text) {
    //Se utilizeaza un regex pentru indentificarea URL-urilor
    var regex_url = /((?<!href=['"])((?:https?:\/\/|www\.)[^\s]+))(?![^<]*>)/g;
    return text.replace(regex_url, function (url) {
        var url_http = url;
        if (!url.match('^https?:\/\/')) {
            url_http = 'http://' + url;
        }
        return '<a href="' + url_http + '" target="_blank">' + url + '</a>';
    });
}

//Functie pentru indepartarea focus-ului de la butonul de send dupa ce a fost trimis un mesaj
$("#send").on("click", function () {
    $(this).blur();
});

//Functie care afiseaza o animatie care indica faptul ca botul scrie un raspuns pentru utilizator
function animatie_tastare() {
    var typingHtml = '<div class="d-flex justify-content-start mb-4"><div class="img_cont_msg"><img src="/static/uploads/user_img.png" class="rounded-circle user_img_msg" id="chatbot-user-img"></div><div class="bot_message_container"><span class="animatie_typing"><span class="dot"></span><span class="dot"></span><span class="dot"></span></span><span class="msg_time"></span></div></div>';
    $("#chat-messages-area").append(typingHtml);
    update_scroll();
}

//Functie care inlatura animatia care indica faptul ca botul scrie un raspuns pentru utilizator
function eliminare_animatie_tastare() {
    $("#chat-messages-area .animatie_typing").closest('.d-flex').remove();
}

function mesaj_bun_venit() {
    if ($('.chat').data('arata_mesaj_bun_venit')) {
        return;
    }

    animatie_tastare();

    setTimeout(() => {
        fetch('/get_setting?name=mesaj_bun_venit')
            .then(response => response.json())
            .then(data => {
                eliminare_animatie_tastare();

                const date = new Date();
                const hour = ("0" + date.getHours()).slice(-2);
                const minute = ("0" + date.getMinutes()).slice(-2);
                const str_time = hour + ":" + minute;

                let welcomeMessage = data.success ? data.value : "Bună ziua! Cu ce te pot ajuta astăzi?";

                var mesaj_intampinare = `<div class="d-flex justify-content-start mb-4"><div class="img_cont_msg"><img src="/static/uploads/user_img.png" class="rounded-circle user_img_msg" id="chatbot-user-img"></div><div class="bot_message_container">${welcomeMessage}<span class="msg_time">${str_time}</span></div></div>`;
                $("#chat-messages-area").append($.parseHTML(mesaj_intampinare));
                update_scroll();

                setTimeout(() => {
                    animatie_tastare();
                    setTimeout(() => {
                        eliminare_animatie_tastare();
                        afiseaza_categorii();
                    }, 500);
                }, 500);
            });

        $('.chat').data('arata_mesaj_bun_venit', true);
    }, 500);
}



// Event handler pentru cand pagina este incarcata si gestioneaza evenimente precum
// afisarea sau ascunderea chat-ului cand este apasat butonul
$(document).ready(function () {

    $("#chat-open-button").click(function () {
        $(".chat").show();
        $(this).hide();
        $("body").addClass("chat-open");
        // se afiseaza mesaj de bun venit cand este deschis chat-ul
        mesaj_bun_venit();
    });

    $("#buton_minimizare").click(function () {
        $(".chat").hide();
        $("#chat-open-button").show();
        $("body").removeClass("chat-open");
    });

    // Când tasta Enter este apasata in timp ce se scrie in inputul "question" (fara a adauga o linie noua in zona de introducere
    // a textului) atunci se va trimite mesajul utilizatorului
    $("#question").on("keydown", function (e) {
        if (e.keyCode == 13 && !e.shiftKey) {
            e.preventDefault();
            $("#message-input-area").submit();
        }
    });
});


$("#message-input-area").on("submit", function (event) {
    event.preventDefault();
    const date = new Date();
    const hour = ("0" + date.getHours()).slice(-2);
    const minute = ("0" + date.getMinutes()).slice(-2);
    const str_time = hour + ":" + minute;
    var raw_text = $("#question").val();

    if (!raw_text.trim()) {
        return;
    }

    raw_text = $("<div>").text(raw_text).html();

    var mesaj_user = '<div class="d-flex justify-content-end mb-4"><div class="user_message_container">' + raw_text + '<span class="msg_time_send">' + str_time + '</span></div></div>';

    $("#question").val("");
    $("#chat-messages-area").append(mesaj_user);
    update_scroll();

    if (!chatAdminActive) {
        animatie_tastare();
    }

    $.ajax({
        data: {
            question: raw_text,
        },
        type: "POST",
        url: "/chat",

    }).done(function (data) {
        setTimeout(function () {
            eliminare_animatie_tastare();
            var answer = transformare_link(data.answer);
            var mesaj_bot = '<div class="d-flex justify-content-start mb-4"><div class="img_cont_msg"><img src="/static/uploads/user_img.png" class="rounded-circle user_img_msg" id="chatbot-user-img"></div><div class="bot_message_container">' + answer + '<span class="msg_time">' + str_time + '</span></div></div>';
            $("#chat-messages-area").append(mesaj_bot);
            update_scroll();

            if (data.show_admin_option) {
                animatie_tastare();
                setTimeout(function () {
                    eliminare_animatie_tastare();
                    var adminOptionHtml = '<div>Chatbot-ul nu a înțeles întrebarea ta. Dorești să soliciți o sesiune cu un admin?</div>' +
                        '<button class="btn btn-success btn-block m-1" onclick="requestAdminSession()">Da</button>' +
                        '<button class="btn btn-secondary btn-block m-1" onclick="endConversation()">Nu</button>';
                    trimite_mesaj_chatbot(adminOptionHtml);
                }, 800);
            }
        }, 800);
    });
});

function requestAdminSession() {
    trimite_mesaj_user("solicitare interventie admin");
    animatie_tastare();
    $.ajax({
        data: { question: "solicitare interventie admin" },
        type: "POST",
        url: "/chat"
    }).done(function (data) {
        eliminare_animatie_tastare();
        trimite_mesaj_chatbot(transformare_link(data.answer));
    });
}
const text_area = document.getElementById('question');
text_area.addEventListener('input', auto_expand);

//Functie care redimensioneaza automat inaltimea campului de text in functie de continutul mesajului pe care il scrie user-ul curent
function auto_expand() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
}
var socket = io('/');
socket.on('admin_chat_active', function (data) {
    chatAdminActive = true;

    eliminare_animatie_tastare();  // Oprirea animației de tastare imediat ce chat-ul de admin este activat
    removeAwaitingAdminMessage();  // Remove the cancellation message when admin starts the chat

    console.log("Chat-ul de admin este activ pentru sesiunea: ", data.id_sesiune_utilizatori);
});
function removeAwaitingAdminMessage() {
    var awaitingMessage = $("#awaiting-admin-message").closest('.d-flex');
    if (awaitingMessage.length) {
        awaitingMessage.remove();
    }
}


socket.on('message_from_admin', function (data) {
    removeAwaitingAdminMessage()
    trimite_mesaj_chatbot(data.data);
});



socket.on('session_closed', function (data) {
    trimite_mesaj_chatbot('Aceasta sectiune a fost inchisa de un admin.');
    animatie_tastare();
    setTimeout(function () {
        eliminare_animatie_tastare();
        var followUpHtml = '<div>Te mai putem ajuta cu alte informații?</div>' +
            '<button class="btn btn-success btn-block m-1" onclick="handleYesResponse()">Da</button>' +
            '<button class="btn btn-secondary btn-block m-1" onclick="endConversation()">Nu</button>';
        trimite_mesaj_chatbot(followUpHtml);
    }, 1700);
});


$("#message-input-area").on("submit", function (event) {
    event.preventDefault();
    var message = $("#question").val().trim();
    if (!message) {
        return;
    }
    afiseaza_mesaj(message, 'user');
    $("#question").val('');

    $.ajax({
        type: "POST",
        url: "/chat",
        data: { question: message },
        success: function (data) {
            afiseaza_mesaj(data.answer, 'chatbot');
        }
    });
});

function afiseaza_mesaj(message, sender) {
    var alignClass = sender === 'admin' ? 'start' : 'end';
    var messageHtml = '<div class="d-flex justify-content-' + alignClass + ' mb-4">' +
        '<div class="' + sender + '_message_container">' + message +
        '<span class="msg_time">' + new Date().toLocaleTimeString() + '</span></div></div>';
    $("#chat-messages-area").append(messageHtml);
}



function trimite_mesaj_chatbot(message) {
    var time = new Date().toLocaleTimeString();
    var messageHtml = `<div class="d-flex justify-content-start mb-4 chatbot-message">
<div class="img_cont_msg">
    <img src="/static/uploads/user_img.png" class="rounded-circle user_img_msg" id="chatbot-user-img"></div>
<div class="bot_message_container">${message}<span class="msg_time">${time}</span></div></div>`;
    $("#chat-messages-area").append(messageHtml);
    update_scroll();
}

function trimite_mesaj_user(message) {
    var time = new Date().toLocaleTimeString();
    var userMessageHtml = '<div class="d-flex justify-content-end mb-4">' +
        '<div class="user_message_container">' + message +
        '<span class="msg_time_send">' + time + '</span></div></div>';
    $("#chat-messages-area").append(userMessageHtml);
    update_scroll();
}
function fetchCategoriesAndQuestions() {
    $.ajax({
        url: '/get_categorii_optiuni',
        type: 'GET',
        success: function (data) {
            categories = data;
            // afiseaza_categorii();
        },
        error: function (error) {
            console.error("Eroare la preluarea categoriilor: ", error);
        }
    });
}


function afiseaza_categorii() {
    var categoriesHtml = '<div>Cu ce te pot ajuta? Poți alege unul din subiectele de mai jos, daca întrebarea ta are legătura cu una din aceste categorii sau adresează-mi o nouă întrebare.</div>';
    categories.forEach(function (category) {
        categoriesHtml += '<button class="btn btn-primary m-1 category-btn" onclick="selectCategory(\'' + category.name + '\')">' + category.name + '</button>';
    });

    trimite_mesaj_chatbot(categoriesHtml);
}

function selectCategory(categoryName) {
    $(".chatbot-message").last().remove();
    trimite_mesaj_user(categoryName);
    var category = categories.find(cat => cat.name === categoryName);
    var questionsHtml = 'Alege una dintre opțiuni:';
    category.questions.forEach(function (question) {
        questionsHtml += '<button class="btn btn-primary m-1 question-btn" onclick="selectPredefinedQuestion(\'' + question + '\')">' + question + '</button>';
    });
    animatie_tastare();
    setTimeout(() => {
        eliminare_animatie_tastare();
        trimite_mesaj_chatbot(questionsHtml);
    }, 500);
}

function selectPredefinedQuestion(question) {
    $(".chatbot-message").last().remove();
    trimite_mesaj_user(question);
    animatie_tastare();

    $.ajax({
        data: { question: question },
        type: "POST",
        url: "/chat"
    }).done(function (data) {
        setTimeout(() => {
            eliminare_animatie_tastare();
            trimite_mesaj_chatbot(transformare_link(data.answer));

            if (question.toLowerCase() === 'solicitare interventie admin' && data.answer.includes('Așteptați un admin')) {
                animatie_tastare();
                setTimeout(function () {
                    eliminare_animatie_tastare();

                    var awaitingAdminHtml = '<div id="awaiting-admin-message">Doriți să anulați solicitarea de chat?.<br>' +
                        '<button class="btn btn-secondary btn-block m-1" onclick="cancelAdminRequest()">Anulează solicitarea</button></div>';
                    trimite_mesaj_chatbot(awaitingAdminHtml);

                }, 60000);
            } else if (!chatAdminActive) {
                setTimeout(function () {
                    animatie_tastare();
                    setTimeout(function () {
                        eliminare_animatie_tastare();
                        var followUpHtml = '<div>Te mai putem ajuta cu alte informații?</div>' +
                            '<button class="btn btn-success btn-block m-1" onclick="handleYesResponse()">Da</button>' +
                            '<button class="btn btn-secondary btn-block m-1" onclick="endConversation()">Nu</button>';
                        trimite_mesaj_chatbot(followUpHtml);
                    }, 500);
                }, 1000);
            }
        }, 500);
    });
}

function cancelAdminRequest() {
    trimite_mesaj_user("anulare interventie admin");
    animatie_tastare();
    $.ajax({
        data: { question: "anulare interventie admin" },
        type: "POST",
        url: "/chat"
    }).done(function (data) {
        removeAwaitingAdminMessage();

        setTimeout(function () {
            eliminare_animatie_tastare();
            trimite_mesaj_chatbot(transformare_link(data.answer));
            chatAdminActive = false;

            animatie_tastare();
            setTimeout(function () {
                eliminare_animatie_tastare();
                afiseaza_categorii();
            }, 1700);
        }, 500);
    });
}

function handleYesResponse() {
    trimite_mesaj_user("Da");
    $(".chatbot-message").last().remove();
    animatie_tastare();
    setTimeout(function () {
        eliminare_animatie_tastare();
        afiseaza_categorii();
    }, 500);
}

// function endConversation() {
//     $(".btn-success, .btn-secondary").remove(); 
//     trimite_mesaj_user('Nu');
//     trimite_mesaj_chatbot('Mulțumim că ai utilizat chatbotul nostru. O zi bună!');
// }
function endConversation() {
    $(".btn-success, .btn-secondary").remove();
    fetch('/get_setting?name=final_message')
        .then(response => response.json())
        .then(data => {
            let goodbyeMessage = data.success ? data.value : "Mulțumim că ai utilizat chatbotul nostru. O zi bună!";
            trimite_mesaj_user('Nu');
            trimite_mesaj_chatbot(goodbyeMessage);
        });
    $(".chatbot-message").last().remove();
}

$(document).ready(function () {

    $('#chatbot-user-img').attr('src', function () {
        return $(this).attr('src');
    });
    fetchCategoriesAndQuestions();
});

