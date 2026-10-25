import { useState } from 'react'
import { CameraPanel } from './components/CameraPanel'

type Tab = 'translate' | 'train'

export default function App() {
  const [tab, setTab] = useState<Tab>('translate')

  return (
    <div className="mx-auto flex min-h-svh max-w-6xl flex-col gap-4 p-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">SignBridge</h1>
          <p className="text-base text-white/70">ISL signs → text + speech (hackathon demo)</p>
        </div>
        <nav className="flex gap-2" aria-label="Main">
          <TabButton active={tab === 'translate'} onClick={() => setTab('translate')}>
            Translate
          </TabButton>
          <TabButton active={tab === 'train'} onClick={() => setTab('train')}>
            Train
          </TabButton>
        </nav>
      </header>

      {tab === 'translate' ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <CameraPanel />
          <section className="rounded-2xl border-2 border-dashed border-white/20 bg-[#12151c] p-4 text-white/70">
            <h2 className="text-xl font-semibold text-white">Gloss + speech</h2>
            <p className="mt-2 text-base">Step 2–4: train a classifier, build a gloss, then polish with Gemma.</p>
          </section>
        </div>
      ) : (
        <section className="rounded-2xl border-2 border-dashed border-white/20 bg-[#12151c] p-6 text-white/80">
          <h2 className="text-2xl font-semibold text-white">Train</h2>
          <p className="mt-2 text-lg">
            Next step: pick a label, hold a sign, capture ~50 frames, save, and retrain k-NN in the browser.
          </p>
        </section>
      )}

      <section className="mt-auto rounded-2xl border-2 border-dashed border-white/20 bg-[#12151c] p-4">
        <h2 className="text-xl font-semibold text-white">Hearing person reply</h2>
        <p className="mt-2 text-lg text-white/70">Step 5: type, speak, or tap a quick reply. Shown in large text.</p>
      </section>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? 'page' : undefined}
      className={`min-h-12 rounded-xl px-5 text-base font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-yellow-400 ${
        active ? 'bg-yellow-400 text-black' : 'bg-white/10 text-white hover:bg-white/20'
      }`}
    >
      {children}
    </button>
  )
}
