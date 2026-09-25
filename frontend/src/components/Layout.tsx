import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'

export function Layout({ badge, children }: { badge: string; children: ReactNode }) {
  return (
    <>
      <Sidebar />
      <main className="main-content">
        <header className="header">
          <div className="badge">{badge}</div>
        </header>
        {children}
      </main>
    </>
  )
}
