from flask import Flask, request, jsonify, render_template
import openai
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import spotipy
import os
from spotipy.oauth2 import SpotifyClientCredentials
from collections import deque
from itertools import chain
import re


app = Flask(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Set up OpenAI API credentials
openai.api_key = os.getenv("OPENAI_API_KEY")

# Set up Spotify API credentials
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

# Create a Spotify client
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# System message for the conversational model
system_message = "You are a friendly and engaging conversational assistant with a focus on providing personalized music recommendations based on the user's preferences, mood, emotional state, and current context. Your role is to engage in natural conversation with users, accurately understand their requests and preferences, and provide relevant recommendations tailored to their needs. When the user explicitly requests music recommendations or mentions specific genres, styles, or regions, prioritize those preferences in your recommendations. If no explicit preferences are mentioned, consider the overall conversation context and the user's mood to provide appropriate recommendations. Engage in back-and-forth conversation, ask clarifying questions when needed, and gather feedback from the user. Adapt your responses and recommendations based on the user's requests and preferences within the conversation flow."



# Function to generate a response using the GPT-3.5-turbo model
def generate_response(conversation_history):
    messages = [
        {"role": "system", "content": system_message},
        *[{"role": "user" if i % 2 == 0 else "assistant", "content": msg} for i, msg in enumerate(conversation_history)],
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
    )
    assistant_response = response.choices[0].message.content.strip()

    # Check if the assistant should provide music recommendations
    intent, user_preferences = extract_intent_and_preferences(conversation_history)
    if intent == "music_recommendation":
        context, recommendation_text, preview_urls, song_info = recommend_music(conversation_history, user_preferences)
        assistant_response += "\n\n" + context + "\n" + recommendation_text

    return assistant_response


# Function to extract intent and user preferences from conversation
def extract_intent_and_preferences(conversation_history):
    conversation_text = " ".join(conversation_history)
    music_recommendation_pattern = r"(recommend|suggest|play).*music"
    genre_pattern = r"(pop|rock|hip hop|rap|jazz|classical|country|metal|punk|indie|folk|blues|reggae|electronic|dance|techno|alternative|ambient|experimental|instrumental|soundtrack|world|ethiopian|ethio-jazz|traditional ethiopian|tizita|eritrean|k-pop|j-pop|c-pop|asian pop|mandopop|cantopop|bollywood|indian classical|indian folk|punjabi|filmi|nepali folk|nepali pop|bangladeshi folk|bangla rock|afrobeats|highlife|soukous|mbalax|kizomba|bongo flava|samba|bossa nova|latin|salsa|merengue|reggaeton|fado|flamenco|tango|mariachi|gqom|amapiano|kwaito|african house|kuduro|throat singing|mongolian|tuvan|gamelan|dangdut|kroncong|nanyin|soca|chutney|bouyon|kadans|enka|shibuya-kei|city pop|kayokyoku)"

    if re.search(music_recommendation_pattern, conversation_text, re.IGNORECASE):
        intent = "music_recommendation"
    else:
        intent = "general_conversation"

    genre_match = re.search(genre_pattern, conversation_text, re.IGNORECASE)
    if genre_match:
        user_preferences = genre_match.group(1)
    else:
        user_preferences = None

    return intent, user_preferences


# Function to analyze sentiment using VADER
def analyze_sentiment(text):
    analyzer = SentimentIntensityAnalyzer()
    sentiment_scores = analyzer.polarity_scores(text)
    sentiment = sentiment_scores['compound']
    if sentiment >= 0.05:
        return "positive"
    elif sentiment <= -0.05:
        return "negative"
    else:
        return "neutral"

# Function to recommend music based on user's mood and conversation context
def recommend_music(conversation_history, user_preferences=None):
    # Analyze the overall sentiment of the conversation
    sentiment = analyze_sentiment(" ".join(conversation_history))

    # Define the search query based on the mood and context
    if sentiment == "positive":
        mood_query = "mood:happy"
    elif sentiment == "negative":
        mood_query = "mood:sad"
    else:
        mood_query = "mood:neutral"

    # Prioritize user preferences if provided
    if user_preferences:
        query = f"{user_preferences}"
    else:
        # Determine the genre/style/region based on the conversation context
        genre_query = extract_genre_from_conversation(conversation_history)
        query = f"{mood_query} {genre_query}"

    # Search for tracks on Spotify based on the query
    results = sp.search(q=query, type='track', limit=5)

    # Extract the track information from the search results
    tracks = results['tracks']['items']

    # Create a list to store the recommended songs
    recommendations = []
    song_info = []

    # Iterate over the tracks and extract the relevant information
    for idx, track in enumerate(tracks, start=1):
        song_title = track['name']
        artist_name = track['artists'][0]['name']
        preview_url = track['preview_url']
        recommendations.append(f"{idx}. {song_title} by {artist_name}")
        song_info.append({'title': song_title, 'artist': artist_name})

    recommendation_text = "\n".join(recommendations)
    preview_urls = [track['preview_url'] for track in tracks]
    context = f"Based on your current mood '{sentiment}' and the conversation context, here are some song recommendations:"

    return context, recommendation_text, preview_urls, song_info


# Function to determine if music recommendations should be provided
def should_recommend_music(conversation_history, assistant_response):
    # Convert the string to a deque
    assistant_response_deque = deque([assistant_response])

    # Join the conversation history and assistant response
    conversation_text = " ".join(chain(conversation_history, assistant_response_deque))
    music_recommendation_pattern = r"(recommend|suggest|play).*music"

    if re.search(music_recommendation_pattern, conversation_text, re.IGNORECASE):
        return True
    else:
        return False
    

# Function to extract the genre/style/region from the conversation context
def extract_genre_from_conversation(conversation_history):
    conversation_text = " ".join(conversation_history)

    # Define patterns for different genres, styles, and regions
    genre_patterns = [
        r"pop|rock|hip hop|rap|jazz|classical|country|metal|punk|indie|folk|blues|reggae|electronic|dance|techno",
        r"alternative|ambient|experimental|instrumental|soundtrack|world",
        r"ethiopian music|ethio-jazz|traditional ethiopian|tizita|eritrean music",
        r"k-pop|j-pop|c-pop|asian pop|mandopop|cantopop",
        r"bollywood|indian classical|indian folk|punjabi|filmi|nepali folk|nepali pop|bangladeshi folk|bangla rock",
        r"afrobeats|highlife|soukous|mbalax|kizomba|bongo flava",
        r"samba|bossa nova|latin|salsa|merengue|reggaeton",
        r"fado|flamenco|tango|mariachi",
        r"gqom|amapiano|kwaito|african house|kuduro",
        r"throat singing|mongolian|tuvan",
        r"gamelan|dangdut|kroncong|nanyin",
        r"soca|chutney|bouyon|kadans",
        r"enka|shibuya-kei|city pop|kayokyoku",
    ]

    for pattern in genre_patterns:
        if re.search(pattern, conversation_text, re.IGNORECASE):
            return pattern

    return ""

# Route for the home page
@app.route('/')
def home():
    return render_template('index.html')

# Route for handling chat requests
@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form['user_input']
    conversation_history = request.form.getlist('conversation_history[]')

    # Maintain conversation history as a deque (double-ended queue)
    conversation_deque = deque(maxlen=10)
    conversation_deque.extend(conversation_history)
    conversation_deque.append(user_input)

    # Generate response based on user's input and conversation history
    response = generate_response(list(conversation_deque))

    # Initialize recommendation_text and preview_urls
    recommendation_text = ""
    preview_urls = []
    song_info = []

    # Check if the assistant should provide music recommendations
    if should_recommend_music(conversation_deque, response):
        context, recommendation_text, preview_urls, song_info = recommend_music(conversation_deque)
        response += "\n\n" + context + "\n" + recommendation_text

    return jsonify({'response': response, 'recommendation_text': recommendation_text, 'preview_urls': preview_urls, 'song_info': song_info})

if __name__ == "__main__":
    app.run(debug=True)