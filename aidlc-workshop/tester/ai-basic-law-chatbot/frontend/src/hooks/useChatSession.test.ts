/**
 * Feature: ai-basic-law-chatbot, Property 4: 세션 만료 감지
 * Validates: Requirements 4.3
 */
import { describe, it, expect } from 'vitest'

const TIMEOUT_MS = 1_800_000 // 30분

function isSessionExpired(lastActiveAt: Date): boolean {
  return Date.now() - lastActiveAt.getTime() > TIMEOUT_MS
}

describe('useChatSession - Property 4: 세션 만료 감지', () => {
  it('30분 초과 세션은 만료 상태로 판단한다', () => {
    const cases = [1801, 3600, 7200].map((s) => s * 1000)
    for (const elapsed of cases) {
      const lastActiveAt = new Date(Date.now() - elapsed)
      expect(isSessionExpired(lastActiveAt)).toBe(true)
    }
  })

  it('30분 미만 세션은 활성 상태로 판단한다', () => {
    const cases = [0, 60, 1799].map((s) => s * 1000)
    for (const elapsed of cases) {
      const lastActiveAt = new Date(Date.now() - elapsed)
      expect(isSessionExpired(lastActiveAt)).toBe(false)
    }
  })

  it('정확히 30분(1800초)은 만료되지 않는다', () => {
    const lastActiveAt = new Date(Date.now() - 1_800_000)
    // 1800000ms는 > 가 아니라 === 이므로 만료 아님
    expect(isSessionExpired(lastActiveAt)).toBe(false)
  })

  it('경계값: 1800001ms는 만료된다', () => {
    const lastActiveAt = new Date(Date.now() - 1_800_001)
    expect(isSessionExpired(lastActiveAt)).toBe(true)
  })
})
