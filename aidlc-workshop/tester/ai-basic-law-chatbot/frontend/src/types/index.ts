export type MessageRole = 'user' | 'assistant'

export type ComplianceStatus = 'Compliant' | 'Partially Compliant' | 'Non-Compliant'
export type Priority = '높음' | '중간' | '낮음'

export interface ComplianceItem {
  article_no: string
  title: string
  status: ComplianceStatus
  priority: Priority
  recommendation?: string
  article_summary?: string
}

export interface ComplianceData {
  overall: ComplianceStatus
  items: ComplianceItem[]
  disclaimer: string
}

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  timestamp: Date
  compliance_data?: ComplianceData
}

export interface ChatSession {
  sessionId: string
  messages: ChatMessage[]
  createdAt: Date
  lastActiveAt: Date
}
