import React, { useEffect, useState } from "react";
import "./SpotifyLogin.css";
import { useNavigate } from "react-router-dom";

const CLIENT_ID = "2a39eea7c8cb440e8096bbc4ecdade9d";
const REDIRECT_URI = "http://127.0.0.1:5173/callback";
const SCOPES = ["user-read-private", "user-read-email","user-top-read"].join(" ");

// Helpers
function base64UrlEncode(arrayBuffer) {
  const bytes = new Uint8Array(arrayBuffer);
  let str = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    str += String.fromCharCode(bytes[i]);
  }
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function sha256(plain) {
  const encoder = new TextEncoder();
  const data = encoder.encode(plain);
  return await window.crypto.subtle.digest("SHA-256", data);
}

function generateRandomString(length = 128) {
  const array = new Uint8Array(length);
  window.crypto.getRandomValues(array);
  return Array.from(array)
    .map((n) => (n % 36).toString(36))
    .join("");
}

export default function SpotifyLoginPKCE() {
    const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [statusMessage, setStatusMessage] = useState("");

  // Step 1: Login redirect
  const loginWithSpotify = async () => {
    if (!CLIENT_ID) {
      setStatusMessage("Missing Spotify client ID.");
      return;
    }

    const codeVerifier = generateRandomString(64);
    sessionStorage.setItem("spotify_code_verifier", codeVerifier);

    const challengeBuffer = await sha256(codeVerifier);
    const codeChallenge = base64UrlEncode(challengeBuffer);

    const state = generateRandomString(16);
    sessionStorage.setItem("spotify_auth_state", state);

    const params = new URLSearchParams({
      response_type: "code",
      client_id: CLIENT_ID,
      scope: SCOPES,
      redirect_uri: REDIRECT_URI,
      state,
      code_challenge_method: "S256",
      code_challenge: codeChallenge,
    });

    window.location.href = `https://accounts.spotify.com/authorize?${params}`;
  };
const fetchUserProfile = async (token) => {
  try {
    const res = await fetch("https://api.spotify.com/v1/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    setUser(data);
    sessionStorage.setItem("spotify_user", JSON.stringify(data)); // store user
  } catch (err) {
    setStatusMessage(`Failed to fetch profile: ${err.message}`);
  }
};

  // Step 2: Exchange code
  const exchangeCodeForToken = async (code) => {
  setStatusMessage("Exchanging code for token...");
  const codeVerifier = sessionStorage.getItem("spotify_code_verifier");
  if (!codeVerifier) {
    setStatusMessage("Missing code verifier in session.");
    return;
  }

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: REDIRECT_URI,
    client_id: CLIENT_ID,
    code_verifier: codeVerifier,
  });

  try {
    const res = await fetch("https://accounts.spotify.com/api/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });

    if (!res.ok) {
      const txt = await res.text();
      setStatusMessage(`Token exchange failed: ${txt}`);
      return;
    }

    const data = await res.json();
    setAccessToken(data.access_token);
    sessionStorage.setItem("spotify_access_token", data.access_token); // store token
    sessionStorage.removeItem("spotify_code_verifier");

    if (data.refresh_token) {
      sessionStorage.setItem("spotify_refresh_token", data.refresh_token);
    }

    // fetchUserProfile(data.access_token);
    setStatusMessage("");

    await fetchUserProfile(data.access_token);
    navigate("/chat");

  } catch (err) {
    setStatusMessage(`Error: ${err.message}`);
  }
};


  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");
    const error = params.get("error");

    if (error) {
      setStatusMessage(`Authorization error: ${error}`);
      return;
    }

    if (code) {
      const storedState = sessionStorage.getItem("spotify_auth_state");
      if (state !== storedState) {
        setStatusMessage("State mismatch. Possible CSRF attack.");
        return;
      }
      window.history.replaceState({}, document.title, window.location.origin + window.location.pathname);
      exchangeCodeForToken(code);
    }
  }, []);

   return (
    <div className="page">
      <div className="card">
        <h2>Login with Spotify</h2>

        {!accessToken ? (
          <>
            <p className="subtitle">
              Sign in to your Spotify account to continue.
            </p>
            <button onClick={loginWithSpotify} className="spotify-btn">
              <img
                src="https://upload.wikimedia.org/wikipedia/commons/1/19/Spotify_logo_without_text.svg"
                alt="Spotify"
              />
              Continue with Spotify
            </button>
            {statusMessage && (
              <p className="status-message">{statusMessage}</p>
            )}
          </>
        ) : (
          <>
            <div className="profile">
              {user?.images?.[0]?.url && (
                <img src={user.images[0].url} alt="avatar" />
              )}
              <div>
                <p className="name">{user?.display_name}</p>
                <p className="email">{user?.email}</p>
              </div>
            </div>
            <button
              onClick={() => {
                sessionStorage.clear();
                setUser(null);
                setAccessToken(null);
              }}
              className="logout-btn"
            >
              Logout
            </button>
          </>
        )}
      </div>
    </div>
  );
}