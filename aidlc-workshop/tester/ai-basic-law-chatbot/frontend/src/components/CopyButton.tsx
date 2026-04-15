import { useState } from 'react'
import type { ChatMessage } from '../types'

interface Props {
  messages: ChatMessage[]
  disabled: boolean
}

function formatMessages(messages: ChatMessage[]): string {
  const lines: string[] = [
    'AI 기본법 준수 확인 결과',
    `분석 일시: ${new Date().toLocaleString('ko-KR')}`,
    '─'.repeat(40),
    '',
  ]

  for (const msg of messages) {
    if (msg.role === 'user') {
      lines.push(`[질문]`)
      lines.push(msg.content)
    } else {
      lines.push(`[AI 분석]`)
      lines.push(msg.content)
      if (msg.compliance_data) {
        lines.push('')
        lines.push(`전체 등급: ${msg.compliance_data.overall}`)
        for (const item of msg.compliance_data.items) {
          lines.push(`  • ${item.article_no} ${item.title} [${item.priority}] - ${item.status}`)
          if (item.recommendation) {
            lines.push(`    권고: ${item.recommendation}`)
          }
        }
      }
    }
    lines.push('')
  }

  lines.push('─'.repeat(40))
  lines.push('본 결과는 참고용이며, 법적 효력이 없습니다. 정확한 법률 해석은 전문가에게 문의하세요.')
  return lines.join('\n')
}

export default function CopyButton({ messages, disabled }: Props) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    if (disabled || copied) return
    try {
      await navigator.clipboard.writeText(formatMessages(messages))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback for older browsers
      const el = document.createElement('textarea')
      el.value = formatMessages(messages)
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <button
      className="text-xs text-kb-navy border border-kb-navy rounded-lg px-2.5 py-1.5 hover:bg-kb-navy hover:text-kb-yellow transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      onClick={handleCopy}
      disabled={disabled}
      aria-label="대화 내용 복사"
    >
      {copied ? '✓ 복사됨' : '복사'}
    </button>
  )
}
