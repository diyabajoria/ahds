import { ReactNode } from 'react'

export function Panel({ title, children, className = '' }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <div className={`panel ${className}`}>
      {title && (
        <div className="border-b hairline px-4 py-2.5 text-[13px] tracking-wide text-slate-300">
          {title}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  )
}
