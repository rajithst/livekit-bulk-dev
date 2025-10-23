# LiveKit Web Client

A React-based web client for the LiveKit Voice Assistant application.

## Features

- **Real-time Video/Audio Communication**: Using LiveKit React components
- **Voice Assistant Integration**: Visual feedback for STT, LLM, and TTS states
- **Chat Panel**: Text-based communication with data channels
- **Participant Management**: Display and manage multiple participants
- **Responsive Design**: Mobile-friendly layout

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **LiveKit Components React** for real-time communication
- **Zustand** for state management

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Running LiveKit server
- Backend API server (for token generation)

### Installation

1. Install dependencies:
```bash
cd web-client
npm install
```

2. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```
VITE_LIVEKIT_URL=ws://your-livekit-server:7880
VITE_BACKEND_URL=http://your-backend:8000
```

### Development

Run the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build

Build for production:
```bash
npm run build
```

Preview production build:
```bash
npm run preview
```

## Project Structure

```
web-client/
├── src/
│   ├── components/
│   │   ├── ParticipantView.tsx      # Video/audio participant tiles
│   │   ├── ChatPanel.tsx             # Text chat interface
│   │   └── VoiceAssistantControls.tsx # Voice assistant status
│   ├── store/
│   │   └── assistantStore.ts         # Zustand state management
│   ├── App.tsx                       # Main application component
│   ├── main.tsx                      # Entry point
│   └── index.css                     # Global styles
├── index.html                        # HTML template
├── vite.config.ts                    # Vite configuration
└── package.json                      # Dependencies and scripts
```

## Usage

1. Open the application in your browser
2. Enter a room name and your name
3. Click "Join Room" to connect
4. Start speaking to interact with the voice assistant
5. View other participants and use the chat panel

## Components

### ParticipantView
Displays video/audio tiles for all participants in the room using LiveKit's `ParticipantTile` component.

### ChatPanel
Text-based chat using LiveKit's data channels. Messages are synchronized across all participants.

### VoiceAssistantControls
Shows the current state of the voice assistant (listening, thinking, speaking, idle) with visual feedback.

## Configuration

The app can be configured through environment variables:

- `VITE_LIVEKIT_URL`: WebSocket URL of your LiveKit server
- `VITE_BACKEND_URL`: HTTP URL of your backend API

## Integration with Backend

The client fetches access tokens from the backend API:

```typescript
POST /api/token
{
  "roomName": "my-room",
  "participantName": "John Doe"
}
```

Response:
```json
{
  "token": "eyJhbGc..."
}
```

## License

MIT
