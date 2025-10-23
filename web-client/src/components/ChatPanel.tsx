import { useState, useEffect, useRef } from 'react';
import { useRoomContext, useDataChannel } from '@livekit/components-react';
import './ChatPanel.css';

interface ChatMessage {
  id: string;
  sender: string;
  message: string;
  timestamp: number;
}

const ChatPanel = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const room = useRoomContext();

  // Subscribe to data channel for chat messages
  const { message } = useDataChannel('chat');

  useEffect(() => {
    if (message) {
      const decoder = new TextDecoder();
      const data = JSON.parse(decoder.decode(message.payload));
      setMessages((prev) => [...prev, {
        id: `${message.from?.identity}-${Date.now()}`,
        sender: message.from?.identity || 'Unknown',
        message: data.message,
        timestamp: Date.now(),
      }]);
    }
  }, [message]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = () => {
    if (!input.trim() || !room) return;

    const encoder = new TextEncoder();
    const data = encoder.encode(JSON.stringify({ message: input }));
    
    room.localParticipant.publishData(data, { reliable: true, topic: 'chat' });
    
    // Add own message to chat
    setMessages((prev) => [...prev, {
      id: `self-${Date.now()}`,
      sender: 'You',
      message: input,
      timestamp: Date.now(),
    }]);
    
    setInput('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-panel">
      <h3>Chat</h3>
      <div className="messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`message ${msg.sender === 'You' ? 'own-message' : ''}`}>
            <div className="message-header">
              <span className="sender">{msg.sender}</span>
              <span className="timestamp">
                {new Date(msg.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <div className="message-content">{msg.message}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type a message..."
        />
        <button onClick={sendMessage} disabled={!input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatPanel;

