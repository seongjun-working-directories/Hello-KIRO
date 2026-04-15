import type { ChatMessage, ComplianceItem } from '../types'

const statusColor: Record<string, string> = {
  Compliant: 'text-green-700 bg-green-50 border-green-200',
  'Partially Compliant': 'text-yellow-700 bg-amber-50 border-amber-200',
  'Non-Compliant': 'text-red-700 bg-red-50 border-red-200',
}

const statusLabel: Record<string, string> = {
  Compliant: '✅ 준수',
  'Partially Compliant': '⚠️ 부분 준수',
  'Non-Compliant': '❌ 미준수',
}

const priorityColor: Record<string, string> = {
  높음: 'text-red-600 bg-red-50',
  중간: 'text-amber-600 bg-amber-50',
  낮음: 'text-gray-500 bg-gray-50',
}

function ComplianceCard({ item }: { item: ComplianceItem }) {
  return (
    <div className={`border rounded-xl p-3 mt-2 text-xs ${statusColor[item.status] ?? ''}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium">{item.article_no} {item.title}</span>
        <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${priorityColor[item.priority] ?? ''}`}>
          {item.priority}
        </span>
      </div>
      <div className="text-xs mb-1">{statusLabel[item.status] ?? item.status}</div>
      {item.recommendation && (
        <div className="mt-1.5 text-xs text-gray-600 border-t border-current border-opacity-20 pt-1.5">
          💡 {item.recommendation}
        </div>
      )}
    </div>
  )
}

interface Props {
  message: ChatMessage
}

function formatTime(date: Date): string {
  const yy = String(date.getFullYear()).slice(2)
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const min = String(date.getMinutes()).padStart(2, '0')
  return `${yy}/${mm}/${dd} ${hh}:${min}`
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3 px-4`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-kb-yellow flex items-center justify-center mr-2 flex-shrink-0 mt-1">
          <span className="text-xs font-bold text-kb-navy">AI</span>
        </div>
      )}
      <div className="flex flex-col items-end max-w-[80%]">
        <div
          className={`rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap shadow-sm w-full ${
            isUser
              ? 'bg-[#FFB800] text-gray-900 rounded-br-sm'
              : 'bg-gray-100 text-gray-900 rounded-bl-sm'
          }`}
        >
          {message.content}
          {message.compliance_data && (
            <div className="mt-3">
              <div className={`text-xs font-medium px-2 py-1 rounded-lg inline-block mb-2 ${
                message.compliance_data.overall === 'Compliant'
                  ? 'bg-green-100 text-green-700'
                  : message.compliance_data.overall === 'Partially Compliant'
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-red-100 text-red-700'
              }`}>
                전체 등급: {statusLabel[message.compliance_data.overall] ?? message.compliance_data.overall}
              </div>
              {message.compliance_data.items.map((item, i) => (
                <ComplianceCard key={i} item={item} />
              ))}
            </div>
          )}
        </div>
        {isUser && message.timestamp && (
          <span className="text-xs text-gray-400 mt-1 mr-1">
            {formatTime(new Date(message.timestamp))}
          </span>
        )}
      </div>
    </div>
  )
}
