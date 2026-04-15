import { useState, type KeyboardEvent } from 'react'

const MAX_LENGTH = 5000

interface Props {
  onSend: (content: string) => void
  disabled: boolean
}

export default function InputBar({ onSend, disabled }: Props) {
  const [value, setValue] = useState('')
  const isOverLimit = value.length > MAX_LENGTH

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled || isOverLimit) return
    onSend(trimmed)
    setValue('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="px-3 py-3">
      {isOverLimit && (
        <p className="text-xs text-red-500 mb-1 px-1">
          입력이 {MAX_LENGTH.toLocaleString()}자를 초과했습니다. ({value.length}/{MAX_LENGTH})
        </p>
      )}
      <div className="flex gap-2 items-center bg-white border border-gray-200 rounded-2xl px-3 py-2 shadow-sm">
        <textarea
          className="flex-1 resize-none bg-transparent text-sm focus:outline-none text-gray-800 placeholder-gray-400 max-h-32"
          rows={1}
          placeholder="예) 저는 [하고자 하는 과업] 을 하려고 하는데, AI 기본법을 잘 준수한 건가요?"
          value={value}
          onChange={(e) => {
            setValue(e.target.value)
            // 자동 높이 조절
            e.target.style.height = 'auto'
            e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px'
          }}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          aria-label="메시지 입력"
        />
        <button
          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
            disabled || isOverLimit || !value.trim()
              ? 'bg-gray-300 cursor-not-allowed'
              : 'bg-kb-yellow hover:bg-kb-yellow-dark'
          }`}
          onClick={handleSend}
          disabled={disabled || isOverLimit || !value.trim()}
          aria-label="전송"
        >
          <svg className="w-4 h-4 text-kb-navy" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
          </svg>
        </button>
      </div>
    </div>
  )
}
