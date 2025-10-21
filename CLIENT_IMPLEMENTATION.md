# Client Side Implementation Guide

## Technology Stack

### Web Client
- **React** + TypeScript (recommended by LiveKit)
- **@livekit/components-react** - UI components 
- **@livekit/components-styles** - Pre-built styles
- **@livekit/react-core** - Core React hooks

### Mobile Client
- **LiveKit iOS SDK** - Native iOS client
- **LiveKit Android SDK** - Native Android client

---

## Web Client Implementation

### Project Structure
```
client/
├── src/
│   ├── components/
│   │   ├── Room/
│   │   │   ├── index.tsx           # Room component
│   │   │   ├── ParticipantView.tsx # Single participant
│   │   │   └── Controls.tsx        # Audio/video controls
│   │   ├── Chat/
│   │   │   ├── index.tsx          # Chat interface
│   │   │   └── Message.tsx        # Message component
│   │   └── common/
│   │       ├── LoadingSpinner.tsx
│   │       └── ErrorBoundary.tsx
│   ├── hooks/
│   │   ├── useLiveKitConnection.ts
│   │   ├── useParticipants.ts
│   │   └── useAudioLevel.ts
│   ├── services/
│   │   ├── api.ts                 # Backend API client
│   │   └── livekit.ts            # LiveKit token service
│   └── types/
│       └── index.ts              # TypeScript types
├── package.json
└── vite.config.ts
```

### 1. Core Room Component

```typescript
// src/components/Room/index.tsx

import {
  LiveKitRoom,
  VideoConference,
  ControlBar,
  useLiveKitRoom,
  RoomAudioRenderer,
  StartAudio
} from '@livekit/components-react';
import '@livekit/components-styles';
import { Room as LiveKitRoom } from 'livekit-client';
import { useState, useEffect } from 'react';
import { getToken } from '../../services/livekit';

interface RoomProps {
  roomName: string;
  username: string;
}

export const Room: React.FC<RoomProps> = ({ roomName, username }) => {
  const [token, setToken] = useState<string>();
  const [error, setError] = useState<Error>();
  
  // Get LiveKit token on mount
  useEffect(() => {
    const init = async () => {
      try {
        const token = await getToken(roomName, username);
        setToken(token);
      } catch (e) {
        setError(e as Error);
      }
    };
    init();
  }, [roomName, username]);

  // Handle room errors
  const onError = (error: Error) => {
    console.error('Room error:', error);
    setError(error);
  };

  // Handle room connection state
  const onConnected = (room: LiveKitRoom) => {
    console.log('Connected to room:', room.name);
  };

  if (error) {
    return <div>Error: {error.message}</div>;
  }

  if (!token) {
    return <div>Loading...</div>;
  }

  return (
    <LiveKitRoom
      token={token}
      serverUrl={import.meta.env.VITE_LIVEKIT_URL}
      connect={true}
      onError={onError}
      onConnected={onConnected}
      // Audio optimization
      audioCaptureDefaults={{
        autoGainControl: true,
        echoCancellation: true,
        noiseSuppression: true
      }}
      // Video optimization
      videoCaptureDefaults={{
        resolution: { width: 640, height: 480 },
        facingMode: 'user'
      }}
      // Data channel options
      rtcConfig={{
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          // Add your TURN servers here
        ]
      }}
    >
      {/* Audio pre-playback for iOS */}
      <StartAudio />
      
      {/* Global room audio handler */}
      <RoomAudioRenderer />
      
      {/* Main video conference UI */}
      <VideoConference />
      
      {/* Audio/video controls */}
      <ControlBar />
    </LiveKitRoom>
  );
};
```

### 2. Custom Participant View

```typescript
// src/components/Room/ParticipantView.tsx

import {
  ParticipantView as LiveKitParticipantView,
  useParticipant,
  AudioTrack,
  VideoTrack
} from '@livekit/components-react';
import { Track, Participant } from 'livekit-client';
import { useAudioLevel } from '../../hooks/useAudioLevel';

interface ParticipantViewProps {
  participant: Participant;
  displayName?: string;
}

export const ParticipantView: React.FC<ParticipantViewProps> = ({
  participant,
  displayName
}) => {
  // Get participant tracks and state
  const {
    isSpeaking,
    isLocal,
    subscribedTracks,
    cameraPublication,
    microphonePublication
  } = useParticipant(participant);

  // Get audio level for visualization
  const audioLevel = useAudioLevel(participant);

  return (
    <div className={`participant ${isSpeaking ? 'speaking' : ''}`}>
      {/* Video track */}
      {cameraPublication?.isSubscribed && (
        <VideoTrack
          track={cameraPublication.track}
          priority={isLocal ? Track.Priority.High : Track.Priority.Medium}
        />
      )}
      
      {/* Audio track */}
      {microphonePublication?.isSubscribed && (
        <AudioTrack
          track={microphonePublication.track}
        />
      )}
      
      {/* Audio visualization */}
      <div 
        className="audio-level" 
        style={{ transform: `scaleY(${audioLevel})` }} 
      />
      
      {/* Participant info */}
      <div className="participant-info">
        <span className="name">
          {displayName || participant.identity}
          {isLocal && ' (You)'}
        </span>
        <div className="indicators">
          {!cameraPublication?.isSubscribed && (
            <span className="camera-off">Camera Off</span>
          )}
          {!microphonePublication?.isSubscribed && (
            <span className="mic-off">Mic Off</span>
          )}
        </div>
      </div>
    </div>
  );
};
```

### 3. Room Controls

```typescript
// src/components/Room/Controls.tsx

import {
  ControlBar,
  useLocalParticipant,
  useLiveKitRoom
} from '@livekit/components-react';
import { Track } from 'livekit-client';

export const Controls: React.FC = () => {
  const { room } = useLiveKitRoom();
  const { localParticipant } = useLocalParticipant();
  
  // Handle device changes
  const onDeviceChanged = async (deviceId: string, kind: string) => {
    try {
      if (kind === 'audioinput') {
        await localParticipant?.setMicrophoneEnabled(true, { deviceId });
      } else if (kind === 'videoinput') {
        await localParticipant?.setCameraEnabled(true, { deviceId });
      }
    } catch (e) {
      console.error('Error changing device:', e);
    }
  };

  // Handle screen share
  const onScreenShareClick = async () => {
    try {
      if (!localParticipant?.isScreenShareEnabled) {
        await room?.localParticipant.setScreenShareEnabled(true);
      } else {
        await room?.localParticipant.setScreenShareEnabled(false);
      }
    } catch (e) {
      console.error('Error toggling screen share:', e);
    }
  };

  return (
    <ControlBar
      controls={{
        microphone: true,
        camera: true,
        screenShare: true,
        leave: true
      }}
      onDeviceChanged={onDeviceChanged}
      onScreenShareClick={onScreenShareClick}
    />
  );
};
```

### 4. LiveKit Connection Hook

```typescript
// src/hooks/useLiveKitConnection.ts

import { useCallback, useEffect, useState } from 'react';
import {
  Room,
  RoomEvent,
  Participant,
  RemoteParticipant,
  LocalParticipant,
  RoomOptions,
  ConnectionState
} from 'livekit-client';

interface UseLiveKitConnectionProps {
  url: string;
  token: string;
  options?: RoomOptions;
}

export const useLiveKitConnection = ({
  url,
  token,
  options
}: UseLiveKitConnectionProps) => {
  const [room, setRoom] = useState<Room>();
  const [connectionState, setConnectionState] = useState<ConnectionState>();
  const [error, setError] = useState<Error>();
  const [participants, setParticipants] = useState<Participant[]>([]);
  
  // Connect to room
  const connect = useCallback(async () => {
    try {
      const room = new Room(options);
      
      // Handle connection state changes
      room.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
        setConnectionState(state);
      });
      
      // Handle participants
      room.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
        setParticipants(prev => [...prev, participant]);
      });
      
      room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
        setParticipants(prev => prev.filter(p => p.sid !== participant.sid));
      });
      
      // Connect
      await room.connect(url, token);
      setRoom(room);
      
      // Add local participant
      setParticipants([room.localParticipant]);
      
    } catch (e) {
      setError(e as Error);
    }
  }, [url, token, options]);
  
  // Disconnect cleanup
  const disconnect = useCallback(() => {
    room?.disconnect();
    setRoom(undefined);
    setParticipants([]);
  }, [room]);
  
  // Auto-connect on mount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);
  
  return {
    room,
    connectionState,
    error,
    participants,
    connect,
    disconnect
  };
};
```

### 5. LiveKit Token Service

```typescript
// src/services/livekit.ts

import axios from 'axios';

interface TokenResponse {
  token: string;
}

export const getToken = async (
  roomName: string,
  participantName: string
): Promise<string> => {
  try {
    const response = await axios.post<TokenResponse>(
      '/api/v1/livekit/token',
      {
        room: roomName,
        username: participantName,
        // Additional metadata
        metadata: JSON.stringify({
          name: participantName,
          // Add any custom metadata
        })
      }
    );
    return response.data.token;
  } catch (error) {
    console.error('Error getting LiveKit token:', error);
    throw error;
  }
};
```

### 6. Audio Level Hook

```typescript
// src/hooks/useAudioLevel.ts

import { useEffect, useState } from 'react';
import { Participant } from 'livekit-client';

export const useAudioLevel = (participant: Participant) => {
  const [audioLevel, setAudioLevel] = useState(0);
  
  useEffect(() => {
    const onAudioLevel = (level: number) => {
      // Smooth audio level changes
      setAudioLevel(prev => prev * 0.7 + level * 0.3);
    };
    
    // Subscribe to audio level updates
    const subscription = participant.getTrackPublication('audio')
      ?.audioLevel?.subscribe(onAudioLevel);
    
    return () => {
      subscription?.();
    };
  }, [participant]);
  
  return audioLevel;
};
```

### 7. Environment Configuration

```typescript
// .env
VITE_LIVEKIT_URL=wss://your-livekit-server.com
VITE_API_URL=https://your-backend.com/api/v1
```

---

## Mobile Implementation

### iOS Client (Swift)

```swift
// RoomViewController.swift

import LiveKitClient
import UIKit

class RoomViewController: UIViewController {
    private var room: Room?
    private var participants: [Participant] = []
    
    override func viewDidLoad() {
        super.viewDidLoad()
        connectToRoom()
    }
    
    private func connectToRoom() {
        // Get token from your backend
        ApiClient.shared.getToken(room: "room-name") { [weak self] result in
            switch result {
            case .success(let token):
                self?.setupRoom(with: token)
            case .failure(let error):
                print("Error getting token:", error)
            }
        }
    }
    
    private func setupRoom(with token: String) {
        // Room configuration
        let roomOptions = RoomOptions(
            adaptiveStream: true,
            dynacast: true,
            reportStats: true
        )
        
        // Connect options
        let connectOptions = ConnectOptions(
            autoSubscribe: true,
            publishDefaults: PublishDefaults(
                audioTrack: true,
                videoTrack: true
            )
        )
        
        // Create room
        room = Room(delegate: self)
        
        // Connect
        Task {
            do {
                try await room?.connect(
                    url: "wss://your-livekit-server.com",
                    token: token,
                    connectOptions: connectOptions,
                    roomOptions: roomOptions
                )
            } catch {
                print("Error connecting to room:", error)
            }
        }
    }
}

// MARK: - Room Delegate
extension RoomViewController: RoomDelegate {
    func room(_ room: Room, participant: RemoteParticipant, didSubscribe track: Track) {
        // Handle new track
    }
    
    func room(_ room: Room, participant: RemoteParticipant, didUnsubscribe track: Track) {
        // Handle removed track
    }
    
    func room(_ room: Room, didConnect roomInfo: RoomInfo) {
        print("Connected to room:", roomInfo.name)
    }
    
    func room(_ room: Room, didDisconnect error: Error?) {
        if let error = error {
            print("Room disconnected with error:", error)
        }
    }
}
```

### Android Client (Kotlin)

```kotlin
// RoomActivity.kt

import io.livekit.android.LiveKit
import io.livekit.android.room.Room
import io.livekit.android.room.RoomListener

class RoomActivity : AppCompatActivity(), RoomListener {
    private var room: Room? = null
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_room)
        
        connectToRoom()
    }
    
    private fun connectToRoom() {
        // Get token from backend
        apiClient.getToken("room-name") { token ->
            setupRoom(token)
        }
    }
    
    private fun setupRoom(token: String) {
        lifecycleScope.launch {
            try {
                // Create room
                room = LiveKit.create(applicationContext)
                
                // Connect
                room?.connect(
                    url = "wss://your-livekit-server.com",
                    token = token,
                    roomOptions = RoomOptions(
                        adaptiveStream = true,
                        dynacast = true
                    ),
                    connectOptions = ConnectOptions(
                        autoSubscribe = true
                    )
                )
                
                // Add listener
                room?.addListener(this@RoomActivity)
                
            } catch (e: Exception) {
                Log.e("RoomActivity", "Error connecting to room", e)
            }
        }
    }
    
    // Room Listener Implementation
    override fun onParticipantConnected(participant: RemoteParticipant) {
        // Handle new participant
    }
    
    override fun onParticipantDisconnected(participant: RemoteParticipant) {
        // Handle participant left
    }
    
    override fun onTrackSubscribed(
        track: Track,
        publication: RemoteTrackPublication,
        participant: RemoteParticipant
    ) {
        // Handle new track
    }
    
    override fun onDisconnect() {
        // Handle disconnection
    }
}
```

---

## Best Practices

### 1. Connection Management
- Always handle connection errors
- Implement reconnection logic
- Clean up resources on disconnect
- Use proper lifecycle management

### 2. Track Optimization
```typescript
// Optimize video tracks
const videoOptions = {
  resolution: {
    width: 640,
    height: 480
  },
  encodings: [
    { maxBitrate: 150_000, maxFramerate: 15 }, // Low
    { maxBitrate: 500_000, maxFramerate: 30 }, // Medium
    { maxBitrate: 1_500_000, maxFramerate: 30 } // High
  ]
};

// Optimize audio tracks
const audioOptions = {
  autoGainControl: true,
  echoCancellation: true,
  noiseSuppression: true
};
```

### 3. Error Handling
```typescript
room.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
  switch (state) {
    case ConnectionState.Disconnected:
      // Handle disconnect
      break;
    case ConnectionState.Connected:
      // Handle connect
      break;
    case ConnectionState.Reconnecting:
      // Show reconnecting UI
      break;
    case ConnectionState.Failed:
      // Show error UI
      break;
  }
});
```

### 4. Resource Management
```typescript
// Clean up tracks when component unmounts
useEffect(() => {
  return () => {
    localParticipant?.tracks.forEach(pub => {
      pub.track?.stop();
    });
    room?.disconnect();
  };
}, [room, localParticipant]);
```

### 5. Performance Optimization
```typescript
// Use memo for participant list
const participants = useMemo(() => {
  return Array.from(room?.participants.values() ?? []);
}, [room?.participants]);

// Use callback for event handlers
const onParticipantConnected = useCallback((participant: RemoteParticipant) => {
  // Handle new participant
}, []);
```

### 6. Mobile Considerations
```typescript
// Handle mobile audio session
if (Platform.OS === 'ios') {
  await AVAudioSession.sharedInstance()
    .setCategory(AVAudioSessionCategoryPlayAndRecord);
}

// Handle screen orientation
useEffect(() => {
  Screen.unlockAsync();
  return () => {
    Screen.lockAsync(ScreenOrientation.OrientationLock.PORTRAIT_UP);
  };
}, []);
```

---

## Testing

### Unit Tests

```typescript
// Room.test.tsx
import { render, act } from '@testing-library/react';
import { Room } from './Room';

describe('Room', () => {
  it('should connect to LiveKit', async () => {
    const onConnected = jest.fn();
    
    render(
      <Room
        roomName="test-room"
        username="test-user"
        onConnected={onConnected}
      />
    );
    
    // Wait for connection
    await act(async () => {
      await new Promise(r => setTimeout(r, 100));
    });
    
    expect(onConnected).toHaveBeenCalled();
  });
});
```

### Integration Tests

```typescript
// RoomIntegration.test.tsx
import { test, expect } from '@playwright/test';

test('should join room and enable camera', async ({ page }) => {
  await page.goto('/room/test');
  
  // Wait for connection
  await expect(page.locator('.connection-state')).toHaveText('connected');
  
  // Enable camera
  await page.click('.camera-button');
  
  // Verify video track exists
  await expect(page.locator('video')).toBeVisible();
});
```

---

## Deployment Configuration

### Environment Variables

```env
# LiveKit Server
VITE_LIVEKIT_URL=wss://your-livekit-server.com

# Backend API
VITE_API_URL=https://your-backend.com/api/v1

# LiveKit Keys (backend only)
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# TURN Servers (optional)
VITE_TURN_URLS=turn:your-turn-server.com:3478
VITE_TURN_USERNAME=username
VITE_TURN_CREDENTIAL=password
```

### nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name your-app.com;

    # SSL configuration
    ssl_certificate /etc/ssl/your-app.crt;
    ssl_certificate_key /etc/ssl/your-app.key;

    # LiveKit WebSocket proxy
    location /livekit/ {
        proxy_pass https://your-livekit-server.com;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Static files
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
}
```

---

## Documentation

For more details, see:
- [LiveKit React Components](https://docs.livekit.io/client-sdk-react/interfaces/components_React.LiveKitRoom.html)
- [LiveKit Client SDK](https://docs.livekit.io/client-sdk-js/)
- [LiveKit iOS SDK](https://docs.livekit.io/client-sdk-ios/)
- [LiveKit Android SDK](https://docs.livekit.io/client-sdk-android/)
