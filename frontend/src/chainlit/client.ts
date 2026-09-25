import { ChainlitAPI } from '@chainlit/react-client'

// Chainlit is mounted inside FastAPI at "/chat" (see app/main.py's
// mount_chainlit(..., path="/chat")), not at the origin root. useChatSession
// derives the socket.io path from this URL's pathname, so the mount prefix
// must be included here or the socket silently connects to the wrong path.
export const chainlitClient = new ChainlitAPI(`${window.location.origin}/chat`, 'webapp')
