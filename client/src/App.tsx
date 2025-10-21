import { LiveKitRoom } from '@livekit/components-react'
import { useState } from 'react'
import VoiceAssistant from '@/components/VoiceAssistant'

function App() {
  const [token, setToken] = useState('')
  
  // Fetch token from your server
  const fetchToken = async () => {
    try {
      const response = await fetch('YOUR_SERVER_URL/token')
      const { token } = await response.json()
      setToken(token)
    } catch (error) {
      console.error('Error fetching token:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {token ? (
        <LiveKitRoom
          token={token}
          serverUrl={import.meta.env.VITE_LIVEKIT_URL}
          connect={true}
          video={false}
          audio={true}
        >
          <VoiceAssistant />
        </LiveKitRoom>
      ) : (
        <button
          onClick={fetchToken}
          className="px-4 py-2 bg-blue-500 text-white rounded"
        >
          Connect to Voice Assistant
        </button>
      )}
    </div>
  )
}