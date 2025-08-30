from langchain_ollama import OllamaLLM  # new package after deprecation
from langchain.prompts import ChatPromptTemplate
import requests

llm = OllamaLLM(model="llama2")  # replaces old langchain_community.llms.Ollama

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a playlist manager assistant.
    - If user wants to add songs (keywords: add, include, put, throw in), set intent = "add".
    - If user wants to remove songs (keywords: remove, delete, drop, exclude), set intent = "remove".
    - If user just wants to view playlist (keywords: show, list, display), set intent = "show".
    - Extract the main search term (song, artist, genre, mood, era) as 'term'.
    Respond ONLY in JSON like: {{"intent": "...", "term": "..."}}.
    """),
    ("user", "{user_input}")
])

chain = prompt | llm

def parse_user_input(user_text: str):
    return chain.invoke({"user_input": user_text})

def spotify_search_tracks(query, limit=3):
    url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {SPOTIFY_TOKEN}"}
    params = {"q": query, "type": "track", "limit": limit}

    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()

    track_ids = []
    if "tracks" in data and "items" in data["tracks"]:
        for item in data["tracks"]["items"]:
            track_ids.append(item["id"])
    return track_ids

def handle_intent(parsed):
    intent = parsed["intent"]
    term = parsed["term"]

    if intent == "add":
        track_ids = spotify_search_tracks(term)
        playlist.extend(track_ids)
        return f"✅ Added {len(track_ids)} tracks for '{term}' → {track_ids}"

    else:
        return "🤔 Sorry, I didn't understand that."
     
while True:
    ex=input("enter: - ")
    parsed = parse_user_input(ex)  # {"intent": "...", "term": "..."}
    result = handle_intent(parsed)
    print(ex, "→", result)
