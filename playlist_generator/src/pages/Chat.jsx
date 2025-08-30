// import { useState, useEffect } from "react";
// import "./ChatInterface.css";

// export default function ChatInterface() {
//   const [messages, setMessages] = useState([
//     { sender: "bot", text: "Hello! How can I help you today? 😊" },
//   ]);
//   const [input, setInput] = useState("");
//   const [loading, setLoading] = useState(false);
//   const [extracted, setExtracted] = useState(null);
//   const [chatDone, setChatDone] = useState(false);
//   const [playlist, setPlaylist] = useState([]);
//   const [token, setToken] = useState(null);
//   const [darkMode, setDarkMode] = useState(true);

//   // Dark/light mode
//   useEffect(() => {
//     document.body.className = darkMode ? "" : "light-mode";
//   }, [darkMode]);

//   const toggleTheme = () => setDarkMode(!darkMode);

//   // Load Spotify token
//   useEffect(() => {
//     const storedToken = sessionStorage.getItem("spotify_access_token");
//     if (storedToken) setToken(storedToken);
//     else window.location.href = "/";
//   }, []);

//   // Send chat message
//   const sendMessage = async () => {
//     if (!input.trim() || loading) return;

//     const userMessage = input;
//     const newMessages = [...messages, { sender: "user", text: userMessage }];
//     setMessages(newMessages);
//     setInput("");
//     setLoading(true);

//     try {
//       const res = await fetch("http://localhost:5000/bot", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({
//           user_id: "user123",
//           chat_messages: newMessages.map((m) => ({
//             role: m.sender === "user" ? "user" : "assistant",
//             content: m.text,
//           })),
//           latest_user_message: userMessage,
//         }),
//       });

//       const data = await res.json();

//       if (data.status === "chatting" && data.reply) {
//         setMessages((prev) => [...prev, { sender: "bot", text: data.reply }]);
//       } else if (data.status === "done") {
//         setExtracted(data.extracted);
//         setChatDone(true);
//         setMessages((prev) => [
//           ...prev,
//           { sender: "bot", text: "🎶 Playlist generation in progress..." },
//         ]);
//       } else {
//         setMessages((prev) => [
//           ...prev,
//           { sender: "bot", text: "⚠ Error fetching reply." },
//         ]);
//       }
//     } catch {
//       setMessages((prev) => [
//         ...prev,
//         { sender: "bot", text: "❌ Failed to connect to bot." },
//       ]);
//     }
//     setLoading(false);
//   };

//   // Generate playlist after chat ends
//   useEffect(() => {
//     const generatePlaylist = async () => {
//       if (!chatDone || !extracted || !token) return;

//       try {
//         const res = await fetch("http://localhost:5000/generate-playlist", {
//           method: "POST",
//           headers: { "Content-Type": "application/json" },
//           body: JSON.stringify({
//             token,
//             preferences: extracted,
//           }),
//         });

//         const data = await res.json();

//         const allSongs = [
//           ...(data.playlist_from_params || []),
//           ...(data.playlist_from_search || []),
//         ];

//         if (allSongs.length) {
//           setPlaylist(allSongs);
//           setMessages((prev) => [
//             ...prev,
//             { sender: "bot", text: "✅ Playlist generated successfully!" },
//           ]);
//         } else {
//           setMessages((prev) => [
//             ...prev,
//             { sender: "bot", text: "⚠ Couldn't generate playlist." },
//           ]);
//         }
//       } catch {
//         setMessages((prev) => [
//           ...prev,
//           { sender: "bot", text: "❌ Playlist API failed." },
//         ]);
//       }
//     };

//     generatePlaylist();
//   }, [chatDone, extracted, token]);

//   // Handle Enter key
//   const handleKeyDown = (e) => {
//     if (e.key === "Enter") {
//       e.preventDefault();
//       sendMessage();
//     }
//   };

//   return (
//     <div className="chat-container">
//       {/* Header */}
//       <div className="chat-header">
//         AI Chatbot
//         <button
//           onClick={toggleTheme}
//           style={{
//             float: "right",
//             padding: "5px 10px",
//             borderRadius: "8px",
//             border: "none",
//             cursor: "pointer",
//           }}
//         >
//           {darkMode ? "🌞 Light" : "🌙 Dark"}
//         </button>
//       </div>

//       {/* Messages */}
//       <div className="chat-messages">
//         {messages.map((msg, idx) => (
//           <div
//             key={idx}
//             className={`message-row ${msg.sender === "user" ? "user-message" : "bot-message"}`}
//           >
//             <div className="message-bubble">{msg.text}</div>
//           </div>
//         ))}

//         {/* Playlist */}
//        {/* Add Playlist Button */}
// {playlist.length > 0 && (
//   <div style={{ marginTop: "10px", textAlign: "center" }}>
//     <button
//       className="add-playlist-button"
//       onClick={async () => {
//         try {
//           const res = await fetch("http://localhost:5000/add-playlist", {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify({
//               token,         // Spotify access token
//               playlistSongs: playlist, // Current playlist tracks
//               playlistName: "My AI Playlist", // You can allow user input too
//             }),
//           });
//           const data = await res.json();
//           if (data.success) {
//             alert("✅ Playlist added to your Spotify account!");
//           } else {
//             alert("⚠ Failed to create playlist.");
//           }
//         } catch (err) {
//           alert("❌ API request failed.");
//         }
//       }}
//       style={{
//         padding: "8px 16px",
//         borderRadius: "8px",
//         border: "none",
//         cursor: "pointer",
//         backgroundColor: "#1DB954",
//         color: "#fff",
//         fontWeight: "bold",
//       }}
//     >
//       Add Playlist
//     </button>
//   </div>
// )}

//       </div>

//       {/* Input */}
//       <div className="chat-input-container">
//         <input
//           type="text"
//           value={input}
//           onChange={(e) => setInput(e.target.value)}
//           onKeyDown={handleKeyDown}
//           placeholder={
//             chatDone
//               ? "Chat ended..."
//               : loading
//               ? "Bot is typing..."
//               : "Type your message..."
//           }
//           className="chat-input"
//           disabled={loading || chatDone}
//         />
//         <button
//           onClick={sendMessage}
//           className="send-button"
//           disabled={loading || chatDone}
//         >
//           {loading ? "..." : "Send"}
//         </button>
//       </div>
//     </div>
//   );
// }
import { useState, useEffect } from "react";
import "./ChatInterface.css";

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    { sender: "bot", text: "Hello! Good to see you here 😊" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [extracted, setExtracted] = useState(null);
  const [chatDone, setChatDone] = useState(false);
  const [playlist, setPlaylist] = useState([]);
  const [token, setToken] = useState(null);
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    document.body.className = darkMode ? "" : "light-mode";
  }, [darkMode]);

  const toggleTheme = () => setDarkMode(!darkMode);

  useEffect(() => {
    const storedToken = sessionStorage.getItem("spotify_access_token");
    if (storedToken) setToken(storedToken);
    else window.location.href = "/";
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input;
    const newMessages = [...messages, { sender: "user", text: userMessage }];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:5000/bot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "user123",
          chat_messages: newMessages.map((m) => ({
            role: m.sender === "user" ? "user" : "assistant",
            content: m.text,
          })),
          latest_user_message: userMessage,
        }),
      });

      const data = await res.json();

      if (data.status === "chatting" && data.reply) {
        setMessages((prev) => [...prev, { sender: "bot", text: data.reply }]);
      } else if (data.status === "done") {
        setExtracted(data.extracted);
        setChatDone(true);
        setMessages((prev) => [
          ...prev,
          { sender: "bot", text: "🎶 Playlist generation in progress..." },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          { sender: "bot", text: "⚠ Error fetching reply." },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "❌ Failed to connect to bot." },
      ]);
    }
    setLoading(false);
  };

  // Generate playlist after chat ends
  useEffect(() => {
    const generatePlaylist = async () => {
      if (!chatDone || !extracted || !token) return;

      try {
        const res = await fetch("http://localhost:5000/generate-playlist", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            token,
            preferences: extracted,
          }),
        });

        const data = await res.json();

        const allSongs = [
          ...(data.playlist_from_params || []),
          ...(data.playlist_from_search || []),
        ];

        if (allSongs.length) {
          setPlaylist(allSongs);
          setMessages((prev) => [
            ...prev,
            { sender: "bot", text: "✅ Playlist generated successfully!" },
          ]);
        } else {
          setMessages((prev) => [
            ...prev,
            { sender: "bot", text: "⚠ Couldn't generate playlist." },
          ]);
        }
      } catch {
        setMessages((prev) => [
          ...prev,
          { sender: "bot", text: "❌ Playlist API failed." },
        ]);
      }
    };

    generatePlaylist();
  }, [chatDone, extracted, token]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  };

  // Add playlist to Spotify
  const addPlaylistToSpotify = async () => {
    try {
      const res = await fetch("http://localhost:5000/add-playlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          playlistSongs: playlist,
          playlistName: "My AI Playlist",
        }),
      });
      const data = await res.json();
      if (data.success) alert("✅ Playlist added to your Spotify account!");
      else alert("⚠ Failed to create playlist.");
    } catch {
      alert("❌ API request failed.");
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        PLAYLIST RECOMMENDER 🎶🎶
        <button
          onClick={toggleTheme}
          style={{
            float: "right",
            padding: "5px 10px",
            borderRadius: "8px",
            border: "none",
            cursor: "pointer",
          }}
        >
          {darkMode ? "🌞 Light" : "🌙 Dark"}
        </button>
      </div>

      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`message-row ${
              msg.sender === "user" ? "user-message" : "bot-message"
            }`}
          >
            <div className="message-bubble">{msg.text}</div>
          </div>
        ))}

        {playlist.length > 0 && (
          <>
            <div className="playlist-box">
              <h4>🎧 Your Playlist</h4>
              <ul className="playlist-list">
                {playlist.map((song, idx) => (
                  <li key={idx} className="playlist-item">
                    <img
                      src={song.image || "/default_album.png"}
                      alt={song.name}
                      className="playlist-album-art"
                    />
                    <div className="playlist-info">
                      <div className="playlist-title">{song.name}</div>
                      <div className="playlist-artist">{song.artist}</div>
                      {song.preview_url ? (
                        <audio controls className="playlist-audio">
                          <source src={song.preview_url} type="audio/mpeg" />
                          Your browser does not support the audio element.
                        </audio>
                      ) : (
                        <span className="no-preview">Preview not available</span>
                      )}
                    </div>
                    {/* Delete Button */}
                    <button
                      className="delete-button"
                      onClick={() =>
                        setPlaylist((prev) => prev.filter((_, i) => i !== idx))
                      }
                    >
                      ✖
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            {/* Add Playlist Button */}
            <div style={{ marginTop: "10px", textAlign: "center" }}>
              <button
                className="add-playlist-button"
                onClick={addPlaylistToSpotify}
                style={{
                  padding: "8px 16px",
                  borderRadius: "8px",
                  border: "none",
                  cursor: "pointer",
                  backgroundColor: "#1DB954",
                  color: "#fff",
                  fontWeight: "bold",
                }}
              >
                Add Playlist
              </button>
            </div>
          </>
        )}
      </div>

      <div className="chat-input-container">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            chatDone
              ? "Chat ended..."
              : loading
              ? "Bot is typing..."
              : "Type your message..."
          }
          className="chat-input"
          disabled={loading || chatDone}
        />
        <button
          onClick={sendMessage}
          className="send-button"
          disabled={loading || chatDone}
        >
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}

