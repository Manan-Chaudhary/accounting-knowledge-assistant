import { useChatData, useChatInteract, useChatMessages, useChatSession } from '@chainlit/react-client'
import { type FormEvent, useEffect, useState } from 'react'
import { Layout } from '../components/Layout'
import { useSearchParams } from 'react-router-dom'

// --- Assistant message parsing -------------------------------------------
//
// Chainlit messages arrive as a single markdown string (`message.output`).
// To render them as structured cards (Legal position / How Alfa Focus
// handles it / Sources), the backend response should use this convention:
//
//   >badge: Income year 2025-26          (optional, first line)
//
//   ## Legal position
//   Free text here.
//
//   ### How Alfa Focus handles it
//   Free text here — rendered in the grey callout box.
//
//   ### Sources / References
//   - [ATO · Concessional contributions cap](https://www.ato.gov.au/...)
//   - [Alfa Focus · SMSF contribution review procedure](https://...)
//
// Any heading that isn't "handles it" or "sources/references" is rendered
// as a plain labelled paragraph (e.g. "Legal position"). Content with no
// headings at all just renders as plain text, so this is backwards
// compatible with the current backend.
type ContentBlock =
  | { kind: 'paragraph'; title: string | null; text: string }
  | { kind: 'callout'; title: string; text: string }
  | { kind: 'sources'; title: string; items: { label: string; url: string }[] }

function extractBadge(raw: string): { badge: string | null; content: string } {
  const match = raw.match(/^>\s*badge:\s*(.+)$/m)
  if (!match) return { badge: null, content: raw }
  return { badge: match[1].trim(), content: raw.replace(match[0], '').trim() }
}

function parseAssistantContent(raw: string): ContentBlock[] {
  const lines = raw.split('\n')
  const blocks: ContentBlock[] = []
  let i = 0

  const introLines: string[] = []
  while (i < lines.length && !/^#{2,3}\s+/.test(lines[i])) {
    introLines.push(lines[i])
    i++
  }
  const intro = introLines.join('\n').trim()
  if (intro) blocks.push({ kind: 'paragraph', title: null, text: intro })

  while (i < lines.length) {
    const heading = lines[i].match(/^#{2,3}\s+(.*)/)
    if (!heading) {
      i++
      continue
    }
    const title = heading[1].trim()
    i++
    const bodyLines: string[] = []
    while (i < lines.length && !/^#{2,3}\s+/.test(lines[i])) {
      bodyLines.push(lines[i])
      i++
    }
    const body = bodyLines.join('\n').trim()

    if (/source|reference/i.test(title)) {
      const items = [...body.matchAll(/\[([^\]]+)\]\(([^)]+)\)/g)].map((m) => ({
        label: m[1],
        url: m[2],
      }))
      blocks.push({ kind: 'sources', title, items })
    } else if (/handles it/i.test(title)) {
      blocks.push({ kind: 'callout', title, text: body })
    } else {
      blocks.push({ kind: 'paragraph', title, text: body })
    }
  }

  return blocks
}

function sourceButtonLabel(label: string): string {
  const firstSegment = label.split(/[·|-]/)[0].trim()
  return `Open ${firstSegment || 'link'}`
}

function getMessageText(message: any): string {
  if (message.output && typeof message.output === 'string' && message.output.trim().length > 0) {
    return message.output
  }
  if (message.content && typeof message.content === 'string' && message.content.trim().length > 0) {
    return message.content
  }
  return ''
}

function getCleanMessages(messages: any[]): any[] {
  const seenIds = new Set<string>()
  const flat: any[] = []

  function traverse(list: any[]) {
    for (const msg of list) {
      if (!msg) continue
      const text = getMessageText(msg)
      if (text && text.trim().length > 0) {
        if (msg.id && !seenIds.has(msg.id)) {
          seenIds.add(msg.id)
          flat.push(msg)
        }
      }
      if (Array.isArray(msg.steps) && msg.steps.length > 0) {
        traverse(msg.steps)
      }
    }
  }

  traverse(messages)

  const result: any[] = []
  const seenAssistantOutputs = new Set<string>()

  for (const msg of flat) {
    const text = getMessageText(msg).trim()
    if (msg.type === 'user_message') {
      result.push(msg)
      seenAssistantOutputs.clear()
    } else {
      if (!seenAssistantOutputs.has(text)) {
        seenAssistantOutputs.add(text)
        result.push(msg)
      }
    }
  }

  return result
}

function AssistantCard({ content }: { content: string }) {
  if (!content || !content.trim()) return null

  const { badge, content: body } = extractBadge(content)
  const blocks = parseAssistantContent(body)

  return (
    <div className="assistant-card">
      <div className="assistant-card__header">
        <span className="assistant-card__name">Alfa Focus Assistant</span>
        {badge && <span className="assistant-card__badge">{badge}</span>}
      </div>

      <div className="assistant-card__body">
        {blocks.map((block, index) => {
          if (block.kind === 'callout') {
            return (
              <div className="assistant-card__callout" key={index}>
                <div className="assistant-card__callout-title">{block.title}</div>
                <p>{block.text}</p>
              </div>
            )
          }
          if (block.kind === 'sources') {
            return (
              <div className="assistant-card__sources" key={index}>
                <div className="assistant-card__sources-title">{block.title}</div>
                {block.items.map((item, itemIndex) => (
                  <a
                    key={itemIndex}
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="assistant-card__source-row"
                  >
                    <span>{item.label}</span>
                    <span className="assistant-card__source-btn">{sourceButtonLabel(item.label)}</span>
                  </a>
                ))}
              </div>
            )
          }
          return (
            <div className="assistant-card__paragraph" key={index}>
              {block.title && <div className="assistant-card__paragraph-title">{block.title}</div>}
              <p>{block.text}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function Chat() {
  const [searchParams] = useSearchParams()
  const threadId = searchParams.get('threadId') || undefined

  const { connect, disconnect } = useChatSession()
  const { connected, loading, error, disabled } = useChatData()
  const { messages } = useChatMessages()
  const { sendMessage } = useChatInteract()

  // 关键：存放从数据库抓取回来的历史消息状态
  const [historyMessages, setHistoryMessages] = useState<any[]>([])
  const [draft, setDraft] = useState('')
  const [selectedModel, setSelectedModel] = useState('gemini-3-8-flash')

  useEffect(() => {
    let unmounted = false

    // 1. 如果当前 URL 带有 threadId，主动去数据库拉取以前的对话记录
    if (threadId) {
      fetch(`/api/chat/threads/${threadId}/messages`, { credentials: 'include' })
        .then((res) => (res.ok ? res.json() : []))
        .then((data) => {
          if (!unmounted) {
            setHistoryMessages(data)
          }
        })
        .catch((err) => console.error('Failed to load thread messages:', err))
    } else {
      setHistoryMessages([])
    }

    // 2. 鉴权并重连 WebSocket
    fetch('/chat/auth/header', {
      method: 'POST',
      credentials: 'include',
    })
      .then((res) => {
        if (!res.ok) console.error('Chainlit header auth failed:', res.status)
      })
      .catch((err) => console.error('Chainlit header auth error:', err))
      .finally(() => {
        if (!unmounted) {
          connect({ userEnv: {}, threadId })
        }
      })

    return () => {
      unmounted = true
      disconnect()
    }
  }, [threadId])

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const content = draft.trim()
    if (!content) return

    sendMessage(
      {
        id: crypto.randomUUID(),
        name: 'user',
        type: 'user_message',
        output: content,
        createdAt: new Date().toISOString(),
        metadata: {
          model: selectedModel,
        },
      },
      [],
    )
    setDraft('')
  }

  // 关键：将数据库取回的历史消息与本次连接产生的新消息合并展示
  const allMessages = getCleanMessages([...historyMessages, ...messages])

  return (
    <Layout badge="Capstone Prototype">
      <div className="chat-page">
        <div className="chat-greeting">
          <h1>How can I help with SMSF guidance?</h1>
          <p>Ask about contribution caps, pensions, compliance and approved SMSF procedures.</p>
        </div>

        <div className="chat-status">
          {error && <span className="chat-status--error">Connection error!</span>}
          {!error && !connected && <span>Connecting…</span>}
        </div>

        <div className="chat-messages">
          {allMessages.map((message) => {
            const text = getMessageText(message)
            return message.type === 'user_message' ? (
              <div className="chat-message chat-message--user" key={message.id}>
                <div className="chat-message__label">You</div>
                <div className="chat-message__bubble">{text}</div>
              </div>
            ) : (
              <div className="chat-message chat-message--assistant" key={message.id}>
                <AssistantCard content={text} />
              </div>
            )
          })}
          {loading && <div className="chat-message chat-message--assistant chat-message--pending">…</div>}
        </div>

        <div className="chat-model-selector">
          <label htmlFor="model-select">AI Model</label>

          <select
            id="model-select"
            value={selectedModel}
            onChange={(event) => setSelectedModel(event.target.value)}
          >
            <option value="gemini-3-8-flash">Gemini 3.8 Flash</option>
            <option value="groq-gpt-oss-120b">Groq GPT-OSS 120B</option>
            <option value="openrouter-free">OpenRouter Free</option>
            <option value="free-fallback">Free Fallback</option>
          </select>
        </div>

        <form className="chat-composer" onSubmit={handleSubmit}>
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Ask an Accounting question…"
            disabled={disabled || !connected}
          />
          <button type="submit" className="chat-composer__send" disabled={disabled || !connected || !draft.trim()}>
            <i className="fas fa-arrow-right" />
          </button>
        </form>

        <div className="chat-warning">
          <i className="fas fa-exclamation-triangle" /> Do not enter client names, TFNs, member numbers or other
          identifying information.
        </div>
      </div>
    </Layout>
  )
}