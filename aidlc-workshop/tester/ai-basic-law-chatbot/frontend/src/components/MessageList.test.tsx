/**
 * Feature: ai-basic-law-chatbot, Property 9: 메시지 순서 보존
 * Validates: Requirements 8.3
 */
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import MessageList from './MessageList'
import type { ChatMessage } from '../types'

function makeMsg(id: string, role: 'user' | 'assistant', offsetMs: number): ChatMessage {
  return {
    id,
    role,
    content: `message-${id}`,
    timestamp: new Date(1000000 + offsetMs),
  }
}

describe('MessageList - Property 9: 메시지 순서 보존', () => {
  it('timestamp 오름차순으로 렌더링된다', () => {
    const messages: ChatMessage[] = [
      makeMsg('c', 'assistant', 3000),
      makeMsg('a', 'user', 1000),
      makeMsg('b', 'assistant', 2000),
    ]

    render(<MessageList messages={messages} />)

    const bubbles = screen.getAllByText(/^message-/)
    expect(bubbles[0].textContent).toBe('message-a')
    expect(bubbles[1].textContent).toBe('message-b')
    expect(bubbles[2].textContent).toBe('message-c')
  })

  it('이미 정렬된 메시지도 순서가 유지된다', () => {
    const messages: ChatMessage[] = [
      makeMsg('x', 'user', 100),
      makeMsg('y', 'assistant', 200),
      makeMsg('z', 'user', 300),
    ]

    render(<MessageList messages={messages} />)

    const bubbles = screen.getAllByText(/^message-/)
    expect(bubbles[0].textContent).toBe('message-x')
    expect(bubbles[1].textContent).toBe('message-y')
    expect(bubbles[2].textContent).toBe('message-z')
  })

  it('사용자 메시지와 어시스턴트 메시지가 시각적으로 구분된다', () => {
    const messages: ChatMessage[] = [
      makeMsg('u1', 'user', 100),
      makeMsg('a1', 'assistant', 200),
    ]

    const { container } = render(<MessageList messages={messages} />)

    // user: justify-end, assistant: justify-start
    const userBubble = container.querySelector('.justify-end')
    const assistantBubble = container.querySelector('.justify-start')
    expect(userBubble).not.toBeNull()
    expect(assistantBubble).not.toBeNull()
  })

  it('빈 메시지 배열이면 아무것도 렌더링하지 않는다', () => {
    const { container } = render(<MessageList messages={[]} />)
    expect(container.querySelectorAll('[class*="rounded-2xl"]').length).toBe(0)
  })
})
