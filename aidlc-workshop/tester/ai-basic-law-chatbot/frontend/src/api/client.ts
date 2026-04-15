import type { ChatMessage } from '../types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export interface ChatRequestBody {
  message: string
  session_id: string
  history: Array<{ role: string; content: string }>
}

export async function sendChatMessage(body: ChatRequestBody): Promise<Response> {
  return fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function exportPDF(
  sessionId: string,
  messages: ChatMessage[],
  projectSummary: string,
): Promise<Blob> {
  const response = await fetch(`${BASE_URL}/api/chat/export-pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      messages: messages.map((m) => ({
        role: m.role,
        content: m.content,
        timestamp: m.timestamp.toISOString(),
        compliance_data: m.compliance_data,
      })),
      project_summary: projectSummary,
    }),
  })
  if (!response.ok) throw new Error('PDF 생성 실패')
  return response.blob()
}
