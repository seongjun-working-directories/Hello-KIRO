import { useState } from 'react'

interface Props {
  onExport: () => Promise<void>
  disabled: boolean
}

export default function ExportButton({ onExport, disabled }: Props) {
  const [loading, setLoading] = useState(false)

  const handleClick = async () => {
    if (disabled || loading) return
    setLoading(true)
    try {
      await onExport()
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      className="text-xs text-kb-navy border border-kb-navy rounded-lg px-2.5 py-1.5 hover:bg-kb-navy hover:text-kb-yellow transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      onClick={handleClick}
      disabled={disabled || loading}
      aria-label="PDF 내보내기"
    >
      {loading ? '생성 중...' : 'PDF'}
    </button>
  )
}
