import { useState, useEffect } from 'react';
import { LiveKitRoom, RoomAudioRenderer, useVoiceAssistant } from '@livekit/components-react';
import '@livekit/components-styles';
import VoiceAssistantControls from './components/VoiceAssistantControls';
import ParticipantView from './components/ParticipantView';
import ChatPanel from './components/ChatPanel';
import { useAssistantStore } from './store/assistantStore';
import { fetchToken } from './utils/api';
import './App.css';

function App() {
  const { token, url, setToken } = useAssistantStore();
  const [roomName, setRoomName] = useState('');
  const [userName, setUserName] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch token from backend
  const handleJoinRoom = async () => {
    if (!roomName || !userName) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetchToken({
        roomName,
        participantName: userName,
      });
      setToken(response.token);
      setIsConnected(true);
    } catch (err) {
      console.error('Failed to fetch token:', err);
      setError('Failed to join room. Please check your connection and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      handleJoinRoom();
    }
  };

  if (!isConnected) {
    return (
      <div className="join-form">
        <h1>Join LiveKit Voice Assistant</h1>
        {error && <div className="error-message">{error}</div>}
        <input
          type="text"
          placeholder="Room Name"
          value={roomName}
          onChange={(e) => setRoomName(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={isLoading}
        />
        <input
          type="text"
          placeholder="Your Name"
          value={userName}
          onChange={(e) => setUserName(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={isLoading}
        />
        <button 
          onClick={handleJoinRoom} 
          disabled={!roomName || !userName || isLoading}
        >
          {isLoading ? 'Joining...' : 'Join Room'}
        </button>
      </div>
    );
  }

  return (
    <LiveKitRoom
      token={token}
      serverUrl={url}
      connectOptions={{ autoSubscribe: true }}
      data-lk-theme="default"
      className="livekit-room"
    >
      <div className="app-container">
        <header>
          <h1>LiveKit Voice Assistant</h1>
        </header>
        <main>
          <div className="content-grid">
            <div className="video-section">
              <ParticipantView />
            </div>
            <div className="sidebar">
              <VoiceAssistantControls />
              <ChatPanel />
            </div>
          </div>
        </main>
        <RoomAudioRenderer />
      </div>
    </LiveKitRoom>
  );
}

export default App;

