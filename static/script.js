function appendMessage(sender, message) {
    var messageClass = sender === 'You' ? 'user-message' : 'bot-message';
    $('#conversation').append('<p class="' + messageClass + '">' + sender + ': ' + message + '</p>');
    $('#conversation').scrollTop($('#conversation')[0].scrollHeight); // Auto-scroll to the bottom
}

function playSong(previewUrl) {
    const player = document.getElementById('player');
    player.src = previewUrl;
    player.play();
}

$('#send_button').click(function() {
    var user_input = $('#user_input').val();
    appendMessage('You', user_input);

    // Send user input to server via AJAX
    $.ajax({
        url: '/chat',
        type: 'POST',
        data: { user_input: user_input },
        success: function(response) {
            appendMessage('Chatbot', response.response);

            // Check if the response includes music recommendations
            if (response.recommendation_text && response.preview_urls && response.song_info) {
                appendMessage('Chatbot', response.recommendation_text);

                // Create clickable buttons or links for each song recommendation
                const recommendationContainer = $('<div class="recommendation-container"></div>');
                for (let i = 0; i < response.preview_urls.length; i++) {
                    const previewUrl = response.preview_urls[i];
                    const songInfo = response.song_info[i];
                    const recommendationButton = $('<button class="recommendation-button"><i class="fas fa-play"></i><div class="song-info"><span class="song-title">' + songInfo.title + '</span><span class="artist-name">' + songInfo.artist + '</span></div></button>');
                    recommendationButton.click(function() {
                        playSong(previewUrl);
                    });
                    recommendationContainer.append(recommendationButton);
                }
                $('#conversation').append(recommendationContainer);
            }
        },
        error: function(error) {
            console.error('Error:', error);
        }
    });

    // Clear user input field
    $('#user_input').val('');
});

$('#user_input').keypress(function(e) {
    if (e.which === 13) { // Enter key
        $('#send_button').click();
    }
});