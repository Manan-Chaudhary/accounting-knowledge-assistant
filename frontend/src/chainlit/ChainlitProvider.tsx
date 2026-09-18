import { ChainlitContext } from '@chainlit/react-client'
import type { ReactNode } from 'react'
import { RecoilRoot } from 'recoil'
import { chainlitClient } from './client'

export function ChainlitProvider({ children }: { children: ReactNode }) {
  return (
    <RecoilRoot>
      <ChainlitContext.Provider value={chainlitClient}>{children}</ChainlitContext.Provider>
    </RecoilRoot>
  )
}
