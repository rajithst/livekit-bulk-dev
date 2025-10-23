const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export interface TokenResponse {
  token: string;
  url?: string;
}

export interface TokenRequest {
  roomName: string;
  participantName: string;
  metadata?: Record<string, any>;
}

/**
 * Fetch an access token from the backend API
 */
export async function fetchToken(request: TokenRequest): Promise<TokenResponse> {
  const response = await fetch(`${BACKEND_URL}/api/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch token: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Send a message to the backend API
 */
export async function sendMessageToBackend(
  conversationId: string,
  message: string
): Promise<void> {
  await fetch(`${BACKEND_URL}/api/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
  });
}

/**
 * Get conversation history from the backend
 */
export async function getConversationHistory(
  conversationId: string,
  limit: number = 50
): Promise<any[]> {
  const response = await fetch(
    `${BACKEND_URL}/api/conversations/${conversationId}/messages?limit=${limit}`
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch conversation history: ${response.statusText}`);
  }

  return response.json();
}
