import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
import json
import re
# from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import requests
import uvicorn
from model import reply_from_bot, extract_preferences, decide_parameters, get_closest_tracks, fetch_songs_from_search
from pydantic import BaseModel
from typing import List
# Request body model
class ExtractedData(BaseModel):
    mood: str | None = None
    genre: str | None = None
    tempo: str | None = None

class PlaylistResponse(BaseModel):
    playlist_from_params: List[dict]       # closest tracks
    playlist_from_search: List[dict] 
    
          # tracks from search
class AddPlaylistRequest(BaseModel):
    token: str
    playlistSongs: list  # Each item should have 'uri' field for Spotify track
    playlistName: str

app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory extraction state { user_id: {field: {...}, ...} }
user_state = {}

@app.post("/bot")
async def chat_with_bot(data: dict, background_tasks: BackgroundTasks):
    user_id = data.get("user_id")
    latest_message = data.get("latest_user_message", "")
    chat_history = data.get("chat_messages", [])

    # Ensure user state exists
    if user_id not in user_state:
        user_state[user_id] = {"context": [], "mood": [], "genre": []}

    # Bot reply (aware of missing fields)
    bot_reply = reply_from_bot(chat_history, latest_message, user_state[user_id])

    # Extractor runs in background
    def run_extractor():
        extracted = extract_preferences(latest_message, bot_reply)
        print("#" * 20, extracted, "#" * 20)

        for item in extracted:
            field = item["field"]
            value = item["value"]
            reason = item.get("reason")

            if value and (not user_state[user_id][field] or user_state[user_id][field][-1]["value"] != value):
                user_state[user_id][field].append({"value": value, "reason": reason})

        # print(f"🔎 Current state for {user_id}: {user_state[user_id]}")

    background_tasks.add_task(run_extractor)

    # Completion check
    state = user_state.get(user_id, {})

    # ensure every field has a non-null latest value
    is_complete = all(
        state.get(f) 
        and state[f][-1].get("value") not in [None, "", "null"]
        for f in ["context", "mood", "genre"]
    )
    # print(is_complete,"$$$$$$$$$$$$",state)
    if is_complete:
        # ✅ trigger playlist generation here
        # playlist = await generate_playlist(state)

        return {
            "reply": None,
            "status": "done",
            "extracted": state
        }

    # If not complete, just keep chatting
    # print(state)
    return {"reply": bot_reply, "status": "chatting"}



# ✅ Fetch top artists directly from Spotify API
def fetch_top_artists(token: str):  # <-- normal function
    # import requests

    url = "https://api.spotify.com/v1/me/top/artists?limit=10"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)

    if resp.status_code != 200:
        print("⚠️ Error fetching top artists:", resp.text)
        return []

    data = resp.json()
    return [artist["id"] for artist in data.get("items", [])]

@app.post("/generate-playlist", response_model=PlaylistResponse)
async def generate_playlist(data: dict):
    token = data.get("token")
    # user_id = data.get("user_id")
    # print(user_id, token)
    if not token:
        raise HTTPException(status_code=400, detail="Missing Spotify token")
    # if not user_id or user_id not in user_state:
    #     raise HTTPException(status_code=400, detail="Missing or invalid user_id")

    # Step 1: Decide target features from chat history and extracted state
    state = data.get("preferences")
    preferences = {
        "user_context": state.get("context", [])[-1]["value"] if state.get("context") else None,
        "user_mood": state.get("mood", [])[-1]["value"] if state.get("mood") else None,
        "user_genre": state.get("genre", [])[-1]["value"] if state.get("genre") else None,
    }

    target_features = decide_parameters(preferences)
    print("TARGET FEATURES:", target_features)

    loop = asyncio.get_event_loop()

    # Step 2: Fetch user's favorite artists from Spotify API
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get("https://api.spotify.com/v1/me/top/artists?limit=20", headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch top artists")
    user_artists = [artist["name"] for artist in resp.json().get("items", [])]

    # Step 3: Fetch closest tracks and search-based tracks concurrently
    chat_history = [msg["message"] for msg in state.get("chat_messages", [])]  # optional: adjust if format differs
    task1 = loop.run_in_executor(None, get_closest_tracks, target_features, token, 10)
    task2 = loop.run_in_executor(None, fetch_songs_from_search, user_artists, chat_history, token, preferences.get("user_genre"), 10)

    closest_tracks, search_tracks = await asyncio.gather(task1, task2)
    print("CLOSEST TRACKS:", closest_tracks)
    print("SEARCH TRACKS:", search_tracks)

    return PlaylistResponse(
        playlist_from_params=closest_tracks,
        playlist_from_search=search_tracks
    )

@app.post("/add-playlist")
def add_playlist(data: AddPlaylistRequest):
    
    headers = {"Authorization": f"Bearer {data.token}", "Content-Type": "application/json"}

    # 1. Get current user profile
    user_resp = requests.get("https://api.spotify.com/v1/me", headers=headers)
    if user_resp.status_code != 200:
        return {"success": False, "error": "Failed to get user profile"}
    
    user_id = user_resp.json()["id"]
    print(user_resp.status_code, user_resp.text)

    # 2. Create a new playlist
    payload = {"name": data.playlistName, "public": False}
    playlist_resp = requests.post(f"https://api.spotify.com/v1/users/{user_id}/playlists",
                                  headers=headers, json=payload)
    print("helllo",playlist_resp)
    if playlist_resp.status_code != 201:
        return {"success": False, "error": "Failed to create playlist"}
    playlist_id = playlist_resp.json()["id"]
    # print("hiiiiiiiiiiiiii",playlist_resp.status_code)

    # 3. Add tracks to the playlist
    track_uris = [song.get("uri") for song in data.playlistSongs if song.get("uri")]
    # print(track_uris,"@@@@@@@@@@@@@@@@@@@@@@@@@@")
    if track_uris:
        add_resp = requests.post(
            f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
            headers=headers,
            json={"uris": track_uris},
        )
        if add_resp.status_code not in [201, 200]:
            return {"success": False, "error": "Failed to add tracks"}

    return {"success": True, "playlist_id": playlist_id}


def main(): # Start uvicorn programmatically 
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True) 
if __name__ == "__main__": 
    main()