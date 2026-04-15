/**
 * Feature: ai-basic-law-chatbot, Property 1 (프론트엔드): 입력 길이 경계 검증
 * Validates: Requirements 1.3, 1.4
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import InputBar from './InputBar'

describe('InputBar - Property 1: 입력 길이 경계 검증', () => {
  it('5000자 이하 입력 시 전송 버튼이 활성화된다', () => {
    render(<InputBar onSend={vi.fn()} disabled={false} />)
    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: '가'.repeat(5000) } })
    const button = screen.getByRole('button', { name: '전송' })
    expect(button).not.toBeDisabled()
  })

  it('5001자 이상 입력 시 전송 버튼이 비활성화된다', () => {
    render(<InputBar onSend={vi.fn()} disabled={false} />)
    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: '가'.repeat(5001) } })
    const button = screen.getByRole('button', { name: '전송' })
    expect(button).toBeDisabled()
  })

  it('5001자 이상 입력 시 경고 메시지가 표시된다', () => {
    render(<InputBar onSend={vi.fn()} disabled={false} />)
    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: '가'.repeat(5001) } })
    // 경고 문구가 포함된 p 태그 확인
    const warning = document.querySelector('p.text-red-500')
    expect(warning).not.toBeNull()
  })

  it('isStreaming=true 이면 입력과 버튼이 비활성화된다', () => {
    render(<InputBar onSend={vi.fn()} disabled={true} />)
    const textarea = screen.getByRole('textbox')
    const button = screen.getByRole('button', { name: '전송' })
    expect(textarea).toBeDisabled()
    expect(button).toBeDisabled()
  })

  it('5000자 경계값 테스트: 4999, 5000은 허용, 5001은 차단', () => {
    const cases = [
      { len: 4999, shouldBlock: false },
      { len: 5000, shouldBlock: false },
      { len: 5001, shouldBlock: true },
    ]

    for (const { len, shouldBlock } of cases) {
      const { unmount } = render(<InputBar onSend={vi.fn()} disabled={false} />)
      const textarea = screen.getByRole('textbox')
      fireEvent.change(textarea, { target: { value: '가'.repeat(len) } })
      const button = screen.getByRole('button', { name: '전송' })
      if (shouldBlock) {
        expect(button).toBeDisabled()
      } else {
        expect(button).not.toBeDisabled()
      }
      unmount()
    }
  })
})
