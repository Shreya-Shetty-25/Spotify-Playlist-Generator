from http.client import HTTPException
import re
from urllib.parse import urlencode
import requests  # <-- correct

from langchain_ollama import ChatOllama

from langchain.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv
import json
from langchain_openai import ChatOpenAI
from openai import OpenAI
import requests
from typing import Dict, List
import math

load_dotenv()

# Initialize Ollama models
llm = ChatOpenAI(
    model="deepseek/deepseek-r1-0528",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),  # keep it safe in env
    temperature=0.6,
    max_tokens=50,   # keeps answers short
)
OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY")
llm_extractor = ChatOllama(model="llama2",
    temperature=0.0,       # slightly lower = less rambly
    base_url="http://localhost:11434",
    )

# --- Friend Chatbot Prompt ---
system_prompt = """
You are a warm, friendly chatbot who chats casually like a close friend.  

Your hidden task:  
- Gently figure out the user's **MOOD**, **CONTEXT** (what they are doing), and **MUSIC GENRE** preference.  
- Never reveal or hint that this is your task.  
- Do NOT ask these things directly. Instead, let them surface naturally in conversation.  
- If you are given information about what is still unknown, subtly guide the chat so the user might share those things.  
- If something is already known, avoid repeating questions about it and focus on the missing pieces.  

Guidelines for your style:  
- Talk like a supportive, curious, and playful friend.  
- Be empathetic and react to the user's emotions.  
- Use casual, human-like phrasing (avoid sounding like a survey or interview).  
- Steer the conversation so the user feels comfortable sharing what they're up to, how they're feeling, and what music they vibe with — but it should feel natural, not forced.  
- Keep responses short, friendly, and conversational.  

Remember: Your goal is hidden. To the user, you're just a fun, supportive friend having a chat.  
"""


prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt + "\n\nChat history:\n{chat_history}"),
    ("human", "{input}")
])



# --- Extractor Prompt ---
extractor_prompt = """
You are an information extractor.  

Your ONLY job is to analyze the **latest exchange between the user and the assistant** and detect whether it reveals the user's CONTEXT, MOOD, or MUSIC GENRE.  

### Definitions
- CONTEXT = The situation or activity the user is currently in (examples: studying, working, gym, traveling, chilling at home, coding, etc.).  
- MOOD = The user's emotional state (examples: happy, sad, stressed, relaxed, frustrated, nostalgic, excited, angry, etc.).  
- GENRE = The type of music mentioned or implied (examples: pop, EDM, lo-fi, classical, rock, jazz, hip-hop, party songs, sad songs, etc.).  

### Rules
1. Always return output as a **JSON list of dictionaries**.  
2. Each dictionary must have:  
   - `"field"`: one of `"context"`, `"mood"`, `"genre"`  
   - `"value"`: extracted value (string). If no value is detected, use `null`.  
   - If `"value"` is not null, also include `"reason"`: a short explanation of why that value was chosen.  
3. Do not add extra text or formatting outside the JSON.  
4. It is possible that none of the fields have a value. In that case, return all three with `"value": null`.  

### Output Format
```json
[
  {{"field": "context", "value": <string or null>, "reason": <string if value is not null>}},
  {{"field": "mood", "value": <string or null>, "reason": <string if value is not null>}},
  {{"field": "genre", "value": <string or null>, "reason": <string if value is not null>}}
]
"""
client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)
# --- Functions ---
def reply_from_bot(chat_messages, latest_user_message, current_state):
    missing = [f for f in ["context", "mood", "genre"] if not current_state.get(f)]
    steering_note = ""
    if missing:
        steering_note = (
            f"\n\n(Pssst: The user still hasn't revealed their {', '.join(missing)}. "
            "Gently guide the conversation so they might share it naturally.)"
        )

    # Build messages
    messages = [{"role": "system", "content": system_prompt + "\n\nChat history:\n" + str(chat_messages)}]
    messages.append({"role": "user", "content": latest_user_message + steering_note})

    try:
        response = client.chat.completions.create(
            model="gemini-2.5-flash",  # or "gemini-2.5-pro", etc.
            messages=messages,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Error during Gemini API call: {e}"

def extract_preferences(user_message, bot_message):
    api_key="AIzaSyDBwgktq7QAcnN_U_fZUTPSby2gSpixu6U"
    last_exchange = f"User: {user_message}\nBot: {bot_message}"
    full_prompt = extractor_prompt + "\n\n### Latest Exchange\n" + last_exchange

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": full_prompt}
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    try:
        raw = response.json()
        # print("Extractor raw output:", json.dumps(raw, indent=2))
        print(raw)
        # Gemini API puts text in candidates[0].content.parts[0].text
        content = raw["candidates"][0]["content"]["parts"][0]["text"]

        # --- FIX: strip ```json ... ``` wrappers ---
        if content.strip().startswith("```"):
            content = content.strip().strip("`")        # remove backticks
            if content.lower().startswith("json"):
                content = content[4:].strip()           # remove leading 'json'

        data = json.loads(content)

        cleaned = []
        print(data)
        for entry in data:
            field = entry.get("field")
            value = entry.get("value")
            reason = entry.get("reason")

            if field in ["context", "mood", "genre"]:
                cleaned.append({
                    "field": field,
                    "value": value,
                    "reason": reason if value else None
                })
        # print("CLEANED",cleaned)
        return cleaned

    except Exception as e:
        print("Extractor parse error:", e)
        return []

def decide_parameters(data: dict) -> dict:
    system_prompt = """
    You are a specialized AI designed to analyze user music preferences and translate them into Spotify audio feature targets.

Your task is to analyze the user's three inputs:
- user_context: [User's activity or situation, e.g., "studying", "gym", "relaxing"]
- user_mood: [User's emotional state, e.g., "happy", "stressed", "calm"]
- user_genre: [User's preferred music genre, e.g., "pop", "lo-fi", "R&B", "kpop"]

---

### Output Format (IMPORTANT):
Return a **single JSON object only**. Do not include explanations, text, or code fences.  

The JSON must contain these keys (when relevant):
- target_valence
- target_energy
- target_danceability
- target_instrumentalness
- target_tempo

---

### Mapping Instructions:

**Mood → target_valence + target_energy:**  
- Happy, upbeat, cheerful → valence: 0.7-1.0 | energy: 0.6-0.9  
- Sad, melancholic → valence: 0.0-0.3 | energy: 0.2-0.5  
- Calm, relaxed → valence: 0.3-0.6 | energy: 0.1-0.3  
- Stressed, angry → valence: 0.1-0.4 | energy: 0.6-0.8  
- Energetic, pumped → valence: 0.6-0.9 | energy: 0.8-1.0  

**Context → target_danceability, target_instrumentalness, target_tempo:**  
- Gym, party, dancing → danceability: 0.7-1.0 | tempo: 120-160 | instrumentalness: 0.0-0.4  
- Studying, relaxing, working, focus → danceability: 0.1-0.4 | tempo: 60-90 | instrumentalness: 0.8-1.0  
- Sleeping → tempo: 60-75 | instrumentalness: 0.9-1.0 | danceability: 0.0-0.2  

---

### Decision Logic:
- Combine inputs logically. Example: if `context = studying` and `mood = stressed`, then:
  - target_valence = low (~0.3)
  - target_energy = low (~0.2)
  - target_instrumentalness = high (~0.9)
- Choose **single representative float values**, not ranges.
- **Do not include seed_genres or any other Spotify parameters**.
- Only include the features that are relevant; omit the rest.

---

### Final Rule:
Return **only one JSON object**, wrapped in a ```json code block``` like this:

```json
{
  "target_valence": <float (between 0 to 1)>,
  "target_energy": <float (between 0 to 1)>,
  "target_danceability": <float (between 0 to 1)>,
  "target_instrumentalness": <float (between 0 to 1)>,
  "target_tempo": <float (between 0 to 1)>
}
```

"""

    json_input = json.dumps(data, indent=2)

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"""
        System Instructions:
        {system_prompt}

        User Input:
        {json_input}

        Expected Output:
        JSON dictionary only.
        """
                            }
                        ]
                    }
                ]
            }

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": "AIzaSyDBwgktq7QAcnN_U_fZUTPSby2gSpixu6U"
    }

    response = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent", headers=headers, json=payload)
    
    result = response.json()
    text = result["candidates"][0]["content"]["parts"][0]["text"]
    # print(text,"^^^^^^^^")
    # match = re.search(r"\{[\s\S]*\}", text)  # greedy match for JSON block
    match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if match:
        clean_json = match.group(1)
        return json.loads(clean_json)   # Convert to dict
    raise ValueError("No fenced JSON found")



import requests
import math
import math
import requests
from typing import List, Dict

def get_closest_tracks(target_features: Dict[str, float], token: str, limit: int = 10) -> List[Dict]:
    headers = {"Authorization": f"Bearer {token}"}

    def fetch_tracks(url: str, key: str):
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            return []
        items = resp.json().get("items", [])
        if key == "recently_played":
            return [item["track"] for item in items]
        return [item["track"] if "track" in item else item for item in items]

    top_tracks = fetch_tracks("https://api.spotify.com/v1/me/top/tracks?limit=50", "top")
    recent_tracks = fetch_tracks("https://api.spotify.com/v1/me/player/recently-played?limit=50", "recently_played")
    saved_tracks = fetch_tracks("https://api.spotify.com/v1/me/tracks?limit=50", "saved")

    all_tracks = {t["id"]: t for t in (top_tracks + recent_tracks + saved_tracks) if t.get("id")}
    if not all_tracks:
        return []

    track_ids = list(all_tracks.keys())

    # Fetch audio features
    features_url = "https://api.spotify.com/v1/audio-features"
    features = []
    for i in range(0, len(track_ids), 100):
        batch_ids = track_ids[i:i+100]
        resp = requests.get(features_url, headers=headers, params={"ids": ",".join(batch_ids)})
        if resp.status_code != 200:
            continue
        features.extend(resp.json().get("audio_features", []))

    # Cosine similarity function
    def cosine_similarity(f, target):
        keys = ["valence", "energy", "danceability"]
        f_vec = [f.get(k, 0) for k in keys]
        t_vec = [target.get(k, 0) for k in keys]
        dot = sum(fv * tv for fv, tv in zip(f_vec, t_vec))
        mag_f = math.sqrt(sum(fv**2 for fv in f_vec))
        mag_t = math.sqrt(sum(tv**2 for tv in t_vec))
        if mag_f == 0 or mag_t == 0:
            return 0  # treat zero magnitude as 0 similarity
        return dot / (mag_f * mag_t)

    scored_tracks = []
    for f in features:
        if not f or f.get("id") not in all_tracks:
            continue
        sim = cosine_similarity(f, target_features)
        scored_tracks.append((sim, all_tracks[f["id"]]))

    # Sort descending by similarity
    scored_tracks.sort(key=lambda x: x[0], reverse=True)
    closest_tracks = [t[1] for _, t in scored_tracks[:limit]]

    # Fill remaining if fewer than limit
    if len(closest_tracks) < limit:
        remaining_tracks = [t for tid, t in all_tracks.items() if t not in closest_tracks]
        closest_tracks.extend(remaining_tracks[:limit - len(closest_tracks)])

    # Format output
    formatted = []
    for track in closest_tracks:
        formatted.append({
            "name": track["name"],
            "artist": ", ".join([artist["name"] for artist in track["artists"]]),
            "album": track["album"]["name"],
            "preview_url": track.get("preview_url"),
            "spotify_url": track["external_urls"]["spotify"],
            "image": track["album"]["images"][0]["url"] if track["album"]["images"] else None
        })

    return formatted



def fetch_songs_from_search(user_artists: list, chat_history: list, token: str, user_genre: str = None, limit: int = 10) -> list:
    # Step 1: Generate 5 search terms via LLM
    system_prompt = """
You are a music AI assistant. Generate exactly 5 unique Spotify search terms
matching the user's current vibe, mood, and preferences.

Constraints:
- Include user genre if provided.
- Return exactly 5 distinct search terms.
- Return lowercase only.
- Return JSON dictionary inside ```json{...} with keys term1..term5.
"""
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"""
System Instructions:
{system_prompt}

User Data:
Favorite Artists: {json.dumps(user_artists)}
Chat History: {json.dumps(chat_history)}
Preferred Genre: {user_genre or "None"}

Expected Output:
Return JSON dictionary only with 5 search terms.
"""
                    }
                ]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": "AIzaSyDBwgktq7QAcnN_U_fZUTPSby2gSpixu6U"  # Replace with your key
    }

    llm_resp = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
        headers=headers,
        json=payload
    )

    llm_result = llm_resp.json()
    raw_text = llm_result["candidates"][0]["content"]["parts"][0]["text"]
    match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", raw_text)
    if not match:
        raise ValueError("No JSON block found in LLM output.")
    search_terms = json.loads(match.group(1))
    for key in search_terms:
        search_terms[key] = search_terms[key].lower()

    # Step 2: Call Spotify Search API for each term until we have `limit` songs
    headers_spotify = {"Authorization": f"Bearer {token}"}
    songs = []
    for key in search_terms:

        term = search_terms[key]
        print(term,end=" ooooooooooooooo ")
        search_url = "https://api.spotify.com/v1/search"
        params = {
            "q": term,
            "type": "track",
            "limit": min(limit, 3)  # max 10 per query
        }
        resp = requests.get(search_url, headers=headers_spotify, params=params)
        if resp.status_code != 200:
            continue
        data = resp.json()
        for track in data.get("tracks", {}).get("items", []):
            songs.append({
                "name": track["name"],
                "artist": ", ".join([artist["name"] for artist in track["artists"]]),
                "album": track["album"]["name"],
                "preview_url": track.get("preview_url"),
                "spotify_url": track["external_urls"]["spotify"],
                "image": track["album"]["images"][0]["url"] if track["album"]["images"] else None
            })
        if len(songs) >= limit:
            break

    return songs[:limit]  # return exactly `limit` songs


# def generate_spotify_playlist(params: dict, token: str) -> dict:
#     base_url = "https://api.spotify.com/v1/recommendations"
    
#     # Build query string (ignore empty params)
#     filtered_params = {k: v for k, v in params.items() if v not in (None, "", [])}
#     query_string = urlencode(filtered_params)
#     url = f"{base_url}?{query_string}"
#     print("ELLLO",url)
#     # Call Spotify API
#     headers = {"Authorization": f"Bearer {token}"}
#     response = requests.get(url, headers=headers)
#     print("📡 Request URL:", url, token)
#     print("📡 Status Code:", response.status_code)
#     print("📡 Raw Response:", response.text[:500])  # only first 500 chars
#     print("GENERATE SPOTIFY",response.json())
#     if response.status_code != 200:
#         return {"error": response.json()}
    
#     data = response.json()
    
#     # Clean response
#     playlist = []
#     for track in data.get("tracks", []):
#         playlist.append({
#             "name": track["name"],
#             "artist": ", ".join([artist["name"] for artist in track["artists"]]),
#             "album": track["album"]["name"],
#             "preview_url": track.get("preview_url"),
#             "spotify_url": track["external_urls"]["spotify"],
#             "image": track["album"]["images"][0]["url"] if track["album"]["images"] else None
#         })
    
#     return {"playlist": playlist}

# def analyze_user_music_features(token: str) -> dict:
#     """
#     Fetch top tracks, recently played, and liked songs from Spotify,
#     calculate mean values of valence, tempo, instrumentalness, danceability,
#     and then fetch recommended songs based on those mean values.
    
#     Args:
#         token (str): Spotify access token (Bearer token).
    
#     Returns:
#         dict: Contains mean feature values and a recommended playlist.
#     """
#     headers = {"Authorization": f"Bearer {token}"}

#     # 1. Get top listened songs (20)
#     top_url = "https://api.spotify.com/v1/me/top/tracks?limit=20"
#     top_tracks = requests.get(top_url, headers=headers).json().get("items", [])

#     # 2. Get recently played (10)
#     recent_url = "https://api.spotify.com/v1/me/player/recently-played?limit=10"
#     recent_tracks = requests.get(recent_url, headers=headers).json().get("items", [])
#     recent_tracks = [item["track"] for item in recent_tracks]

#     # 3. Get liked (saved) songs (30)
#     liked_url = "https://api.spotify.com/v1/me/tracks?limit=30"
#     liked_tracks = requests.get(liked_url, headers=headers).json().get("items", [])
#     liked_tracks = [item["track"] for item in liked_tracks]

#     # Collect track IDs
#     track_ids = [track["id"] for track in top_tracks + recent_tracks + liked_tracks if track.get("id")]

#     if not track_ids:
#         return {"error": "No tracks found."}

#     # 4. Fetch audio features
#     features_url = "https://api.spotify.com/v1/audio-features"
#     features = []
#     for i in range(0, len(track_ids), 100):
#         batch_ids = track_ids[i:i+100]
#         resp = requests.get(features_url, headers=headers, params={"ids": ",".join(batch_ids)})
#         features.extend(resp.json().get("audio_features", []))

#     # 5. Compute mean values
#     metrics = ["valence", "tempo", "instrumentalness", "danceability"]
#     sums = {m: 0 for m in metrics}
#     count = 0

#     for f in features:
#         if f:
#             for m in metrics:
#                 sums[m] += f.get(m, 0)
#             count += 1

#     if count == 0:
#         return {"error": "No audio features available."}

#     mean_features = {m: round(sums[m] / count, 4) for m in metrics}

#     # 6. Fetch recommendations based on mean values
#     rec_url = "https://api.spotify.com/v1/recommendations"
#     # Use top 2 tracks + 2 artists as seeds (fallback if no seeds available)
#     seed_tracks = ",".join([t["id"] for t in top_tracks[:2] if t.get("id")])
#     seed_artists = ",".join([a["id"] for t in top_tracks[:2] for a in t["artists"][:1]])

#     params = {
#         "limit": 20,
#         "seed_tracks": seed_tracks or track_ids[0],
#         "seed_artists": seed_artists or "",
#         "target_valence": mean_features["valence"],
#         "target_tempo": mean_features["tempo"],
#         "target_instrumentalness": mean_features["instrumentalness"],
#         "target_danceability": mean_features["danceability"]
#     }

#     rec_resp = requests.get(rec_url, headers=headers, params=params)
#     if rec_resp.status_code != 200:
#         return {"mean_features": mean_features, "error": rec_resp.json()}

#     rec_data = rec_resp.json()
#     print("USERS", rec_data)

#     # 7. Format recommendations for frontend
#     playlist = []
#     for track in rec_data.get("tracks", []):
#         playlist.append({
#             "name": track["name"],
#             "artist": ", ".join([artist["name"] for artist in track["artists"]]),
#             "album": track["album"]["name"],
#             "preview_url": track.get("preview_url"),
#             "spotify_url": track["external_urls"]["spotify"],
#             "image": track["album"]["images"][0]["url"] if track["album"]["images"] else None
#         })

#     return {
#         "track_count_analyzed": count,
#         "mean_features": mean_features,
#         "recommended_playlist": playlist
#     }

# def generate_playlist_from_top_artists(top_artists: list, target_features: dict, token: str, limit: int = 20) -> dict:
    
#     if not top_artists or len(top_artists) == 0:
#         return {"error": "No top artists provided."}

#     # Limit to 5 artists for Spotify API
#     seed_artists = ",".join(top_artists[:5])
    
#     # Build query params
#     params = {"seed_artists": seed_artists, "limit": limit}
    
#     # Include only valid non-empty target features
#     for key in ["target_valence", "target_tempo", 
#                 "target_instrumentalness", "target_energy", "target_danceability"]:
#         if key in target_features and target_features[key] not in (None, "", []):
#             params[key] = target_features[key]

#     # Build URL
#     base_url = "https://api.spotify.com/v1/recommendations"
#     query_string = urlencode(params)
#     url = f"{base_url}?{query_string}"

#     # Call Spotify API
#     headers = {"Authorization": f"Bearer {token}"}
#     response = requests.get(url, headers=headers)

#     if response.status_code != 200:
#         return {"error": response.json()}

#     data = response.json()
#     print("COMBO",data)

#     # Clean and format tracks for frontend
#     playlist = []
#     for track in data.get("tracks", []):
#         playlist.append({
#             "name": track["name"],
#             "artist": ", ".join([artist["name"] for artist in track["artists"]]),
#             "album": track["album"]["name"],
#             "preview_url": track.get("preview_url"),
#             "spotify_url": track["external_urls"]["spotify"],
#             "image": track["album"]["images"][0]["url"] if track["album"]["images"] else None
#         })

#     return {"playlist": playlist}