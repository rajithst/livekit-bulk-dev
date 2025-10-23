import { create } from 'zustand';

interface AssistantState {
  token: string;
  url: string;
  roomName: string;
  userName: string;
  isConnected: boolean;
  setToken: (token: string) => void;
  setUrl: (url: string) => void;
  setRoomName: (roomName: string) => void;
  setUserName: (userName: string) => void;
  setIsConnected: (isConnected: boolean) => void;
}

export const useAssistantStore = create<AssistantState>((set) => ({
  token: '',
  url: import.meta.env.VITE_LIVEKIT_URL || 'ws://localhost:7880',
  roomName: '',
  userName: '',
  isConnected: false,
  setToken: (token: string) => set({ token }),
  setUrl: (url: string) => set({ url }),
  setRoomName: (roomName: string) => set({ roomName }),
  setUserName: (userName: string) => set({ userName }),
  setIsConnected: (isConnected: boolean) => set({ isConnected }),
}));

