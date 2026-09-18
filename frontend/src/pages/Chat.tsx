import { useChatData, useChatInteract, useChatMessages, useChatSession } from '@chainlit/react-client'
import { type FormEvent, useEffect, useState } from 'react'

export function Chat() {
  const { connect, disconnect, session } = useChatSession()
  const { connected, loading, error, disabled } = useChatData()
  const { messages } = useChatMessages()
  const { sendMessage } = useChatInteract()
  const [draft, setDraft] = useState('')

  useEffect(() => {
    if (!session) {
      connect({ userEnv: {} })
    }
    return () => disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const content = draft.trim()
    if (!content) return
    sendMessage({ name: 'user', type: 'user_message', output: content })
    setDraft('')
  }

  return (
    <div className="chat-page">
      <div className="chat-status">
        {error && <span className="chat-status--error">Connection error</span>}
        {!error && !connected && <span>Connecting…</span>}
        {!error && connected && <span className="chat-status--ok">Connected</span>}
      </div>

      <div className="compliance-banner" role="note">
        <i className="fas fa-triangle-exclamation" aria-hidden="true" />
        <span>
          Please do not enter client names, TFNs, member numbers or other client-identifying information.
        </span>
      </div>

      <div className="chat-messages">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`chat-message chat-message--${message.type === 'user_message' ? 'user' : 'assistant'}`}
          >
            <div className="chat-message__output">{message.output}</div>
          </div>
        ))}
        {loading && <div className="chat-message chat-message--assistant chat-message--pending">…</div>}
      </div>

      <form className="chat-composer" onSubmit={handleSubmit}>
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ask any accounting or business question"
          disabled={disabled || !connected}
        />
        <button type="submit" disabled={disabled || !connected || !draft.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}
