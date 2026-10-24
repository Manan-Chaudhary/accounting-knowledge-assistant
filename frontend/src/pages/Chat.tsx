
import { useChatData, useChatMessages, useChatSession } from '@chainlit/react-client'
import { type FormEvent, useEffect, useRef, useState } from 'react'
import { Layout } from '../components/Layout'
import { useSearchParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// --- Types ---------------------------------------------------------------

type ContentBlock =
  | { kind: 'paragraph'; title: string | null; text: string }
  | { kind: 'callout'; title: string; text: string }

type RetrievedSource = {
  number: number
  chunk_id: number | string
  document_id: number | string
  chunk_index: number
  content: string
  title: string
  filename: string
  url?: string | null
}

// --- Assistant message parsing ------------------------------------------

function extractBadge(raw: string): { badge: string | null; content: string } {
  const match = raw.match(/^>\s*badge:\s*(.+)$/m)

  if (!match) {
    return { badge: null, content: raw }
  }

  return {
    badge: match[1].trim(),
    content: raw.replace(match[0], '').trim(),
  }
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

  if (intro) {
    blocks.push({
      kind: 'paragraph',
      title: null,
      text: intro,
    })
  }

  while (i < lines.length) {
    const heading = lines[i].match(/^#{2,3}\s+(.*)/)

    if (!heading) {
      const text = lines[i]

      if (text.trim()) {
        blocks.push({
          kind: 'paragraph',
          title: null,
          text,
        })
      }

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

    if (/handles it/i.test(title)) {
      blocks.push({
        kind: 'callout',
        title,
        text: body,
      })
    } else {
      blocks.push({
        kind: 'paragraph',
        title,
        text: body,
      })
    }
  }

  return blocks
}

// --- Citation parsing ----------------------------------------------------
//
// Canonical markers: [1], [2]
// Also accepted: [1, 2], 【2】, 【2 additional text】
// Does not expand ranges such as [1-3].
// Markdown links, footnotes, checkboxes and code are preserved.

function remarkCitations() {
  return (tree: any) => {
    function visit(parent: any) {
      if (!Array.isArray(parent.children)) return

      const result: any[] = []

      for (const node of parent.children) {
        // Do not parse code, existing links, images or link references.
        if (
          [
            'inlineCode',
            'code',
            'link',
            'linkReference',
            'image',
            'imageReference',
          ].includes(node.type)
        ) {
          result.push(node)
          continue
        }

        if (node.type !== 'text' || typeof node.value !== 'string') {
          visit(node)
          result.push(node)
          continue
        }

        const value: string = node.value
        const pattern = /\[(\d+(?:\s*,\s*\d+)*)\]|【\s*(\d+)[^】]*】/g

        let lastIndex = 0
        let match: RegExpExecArray | null
        let changed = false

        while ((match = pattern.exec(value)) !== null) {
          const numbers = match[1]
            ? match[1].split(',').map((part) => Number(part.trim()))
            : [Number(match[2])]

          // A legal case citation such as [2019] HCA 12 is not a marker.
          const followingText = value.slice(pattern.lastIndex)

          if (
            numbers.length === 1 &&
            /^\s*(?:HCA|FCA|FCAFC|NSWCA|VSCA|CLR)\b/i.test(followingText)
          ) {
            continue
          }

          if (match.index > lastIndex) {
            result.push({
              type: 'text',
              value: value.slice(lastIndex, match.index),
            })
          }

          for (const number of numbers) {
            result.push({
              type: 'link',
              url: `citation-source:${number}`,
              children: [
                {
                  type: 'text',
                  value: `[${number}]`,
                },
              ],
            })
          }

          lastIndex = pattern.lastIndex
          changed = true
        }

        if (!changed) {
          result.push(node)
        } else if (lastIndex < value.length) {
          result.push({
            type: 'text',
            value: value.slice(lastIndex),
          })
        }
      }

      parent.children = result
    }

    visit(tree)
  }
}

// Hide an incomplete citation only at the end of a live stream.
// Once streaming ends, the original text is shown again.
function hideIncompleteCitationTail(text: string): string {
  return text.replace(
    /(?:\[(?:\d+(?:\s*,\s*\d*)*)?|【\s*\d*[^】]*)$/,
    '',
  )
}

// --- Markdown renderer ---------------------------------------------------

function MarkdownBody({
  text,
  sources,
  sourcesReady,
  isStreaming,
}: {
  text: string
  sources: RetrievedSource[]
  sourcesReady: boolean
  isStreaming: boolean
}) {
  const displayText = isStreaming
    ? hideIncompleteCitationTail(text)
    : text

  return (
    <div className="assistant-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkCitations]}
        components={{
          a: ({ href, children }) => {
            const match = href?.match(/^citation-source:(\d+)$/)

            // Preserve normal Markdown links.
            if (!match) {
              return (
                <a href={href} target="_blank" rel="noopener noreferrer">
                  {children}
                </a>
              )
            }

            const number = Number(match[1])
            const source = sources.find((item) => item.number === number)

            // A completed marker may arrive before its source list.
            if (!sourcesReady && isStreaming) {
              return (
                <span
                  className="citation-chip citation-chip--pending"
                  title="Waiting for retrieved sources"
                >
                  {children}
                </span>
              )
            }

            // Historical messages without source metadata stay as plain text.
            if (!sourcesReady) {
              return <span>{children}</span>
            }

            // Only an actual numbered source entry can resolve a citation.
            if (!source || number < 1) {
              return (
                <span
                  className="citation-chip citation-chip--unmatched"
                  title="No matching retrieved source"
                >
                  [{number}?]
                </span>
              )
            }

            return (
              <span
                className="citation-chip"
                title={source.title || source.filename || `Source ${number}`}
                aria-label={`Citation ${number}: ${source.title || source.filename || 'Retrieved source'}`}
              >
                {children}
              </span>
            )
          },
        }}
      >
        {displayText}
      </ReactMarkdown>
    </div>
  )
}

// --- Message helpers -----------------------------------------------------

function getMessageText(message: any): string {
  if (
    message.output &&
    typeof message.output === 'string' &&
    message.output.trim().length > 0
  ) {
    return message.output
  }

  if (
    message.content &&
    typeof message.content === 'string' &&
    message.content.trim().length > 0
  ) {
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
    } else if (!seenAssistantOutputs.has(text)) {
      seenAssistantOutputs.add(text)
      result.push(msg)
    }
  }

  return result
}

// --- Assistant card ------------------------------------------------------

function AssistantCard({
  content,
  sources,
  sourcesReady,
  isStreaming,
}: {
  content: string
  sources: RetrievedSource[]
  sourcesReady: boolean
  isStreaming: boolean
}) {
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
                <div className="assistant-card__callout-title">
                  {block.title}
                </div>

                <MarkdownBody
                  text={block.text}
                  sources={sources}
                  sourcesReady={sourcesReady}
                  isStreaming={isStreaming}
                />
              </div>
            )
          }

          return (
            <div className="assistant-card__paragraph" key={index}>
              {block.title && (
                <div className="assistant-card__paragraph-title">
                  {block.title}
                </div>
              )}

              <MarkdownBody
                text={block.text}
                sources={sources}
                sourcesReady={sourcesReady}
                isStreaming={isStreaming}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}

// --- Chat page -----------------------------------------------------------

export function Chat() {
  const [searchParams, setSearchParams] = useSearchParams()
  const threadId = searchParams.get('threadId') || undefined

  const { connect, disconnect } = useChatSession()
  const { connected, disabled } = useChatData()
  const { messages } = useChatMessages()

  const [historyMessages, setHistoryMessages] = useState<any[]>([])
  const [draft, setDraft] = useState('')
  const [selectedModel, setSelectedModel] = useState('gemini-3-8-flash')

  const [localMessages, setLocalMessages] = useState<any[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [streamError, setStreamError] = useState<string | null>(null)

  const abortControllerRef = useRef<AbortController | null>(null)

  const [messageSources, setMessageSources] = useState<
    Record<string, RetrievedSource[]>
  >({})

  useEffect(() => {
    let unmounted = false

    setLocalMessages([])
    setMessageSources({})

    if (threadId) {
      fetch(`/api/chat/threads/${threadId}/messages`, {
        credentials: 'include',
      })
        .then((res) => (res.ok ? res.json() : []))
        .then((data) => {
          if (!unmounted) {
            setHistoryMessages(data)
          }
        })
        .catch((err) => {
          console.error('Failed to load thread messages:', err)
        })
    } else {
      setHistoryMessages([])
    }

    fetch('/chat/auth/header', {
      method: 'POST',
      credentials: 'include',
    })
      .then((res) => {
        if (!res.ok) {
          console.error('Chainlit header auth failed:', res.status)
        }
      })
      .catch((err) => {
        console.error('Chainlit header auth error:', err)
      })
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

  const handleStopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
      setIsStreaming(false)
      setIsLoading(false)
    }
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()

    const content = draft.trim()
    if (!content || isStreaming) return

    const userMessage = {
      id: crypto.randomUUID(),
      name: 'user',
      type: 'user_message',
      output: content,
      createdAt: new Date().toISOString(),
    }

    const assistantMsgId = crypto.randomUUID()

    const placeholderAssistantMessage = {
      id: assistantMsgId,
      name: 'Alfa Focus Assistant',
      type: 'assistant_message',
      output: '',
      createdAt: new Date().toISOString(),
    }

    setLocalMessages((prev) => [
      ...prev,
      userMessage,
      placeholderAssistantMessage,
    ])
    setDraft('')
    setIsLoading(true)
    setIsStreaming(true)
    setStreamError(null)

    abortControllerRef.current = new AbortController()

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          message: content,
          model: selectedModel,
          thread_id: threadId,
        }),
        signal: abortControllerRef.current.signal,
      })

      if (!response.ok) {
        throw new Error(
          `Streaming endpoint returned status ${response.status}`,
        )
      }

      setIsLoading(false)

      const reader = response.body?.getReader()
      const decoder = new TextDecoder('utf-8')

      let accumulatedOutput = ''
      let buffer = ''
      let streamFinished = false

      if (reader) {
        while (!streamFinished) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue

            const dataStr = line.slice(6).trim()

            if (dataStr === '[DONE]') {
              streamFinished = true
              break
            }

            try {
              const parsed = JSON.parse(dataStr)

              if (parsed.thread_id && !threadId) {
                setSearchParams(
                  { threadId: parsed.thread_id },
                  { replace: true },
                )
              }

              if (typeof parsed.token === 'string') {
                setIsLoading(false)
                accumulatedOutput += parsed.token

                setLocalMessages((prev) =>
                  prev.map((message) =>
                    message.id === assistantMsgId
                      ? { ...message, output: accumulatedOutput }
                      : message,
                  ),
                )
              }

              if (Array.isArray(parsed.sources)) {
                setMessageSources((prev) => ({
                  ...prev,
                  [assistantMsgId]: parsed.sources,
                }))
              }

              if (parsed.error) {
                setStreamError('The assistant encountered a streaming error.')
              }
            } catch {
              // Ignore malformed SSE data rather than treating JSON fragments
              // as assistant output.
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setLocalMessages((prev) =>
          prev.map((message) =>
            message.id === assistantMsgId
              ? {
                ...message,
                output:
                  (message.output || '') +
                  '\n\n*(Generation stopped by user)*',
              }
              : message,
          ),
        )
        return
      }

      console.warn(
        'Streaming unavailable, falling back to standard endpoint...',
        err,
      )

      try {
        const fallbackRes = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            message: content,
            model: selectedModel,
            thread_id: threadId,
          }),
        })

        if (!fallbackRes.ok) {
          throw new Error('Fallback failed')
        }

        const fallbackData = await fallbackRes.json()

        const fullOutput =
          fallbackData.output ||
          fallbackData.message ||
          fallbackData.answer ||
          ''

        setLocalMessages((prev) =>
          prev.map((message) =>
            message.id === assistantMsgId
              ? { ...message, output: fullOutput }
              : message,
          ),
        )
      } catch (fallbackError) {
        console.error('Chat fallback failed:', fallbackError)
        setStreamError('Failed to generate response. Please try again.')

        setLocalMessages((prev) =>
          prev.map((message) =>
            message.id === assistantMsgId
              ? {
                ...message,
                output: 'Error: Failed to generate response from server.',
              }
              : message,
          ),
        )
      }
    } finally {
      setIsLoading(false)
      setIsStreaming(false)
      abortControllerRef.current = null
    }
  }

  const allMessages = getCleanMessages([
    ...historyMessages,
    ...messages,
    ...localMessages,
  ])

  return (
    <Layout badge="Capstone Prototype">
      <div className="chat-page">
        <div className="chat-greeting">
          <h1>How can I help with SMSF guidance?</h1>
          <p>
            Ask about contribution caps, pensions, compliance and approved SMSF
            procedures.
          </p>
        </div>

        <div className="chat-status">
          {streamError && (
            <span className="chat-status--error">{streamError}</span>
          )}
          {!streamError && !connected && <span>Connecting…</span>}
        </div>

        <div className="chat-messages">
          {allMessages.map((message) => {
            const text = getMessageText(message)

            if (message.type === 'user_message') {
              return (
                <div
                  className="chat-message chat-message--user"
                  key={message.id}
                >
                  <div className="chat-message__label">You</div>
                  <div className="chat-message__bubble">{text}</div>
                </div>
              )
            }

            const sourcesReady = Object.prototype.hasOwnProperty.call(
              messageSources,
              message.id,
            )

            const messageIsStreaming =
              isStreaming &&
              localMessages.some((item) => item.id === message.id)

            return (
              <div
                className="chat-message chat-message--assistant"
                key={message.id}
              >
                <AssistantCard
                  content={text}
                  sources={messageSources[message.id] ?? []}
                  sourcesReady={sourcesReady}
                  isStreaming={messageIsStreaming}
                />
              </div>
            )
          })}

          {isLoading && (
            <div className="chat-message chat-message--assistant chat-message--pending">
              …
            </div>
          )}
        </div>

        <div className="chat-model-selector">
          <label htmlFor="model-select">AI Model</label>

          <select
            id="model-select"
            value={selectedModel}
            onChange={(event) => setSelectedModel(event.target.value)}
            disabled={isStreaming}
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
            disabled={disabled || isStreaming}
          />

          {isStreaming ? (
            <button
              type="button"
              className="chat-composer__send chat-composer__stop"
              onClick={handleStopGenerating}
              title="Stop Generating"
              style={{ backgroundColor: '#dc2626', color: '#fff' }}
            >
              <i className="fas fa-stop" />
            </button>
          ) : (
            <button
              type="submit"
              className="chat-composer__send"
              disabled={disabled || !draft.trim()}
            >
              <i className="fas fa-arrow-right" />
            </button>
          )}
        </form>

        <div className="chat-warning">
          <i className="fas fa-exclamation-triangle" /> Do not enter client
          names, TFNs, member numbers or other identifying information.
        </div>
      </div>
    </Layout>
  )
}
