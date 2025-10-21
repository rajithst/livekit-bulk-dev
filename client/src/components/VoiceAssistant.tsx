import { useEffect, useState } from 'react'
import { useLocalParticipant, useRoom } from '@livekit/components-react'
import { DataPacket_Kind, RoomEvent } from 'livekit-client'
import useAssistantStore from '@/store/assistantStore'

export default function VoiceAssistant() {
  const { room } = useRoom()
  const { localParticipant } = useLocalParticipant()
  const [isListening, setIsListening] = useState(false)
  const { messages, addMessage } = useAssistantStore()

  useEffect(() => {
    if (!room) return

    const handleData = (payload: Uint8Array, participant: any, kind: DataPacket_Kind) => {
      if (kind === DataPacket_Kind.RELIABLE) {
        try {
          const message = JSON.parse(new TextDecoder().decode(payload))
          addMessage(message)
        } catch (error) {
          console.error('Error parsing message:', error)
        }
      }
    }

    room.on(RoomEvent.DataReceived, handleData)

    return () => {
      room.off(RoomEvent.DataReceived, handleData)
    }
  }, [room, addMessage])

  const toggleListening = () => {
    if (!localParticipant) return

    if (isListening) {
      localParticipant.setMicrophoneEnabled(false)
    } else {
      localParticipant.setMicrophoneEnabled(true)
    }
    setIsListening(!isListening)
  }

  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="space-y-4 mb-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`p-3 rounded-lg ${
              message.role === 'assistant' ? 'bg-blue-100' : 'bg-gray-100'
            }`}
          >
            <p className="text-sm font-semibold">{message.role}</p>
            <p>{message.content}</p>
          </div>
        ))}
      </div>

      <button
        onClick={toggleListening}
        className={`px-4 py-2 rounded-full w-16 h-16 flex items-center justify-center ${
          isListening ? 'bg-red-500' : 'bg-blue-500'
        } text-white`}
      >
        <span className="sr-only">{isListening ? 'Stop' : 'Start'}</span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="w-6 h-6"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z"
          />
        </svg>
      </button>
    </div>
  )
}