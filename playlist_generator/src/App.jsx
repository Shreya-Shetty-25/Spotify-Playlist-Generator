import { Routes, Route } from "react-router-dom";
import SpotifyLoginPKCE from "./pages/SpotifyLoginPKCE";
import ChatInterface from "./pages/Chat";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<SpotifyLoginPKCE />} />
      <Route path="/chat" element={<ChatInterface />} />
    </Routes>
  );
}
