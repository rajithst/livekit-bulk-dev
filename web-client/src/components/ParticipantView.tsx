import { 
  useParticipants, 
  ParticipantTile,
  useTracks,
  TrackRefContext,
} from '@livekit/components-react';
import { Track } from 'livekit-client';
import './ParticipantView.css';

const ParticipantView = () => {
  const participants = useParticipants();
  const tracks = useTracks(
    [
      { source: Track.Source.Camera, withPlaceholder: true },
      { source: Track.Source.ScreenShare, withPlaceholder: false },
    ],
    { onlySubscribed: false },
  );

  return (
    <div className="participant-view">
      <h2>Participants ({participants.length})</h2>
      <div className="participant-grid">
        {tracks.map((track) => (
          <TrackRefContext.Provider value={track} key={track.publication.trackSid}>
            <ParticipantTile />
          </TrackRefContext.Provider>
        ))}
      </div>
    </div>
  );
};

export default ParticipantView;

