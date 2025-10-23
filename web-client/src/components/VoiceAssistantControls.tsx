import { useVoiceAssistant, BarVisualizer } from '@livekit/components-react';
import './VoiceAssistantControls.css';

const VoiceAssistantControls = () => {
  const { state, audioTrack } = useVoiceAssistant();

  return (
    <div className="voice-assistant">
      <h3>Voice Assistant</h3>
      <div className="assistant-status">
        <div className={`status-indicator ${state}`}>
          <span className="status-dot"></span>
          <span className="status-text">{state}</span>
        </div>
      </div>
      
      {audioTrack && (
        <div className="audio-visualizer">
          <BarVisualizer
            state={state}
            barCount={5}
            trackRef={audioTrack}
            options={{ minHeight: 20 }}
          />
        </div>
      )}

      <div className="assistant-info">
        <p className="info-text">
          {state === 'listening' && '🎤 Listening to your voice...'}
          {state === 'thinking' && '🤔 Processing your request...'}
          {state === 'speaking' && '🔊 Agent is speaking...'}
          {state === 'idle' && '✨ Ready to assist you'}
        </p>
      </div>
    </div>
  );
};

export default VoiceAssistantControls;

