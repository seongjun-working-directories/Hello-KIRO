import { useEffect, useRef } from 'react'
import type { ChatMessage } from '../types'
import MessageBubble from './MessageBubble'

interface Props {
  messages: ChatMessage[]
}

export default function MessageList({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sorted = [...messages].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4">
      {sorted.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
