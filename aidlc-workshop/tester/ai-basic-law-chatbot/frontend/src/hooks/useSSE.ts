import type { ComplianceData } from '../types'

interface SSEOptions {
  onChunk: (chunk: string) => void
  onDone: (content: string, complianceData?: ComplianceData) => void
  onError: (error: string) => void
}

export function useSSE(options: SSEOptions) {
  const sendRequest = async (url: string, body: object): Promise<void> => {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      options.onError(data?.detail?.detail || '요청 처리 중 오류가 발생했습니다.')
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      options.onError('스트림을 읽을 수 없습니다.')
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const raw = line.slice(6).trim()
        if (raw === '[DONE]') return

        try {
          const event = JSON.parse(raw)
          if (event.type === 'chunk') {
            options.onChunk(event.content)
          } else if (event.type === 'done') {
            options.onDone(event.content, event.compliance_data)
          } else if (event.type === 'error') {
            options.onError(event.message)
          }
        } catch {
          // ignore parse errors
        }
      }
    }
  }

  return { sendRequest }
}
