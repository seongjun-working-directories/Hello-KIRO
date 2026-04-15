export default function LoadingIndicator() {
  return (
    <div className="flex justify-start px-4 mb-3" aria-label="분석 중">
      <div className="w-7 h-7 rounded-full bg-kb-yellow flex items-center justify-center mr-2 flex-shrink-0">
        <span className="text-xs font-bold text-kb-navy">AI</span>
      </div>
      <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 flex gap-1.5 items-center">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-2 h-2 bg-kb-yellow rounded-full animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
        <span className="text-xs text-gray-400 ml-1">분석 중...</span>
      </div>
    </div>
  )
}
