import { useState, useCallback, useEffect } from 'react'
import { v4 as uuidv4 } from 'uuid'
import type { ChatSession, ChatMessage, ComplianceData } from '../types'
import { useSSE } from './useSSE'

const SESSION_KEY = 'chat_session'
const TIMEOUT_MS = Number(import.meta.env.VITE_SESSION_TIMEOUT_MS) || 1_800_000
const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

function createSession(): ChatSession {
  const now = new Date()
  return { sessionId: uuidv4(), messages: [], createdAt: now, lastActiveAt: now }
}

function loadSession(): ChatSession {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    if (!raw) return createSession()
    const parsed = JSON.parse(raw)
    const lastActive = new Date(parsed.lastActiveAt)
    if (Date.now() - lastActive.getTime() > TIMEOUT_MS) return createSession()
    return {
      ...parsed,
      createdAt: new Date(parsed.createdAt),
      lastActiveAt: lastActive,
      messages: parsed.messages.map((m: ChatMessage) => ({
        ...m,
        timestamp: new Date(m.timestamp),
      })),
    }
  } catch {
    return createSession()
  }
}

function saveSession(session: ChatSession) {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export interface UseChatSessionReturn {
  session: ChatSession
  isStreaming: boolean
  sendMessage: (content: string) => Promise<void>
  clearSession: () => void
}

export function useChatSession(): UseChatSessionReturn {
  const [session, setSession] = useState<ChatSession>(loadSession)
  const [isStreaming, setIsStreaming] = useState(false)

  useEffect(() => {
    saveSession(session)
  }, [session])

  const updateSession = useCallback((updater: (s: ChatSession) => ChatSession) => {
    setSession((prev) => {
      const next = updater(prev)
      saveSession(next)
      return next
    })
  }, [])

  const { sendRequest } = useSSE({
    onChunk: (chunk) => {
      updateSession((s) => {
        const msgs = [...s.messages]
        const last = msgs[msgs.length - 1]
        if (last?.role === 'assistant' && last.id === 'streaming') {
          msgs[msgs.length - 1] = { ...last, content: last.content + chunk }
        }
        return { ...s, messages: msgs }
      })
    },
    onDone: (_content, complianceData?: ComplianceData) => {
      let updatedSession: ChatSession | null = null
      updateSession((s) => {
        const msgs = s.messages.map((m) =>
          m.id === 'streaming'
            ? { ...m, id: uuidv4(), compliance_data: complianceData }
            : m,
        )
        updatedSession = { ...s, messages: msgs, lastActiveAt: new Date() }
        return updatedSession
      })

      // updateSession 밖에서 한 번만 호출
      setTimeout(() => {
        if (!updatedSession) return
        const allMsgs = (updatedSession as ChatSession).messages.filter((m) => m.id !== 'streaming')
        fetch(`${BASE_URL}/api/chat/log`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: (updatedSession as ChatSession).sessionId,
            messages: allMsgs.map((m) => ({ role: m.role, content: m.content })),
          }),
        }).catch((e) => console.warn('로그 저장 실패:', e))
      }, 0)

      setIsStreaming(false)
    },
    onError: (error) => {
      updateSession((s) => {
        const msgs = s.messages.map((m) =>
          m.id === 'streaming' ? { ...m, id: uuidv4(), content: `오류: ${error}` } : m,
        )
        return { ...s, messages: msgs }
      })
      setIsStreaming(false)
    },
  })

  const sendMessage = useCallback(
    async (content: string) => {
      if (isStreaming) return

      const userMsg: ChatMessage = {
        id: uuidv4(),
        role: 'user',
        content,
        timestamp: new Date(),
      }
      const assistantPlaceholder: ChatMessage = {
        id: 'streaming',
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      }

      let currentSession: ChatSession = session
      updateSession((s) => {
        currentSession = {
          ...s,
          messages: [...s.messages, userMsg, assistantPlaceholder],
          lastActiveAt: new Date(),
        }
        return currentSession
      })

      setIsStreaming(true)

      const history = currentSession.messages
        .filter((m) => m.id !== 'streaming' && m.id !== userMsg.id)
        .slice(-40)
        .map((m) => ({ role: m.role, content: m.content }))

      await sendRequest(`${BASE_URL}/api/chat`, {
        message: content,
        session_id: currentSession.sessionId,
        history,
      })
    },
    [isStreaming, session, sendRequest, updateSession],
  )

  const clearSession = useCallback(() => {
    const newSession = createSession()
    setSession(newSession)
    saveSession(newSession)
  }, [])

  return { session, isStreaming, sendMessage, clearSession }
}
