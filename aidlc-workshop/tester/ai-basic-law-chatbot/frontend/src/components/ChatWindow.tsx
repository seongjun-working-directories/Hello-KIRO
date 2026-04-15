import { useChatSession } from '../hooks/useChatSession'
import MessageList from './MessageList'
import LoadingIndicator from './LoadingIndicator'
import InputBar from './InputBar'
import CopyButton from './CopyButton'

export default function ChatWindow() {
  const { session, isStreaming, sendMessage, clearSession } = useChatSession()
  const hasMessages = session.messages.length > 0

  return (
    <div className="flex flex-col h-screen bg-white max-w-2xl mx-auto relative">

      {/* 헤더 */}
      <header className="flex-shrink-0 bg-[#FFB800] px-4 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <img src="/logo.png" alt="KB 로고" className="h-7 object-contain" />
          <span className="font-display font-medium text-[#1A1A2E] text-base leading-tight">
            AI 기본법<br />
            <span className="text-xs font-sans font-light">준수 확인 서비스</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          {hasMessages && (
            <CopyButton messages={session.messages} disabled={isStreaming} />
          )}
          {hasMessages && (
            <button
              className="text-xs text-[#1A1A2E] border border-[#1A1A2E] rounded-lg px-2.5 py-1.5 hover:bg-[#1A1A2E] hover:text-[#FFB800] transition-colors"
              onClick={clearSession}
              aria-label="새 대화 시작"
            >
              새 대화
            </button>
          )}
        </div>
      </header>

      {/* 면책 배너 */}
      <div className="flex-shrink-0 bg-amber-50 border-b border-amber-200 px-4 py-1.5 text-xs text-amber-800 text-center">
        본 결과는 참고용이며, 법적 효력이 없습니다. 정확한 법률 해석은 전문가에게 문의하세요.
      </div>

      {/* 메인 영역 */}
      <div className="flex-1 overflow-y-auto">
        {!hasMessages ? (
          <div className="flex flex-col items-center justify-start pt-6 px-4 pb-4">
            <img
              src="/visual_main_yuna2025.png"
              alt="AI 기본법 준수 확인"
              className="w-full max-w-xs object-contain mb-6"
            />
            <div className="w-full bg-gray-50 rounded-2xl p-4 text-center mb-4">
              <p className="font-display font-medium text-[#1A1A2E] text-base mb-2">
                AI 프로젝트, 법적으로 안전한가요?
              </p>
              <p className="text-sm text-gray-500 leading-relaxed">
                개발 중인 AI 서비스를 설명하고<br />
                <span className="font-medium text-[#1A1A2E]">"AI 기본법을 잘 준수한 건가요?"</span>라고 물어보세요.
              </p>
            </div>
            <div className="w-full space-y-2">
              {[
                '얼굴 인식 기반 출입 통제 시스템을 개발하려고 하는데, AI 기본법을 잘 준수한 건가요?',
                '대출 심사를 자동화하는 AI 시스템을 만들려고 하는데, AI 기본법을 잘 준수한 건가요?',
                '고객 상담 챗봇에 AI를 도입하려고 하는데, AI 기본법을 잘 준수한 건가요?',
              ].map((example) => (
                <button
                  key={example}
                  className="w-full text-left text-xs text-[#1A1A2E] bg-white border border-[#FFB800] rounded-xl px-3 py-2.5 hover:bg-amber-50 transition-colors"
                  onClick={() => sendMessage(example)}
                >
                  💬 {example}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <MessageList messages={session.messages} />
        )}
        {isStreaming && <LoadingIndicator />}
      </div>

      {/* 하단 입력바 */}
      <div className="flex-shrink-0 border-t border-gray-100 bg-white">
        <InputBar onSend={sendMessage} disabled={isStreaming} />
      </div>

    </div>
  )
}
