# Client-Side Architecture (React)

## Overview
The client application is built using React with TypeScript and leverages LiveKit's official React components for real-time audio/video communication. The architecture follows the official [LiveKit React Quickstart](https://docs.livekit.io/home/quickstarts/react/) guidelines, ensuring best practices and seamless integration with the LiveKit ecosystem.

## Tech Stack
- **React 18.3** - Modern React with hooks and concurrent features
- **TypeScript 5.5** - Type-safe development
- **Vite 5.4** - Fast build tool and dev server
- **@livekit/components-react 2.5** - Official LiveKit React components
- **livekit-client 2.5** - Core LiveKit client SDK
- **Zustand 4.5** - Lightweight state management
- **@livekit/components-styles** - Pre-built styling for LiveKit components

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     App.tsx (Root)                      │
│  - Connection management                                │
│  - Token authentication                                 │
│  - Room join flow                                       │
└──────────────────┬──────────────────────────────────────┘
                   │
         ┌─────────▼─────────┐
         │   LiveKitRoom     │ ◄─── From @livekit/components-react
         │  (Connection)     │
         └─────────┬─────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼───┐    ┌────▼────┐   ┌────▼────────┐
│Partic-│    │  Chat   │   │   Voice     │
│ipant  │    │  Panel  │   │  Assistant  │
│View   │    │         │   │  Controls   │
└───────┘    └─────────┘   └─────────────┘
```

## Key Components

### 1. App.tsx (Main Application)
**Purpose**: Root component managing authentication and room connection

**Features**:
- Token-based authentication via backend API
- Join room flow with user input
- Error handling and loading states
- LiveKitRoom wrapper configuration

**Code Example**:
```tsx
<LiveKitRoom
  token={token}
  serverUrl={url}
  connectOptions={{ autoSubscribe: true }}
  data-lk-theme="default"
>
  {/* Child components */}
</LiveKitRoom>
```

### 2. ParticipantView Component
**Purpose**: Display video/audio tiles for all participants

**LiveKit Hooks Used**:
- `useParticipants()` - Get all participants in room
- `useTracks()` - Subscribe to video/audio tracks
- `ParticipantTile` - Render individual participant UI

**Features**:
- Automatic track subscription
- Responsive grid layout
- Camera and screen share support
- Placeholder for participants without video

**Implementation**:
```tsx
const participants = useParticipants();
const tracks = useTracks([
  { source: Track.Source.Camera, withPlaceholder: true },
  { source: Track.Source.ScreenShare, withPlaceholder: false },
]);
```

### 3. ChatPanel Component
**Purpose**: Text-based messaging using LiveKit data channels

**LiveKit Hooks Used**:
- `useRoomContext()` - Access room instance
- `useDataChannel()` - Subscribe to data messages

**Features**:
- Real-time message synchronization
- Message history display
- Sender identification
- Timestamp display
- Keyboard shortcuts (Enter to send)

**Data Channel Usage**:
```tsx
const { message } = useDataChannel('chat');
room.localParticipant.publishData(data, { 
  reliable: true, 
  topic: 'chat' 
});
```

### 4. VoiceAssistantControls Component
**Purpose**: Visual feedback for agent state and audio visualization

**LiveKit Hooks Used**:
- `useVoiceAssistant()` - Get assistant state and audio
- `BarVisualizer` - Audio level visualization

**Features**:
- Real-time state display (idle, listening, thinking, speaking)
- Animated status indicators
- Audio waveform visualization
- Contextual messaging based on state

**States**:
- `idle` - Ready to assist
- `listening` - Capturing user speech (STT active)
- `thinking` - Processing with LLM
- `speaking` - Playing TTS response

## State Management

### Zustand Store (assistantStore.ts)
Manages global application state:

```typescript
{
  token: string;           // LiveKit access token
  url: string;             // WebSocket URL for LiveKit server
  roomName: string;        // Current room name
  userName: string;        // Participant name
  isConnected: boolean;    // Connection status
}
```

### Component-Level State
Each component maintains its own local state:
- **ChatPanel**: Message history, input state
- **App**: Loading state, error messages
- **ParticipantView**: No local state (uses LiveKit hooks)

## API Integration

### Token Generation
Located in `src/utils/api.ts`

```typescript
fetchToken({
  roomName: string,
  participantName: string,
  metadata?: Record<string, any>
}) => Promise<{ token: string }>
```

**Backend Endpoint**: `POST /api/token`

**Flow**:
1. User enters room name and username
2. Client calls `fetchToken()` with credentials
3. Backend generates JWT token with LiveKit SDK
4. Client receives token and connects to LiveKit room

### Conversation API
Additional utilities for backend integration:
- `sendMessageToBackend()` - Store messages in backend
- `getConversationHistory()` - Retrieve message history

## Styling Approach

### 1. Global Styles (index.css)
- Reset and base styles
- Font definitions
- LiveKit component overrides

### 2. Component Styles (*.css)
- Scoped component styles
- Dark theme with professional colors
- Responsive layouts with CSS Grid/Flexbox

### 3. LiveKit Default Theme
Using `@livekit/components-styles` for consistent UI:
```tsx
import '@livekit/components-styles';
<LiveKitRoom data-lk-theme="default">
```

## Environment Configuration

### Environment Variables (.env)
```bash
VITE_LIVEKIT_URL=ws://localhost:7880
VITE_BACKEND_URL=http://localhost:8000
```

### Type Definitions (vite-env.d.ts)
```typescript
interface ImportMetaEnv {
  readonly VITE_BACKEND_URL: string
  readonly VITE_LIVEKIT_URL: string
}
```

## Project Structure

```
web-client/
├── src/
│   ├── components/
│   │   ├── ParticipantView.tsx       # Participant video tiles
│   │   ├── ParticipantView.css
│   │   ├── ChatPanel.tsx              # Text chat interface
│   │   ├── ChatPanel.css
│   │   ├── VoiceAssistantControls.tsx # Agent status UI
│   │   └── VoiceAssistantControls.css
│   ├── store/
│   │   └── assistantStore.ts          # Zustand state
│   ├── utils/
│   │   └── api.ts                     # Backend API calls
│   ├── App.tsx                        # Main component
│   ├── App.css
│   ├── main.tsx                       # Entry point
│   ├── index.css                      # Global styles
│   └── vite-env.d.ts                  # Type definitions
├── index.html                         # HTML template
├── vite.config.ts                     # Vite configuration
├── tsconfig.json                      # TypeScript config
├── package.json                       # Dependencies
├── .env.example                       # Environment template
└── README.md                          # Documentation
```

## Development Workflow

### 1. Installation
```bash
cd web-client
npm install
```

### 2. Configuration
```bash
cp .env.example .env
# Edit .env with your LiveKit and backend URLs
```

### 3. Development
```bash
npm run dev
# Opens http://localhost:5173
```

### 4. Build
```bash
npm run build
# Output in dist/
```

## Integration Points

### With LiveKit Server
- WebSocket connection via `VITE_LIVEKIT_URL`
- Token-based authentication
- Real-time media tracks (audio/video)
- Data channels for chat

### With Backend API
- Token generation endpoint
- Conversation storage
- Message history retrieval
- Error logging

### With Voice Agent
- Audio track from agent's TTS
- Data channels for metadata
- State synchronization via room metadata
- Participant metadata for context

## Best Practices

### 1. LiveKit Components
- Always wrap with `<LiveKitRoom>`
- Use hooks inside LiveKitRoom context
- Enable `autoSubscribe` for automatic track handling

### 2. Error Handling
- Display user-friendly error messages
- Graceful degradation on connection loss
- Loading states for async operations

### 3. Performance
- Lazy load components when possible
- Optimize re-renders with React.memo
- Use LiveKit's built-in optimizations

### 4. Security
- Never expose tokens in client code
- Always fetch tokens from secure backend
- Validate room access server-side

## Future Enhancements

### Planned Features
- Screen sharing controls
- Recording indicators
- Participant controls (mute/kick)
- Chat file sharing
- Conversation export
- Mobile responsive improvements

### Agent Integration
- Real-time transcription display
- LLM response streaming
- Voice activity detection UI
- Custom agent controls

## References
- [LiveKit React Quickstart](https://docs.livekit.io/home/quickstarts/react/)
- [LiveKit React Components](https://docs.livekit.io/components/react/)
- [LiveKit Client SDK](https://docs.livekit.io/client-sdk-js/)
- [Vite Documentation](https://vitejs.dev/)
- [Zustand Documentation](https://github.com/pmndrs/zustand)

This architecture ensures a robust, scalable, and maintainable client application that integrates seamlessly with LiveKit's ecosystem and your voice assistant backend.
