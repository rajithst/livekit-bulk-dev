import { create } from 'zustand'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface AssistantStore {
  messages: Message[]
  addMessage: (message: Message) => void
  clearMessages: () => void
}

const useAssistantStore = create<AssistantStore>((set) => ({
  messages: [],
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  clearMessages: () => set({ messages: [] }),
}))

export default useAssistantStore