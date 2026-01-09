import React, { useEffect, useMemo, useState } from 'react'

type Choice = {
  choiceId: string
  text: string
  moveType?: string
  weight?: number
  guards?: string[]
  effects?: string[]
  to: string
}

type NodeT = {
  nodeId: string
  narration: string
  image?: string
  choices: Choice[]
}

type EndingT = {
  endingId: string
  title: string
  type: 'success' | 'mixed' | 'failure' | 'twist'
  narration: string
  image?: string
  weight?: number
}

type InitialState = {
  tags?: string[]
  stats?: Record<string, number>
  facts?: Record<string, string>
  goals?: Record<string, number>
}

type Scene = {
  sceneId: string
  variantId: string
  intro: { narration: string }
  nodes: NodeT[]
  endings: EndingT[]
  initialState?: InitialState
}

type RuntimeState = {
  tags: Set<string>
  stats: Record<string, number>
  facts: Record<string, string>
  goals: Record<string, number>
}

function cloneState(s: RuntimeState): RuntimeState {
  return {
    tags: new Set(s.tags),
    stats: { ...s.stats },
    facts: { ...s.facts },
    goals: { ...s.goals },
  }
}

function cmp(op: string, left: number, right: number): boolean {
  switch (op) {
    case '==':
      return left === right
    case '!=':
      return left !== right
    case '>=':
      return left >= right
    case '<=':
      return left <= right
    case '>':
      return left > right
    case '<':
      return left < right
    default:
      return false
  }
}

function canTakeGuard(state: RuntimeState, guardRaw: string): boolean {
  const g = guardRaw.trim()
  if (!g) return true

  // Back-compat: bare tag or !tag
  if (!g.includes(':')) {
    if (g.startsWith('!')) return !state.tags.has(g.slice(1))
    return state.tags.has(g)
  }

  const mNs = g.match(/^(tag|stat|goal|fact):(.*)$/)
  if (!mNs) return false
  const ns = mNs[1]
  const rest = mNs[2].trim()

  if (ns === 'tag') {
    if (rest.startsWith('!')) return !state.tags.has(rest.slice(1))
    return state.tags.has(rest)
  }

  if (ns === 'stat' || ns === 'goal') {
    const m = rest.match(/^([A-Za-z_][\w\.]*)\s*(==|!=|>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)$/)
    if (!m) return false
    const key = m[1]
    const op = m[2]
    const rhs = Number(m[3])
    const lhs = (ns === 'stat' ? state.stats[key] : state.goals[key]) ?? 0
    return cmp(op, lhs, rhs)
  }

  if (ns === 'fact') {
    // fact:key (truthy) or fact:key==verified
    const mCmp = rest.match(/^([A-Za-z_][\w\.]*)\s*(==|!=)\s*([A-Za-z_][\w\-]*)$/)
    if (mCmp) {
      const key = mCmp[1]
      const op = mCmp[2]
      const rhs = mCmp[3]
      const lhs = state.facts[key] ?? 'unknown'
      return op === '==' ? lhs === rhs : lhs !== rhs
    }
    const key = rest
    const v = state.facts[key] ?? 'unknown'
    return v === 'verified' || v === 'true'
  }

  return false
}

function applyEffect(state: RuntimeState, effRaw: string): RuntimeState {
  const eff = effRaw.trim()
  if (!eff) return state

  const next = cloneState(state)

  // Back-compat: !tag clears
  if (!eff.includes(':')) {
    if (eff.startsWith('!')) next.tags.delete(eff.slice(1))
    else next.tags.add(eff)
    return next
  }

  const mNs = eff.match(/^(tag|stat|goal|fact):(.*)$/)
  if (!mNs) return next
  const ns = mNs[1]
  const rest = mNs[2].trim()

  if (ns === 'tag') {
    if (rest.startsWith('!')) next.tags.delete(rest.slice(1))
    else next.tags.add(rest)
    return next
  }

  if (ns === 'stat' || ns === 'goal') {
    const mDelta = rest.match(/^([A-Za-z_][\w\.]*)\s*([+-])\s*(-?\d+(?:\.\d+)?)$/)
    const mAssign = rest.match(/^([A-Za-z_][\w\.]*)\s*=\s*(-?\d+(?:\.\d+)?)$/)
    const box = ns === 'stat' ? next.stats : next.goals
    if (mAssign) {
      box[mAssign[1]] = Number(mAssign[2])
      return next
    }
    if (mDelta) {
      const key = mDelta[1]
      const sign = mDelta[2]
      const amt = Number(mDelta[3])
      const curr = box[key] ?? 0
      box[key] = sign === '+' ? curr + amt : curr - amt
      return next
    }
    return next
  }

  if (ns === 'fact') {
    // fact:key=value or fact:key (=> verified)
    const mSet = rest.match(/^([A-Za-z_][\w\.]*)\s*=\s*([A-Za-z_][\w\-]*)$/)
    if (mSet) next.facts[mSet[1]] = mSet[2]
    else next.facts[rest] = 'verified'
    return next
  }

  return next
}

function shortEffect(eff: string): { label: string; tone: 'good' | 'warn' | 'bad' | 'neutral' } {
  const s = eff.trim()
  const tone: { [k: string]: 'good' | 'warn' | 'bad' | 'neutral' } = {
    tag: 'neutral',
    fact: 'neutral',
  }

  const m = s.match(/^(tag|stat|goal|fact):(.*)$/)
  if (!m) return { label: s, tone: 'neutral' }
  const ns = m[1]
  const rest = m[2]

  if (ns === 'tag') {
    const isRemove = rest.trim().startsWith('!')
    return { label: isRemove ? `Remove tag: ${rest.trim().slice(1)}` : `Tag: ${rest.trim()}`, tone: 'neutral' }
  }

  if (ns === 'stat' || ns === 'goal') {
    const mDelta = rest.match(/^([A-Za-z_][\w\.]*)\s*([+-])\s*(-?\d+(?:\.\d+)?)$/)
    const mAssign = rest.match(/^([A-Za-z_][\w\.]*)\s*=\s*(-?\d+(?:\.\d+)?)$/)
    if (mAssign) return { label: `${ns}: ${mAssign[1]} = ${mAssign[2]}`, tone: 'neutral' }
    if (mDelta) {
      const n = Number(mDelta[3])
      const sign = mDelta[2]
      const v = sign === '-' ? -Math.abs(n) : Math.abs(n)
      return {
        label: `${ns}: ${mDelta[1]} ${v >= 0 ? '+' : ''}${v}`,
        tone: v > 0 ? 'good' : v < 0 ? 'bad' : 'neutral',
      }
    }
  }

  if (ns === 'fact') {
    return { label: `Fact: ${rest.trim()}`, tone: tone[ns] ?? 'neutral' }
  }

  return { label: s, tone: 'neutral' }
}

function shortGuard(g: string): string {
  const s = g.trim()
  const m = s.match(/^(tag|stat|goal|fact):(.*)$/)
  if (!m) return s
  const ns = m[1]
  const rest = m[2].trim()
  if (ns === 'tag') return rest.startsWith('!') ? `No tag: ${rest.slice(1)}` : `Tag: ${rest}`
  return `${ns}: ${rest}`
}

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReduced(!!mq.matches)
    update()
    mq.addEventListener?.('change', update)
    return () => mq.removeEventListener?.('change', update)
  }, [])

  return reduced
}

function Typewriter({
  text,
  speed = 14,
  className,
}: {
  text: string
  speed?: number
  className?: string
}) {
  const reduced = usePrefersReducedMotion()
  const [shown, setShown] = useState('')

  useEffect(() => {
    if (reduced) {
      setShown(text || '')
      return
    }

    const full = text || ''
    setShown('')

    let i = 0
    const id = window.setInterval(() => {
      i += 1
      setShown(full.slice(0, i))
      if (i >= full.length) window.clearInterval(id)
    }, speed)

    return () => window.clearInterval(id)
  }, [text, speed, reduced])

  return <div className={className}>{shown}</div>
}


export default function App() {
  const [data, setData] = useState<Scene | null>(null)
  const [currId, setCurrId] = useState<string>('')
  const [state, setState] = useState<RuntimeState>({ tags: new Set(), stats: {}, facts: {}, goals: {} })
  const [log, setLog] = useState<string[]>([])
  const [showDebug, setShowDebug] = useState(false)
  const [highlightGuards, setHighlightGuards] = useState(true)
  // For previewing, it's usually nicer if you can always click through.
  // You can still turn guard-highlighting on to see why an option would be gated.
  const [ignoreGuards, setIgnoreGuards] = useState(true)

  const resetRuntime = (scene?: Scene | null) => {
    const init = scene?.initialState
    setState({
      tags: new Set(init?.tags ?? []),
      stats: { ...(init?.stats ?? {}) },
      facts: { ...(init?.facts ?? {}) },
      goals: { ...(init?.goals ?? {}) },
    })
  }

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const text = await file.text()
    const json = JSON.parse(text) as Scene
    setData(json)
    setCurrId(json.nodes?.[0]?.nodeId ?? '')
    setLog([`Loaded scene: ${json.sceneId} [${json.variantId}]`])
    resetRuntime(json)
  }

  const getNode = (id: string) => data?.nodes.find((n) => n.nodeId === id)
  const getEnding = (id: string) => data?.endings.find((e) => e.endingId === id)

  const canTake = (guards?: string[]) => {
    if (ignoreGuards) return true
    if (!guards || guards.length === 0) return true
    return guards.every((g) => canTakeGuard(state, g))
  }

  const applyEffects = (effects?: string[]) => {
    if (!effects || effects.length === 0) return
    setState((prev) => {
      let next = prev
      for (const eff of effects) next = applyEffect(next, eff)
      return next
    })
  }

  const clickChoice = (c: Choice) => {
    if (!data) return
    if (!canTake(c.guards)) return
    applyEffects(c.effects)
    setLog((l) => [...l, `→ ${c.text}`])

    if (getNode(c.to)) {
      setCurrId(c.to)
    } else {
      const end = getEnding(c.to)
      if (end) {
        setCurrId(`END:${end.endingId}`)
        setLog((l) => [...l, `● Ending: ${end.title} (${end.type})`])
      } else {
        setLog((l) => [...l, `⚠ Unknown target: ${c.to}`])
      }
    }
  }

  const currentNode = useMemo(() => getNode(currId), [data, currId])
  const currentEnding = useMemo(() => {
    if (!currId.startsWith('END:')) return undefined
    return getEnding(currId.replace('END:', ''))
  }, [data, currId])

  const prettySceneName = useMemo(() => {
    const raw = (data?.sceneId || '').trim()
    if (!raw) return 'Untitled scene'
    // keep it readable even when sceneId is a long slug
    return raw
      .split('-')
      .filter(Boolean)
      .slice(0, 16)
      .join(' ')
  }, [data])

  // Auto-load latest.json from /public
  useEffect(() => {
    ;(async () => {
      try {
        const res = await fetch('/latest.json', { cache: 'no-store' })
        if (res.ok) {
          const json = (await res.json()) as Scene
          setData(json)
          setCurrId(json.nodes?.[0]?.nodeId ?? '')
          setLog([`Auto-loaded: ${json.sceneId} [${json.variantId}]`])
          resetRuntime(json)
        }
      } catch {
        // ignore
      }
    })()
  }, [])

  const availableChoices = useMemo(() => {
    if (!currentNode) return []
    const list = Array.isArray(currentNode.choices) ? currentNode.choices : []
    return list.map((c) => ({ choice: c, ok: canTake(c.guards) }))
  }, [currentNode, state, ignoreGuards])

  const noChoicesAvailable = availableChoices.length > 0 && availableChoices.every((c) => !c.ok)

  const sortedEntries = (obj: Record<string, any>) =>
    Object.entries(obj).sort((a, b) => String(a[0]).localeCompare(String(b[0])))

  return (
    <div className="wrap">
      <header className="topbar">
        <div className="brand">
          <div className="brandTitle">Scene Previewer</div>
          <div className="brandSub">Loads previewer/public/latest.json automatically</div>
        </div>

        <div className="topbarActions">
          <label className="fileBtn">
            <input type="file" accept="application/json" onChange={onFile} />
            Choose JSON…
          </label>

          <button
            className="btn"
            onClick={() => {
              if (!data) return
              setCurrId(data.nodes?.[0]?.nodeId ?? '')
              resetRuntime(data)
              setLog((l) => [...l, '⟲ Reset'])
            }}
            disabled={!data}
          >
            Reset
          </button>

          <button className="btnGhost" onClick={() => setShowDebug((s) => !s)}>
            {showDebug ? 'Hide debug' : 'Show debug'}
          </button>
        </div>
      </header>

      {!data ? (
        <main className="grid">
          <section className="card hero">
            <h1 className="h1">No scene loaded</h1>
            <p className="muted">
              Drop an expanded scene JSON into <code className="code">previewer/public/latest.json</code> or use the
              pipeline to publish it automatically.
            </p>
            <p className="muted">
              Tip: from <code className="code">scene-lab/scene-kit</code> run{' '}
              <code className="code">python pipeline.py --provider ollama --brief "..." --variant "..." --serve</code>
            </p>
          </section>
        </main>
      ) : (
        <main className="grid">
          <section className="card hero">
            <div className="sceneRow">
              <div>
                <div className="kicker">Scene</div>
                <div className="sceneTitle">
                    {(data as any).title ?? prettySceneName} <span className="pill">{data.variantId}</span>
                </div>
                <div className="sceneId" title={data.sceneId}>{data.sceneId}</div>
                <div className="sceneIntro">{data.intro?.narration}</div>
              </div>

              <div className="rowGap">
                <button className="chip" onClick={() => setHighlightGuards((v) => !v)}>
                  {highlightGuards ? 'Highlight guards: on' : 'Highlight guards: off'}
                </button>
                <button className="chip" onClick={() => setIgnoreGuards((v) => !v)}>
                  {ignoreGuards ? 'Ignore guards: on' : 'Ignore guards: off'}
                </button>
              </div>
            </div>
          </section>

          <section
          className={
            'card main ' +
          (currentEnding
          ? `frame frame_ending frame_${currentEnding.type}`
          : currentNode
            ? 'frame frame_node'
           : 'frame')
            }
              >
            {currentEnding ? (
              <>
                <div className="nodeHeader">
                  <div className="nodeTitle">Ending · {currentEnding.title}</div>
                  <span className={`badge badge_${currentEnding.type}`}>{currentEnding.type}</span>
                </div>
                <Typewriter className="nodeText" text={currentEnding.narration} speed={14} />
                <div className="rowGap">
                  <button
                    className="btn"
                    onClick={() => {
                      setCurrId(data.nodes?.[0]?.nodeId ?? '')
                      resetRuntime(data)
                    }}
                  >
                    Restart
                  </button>
                </div>
              </>
            ) : currentNode ? (
              <>
                <div className="nodeHeader">
                  <div>
                    <div className="kicker">Node</div>
                    <div className="nodeTitle">{currentNode.nodeId}</div>
                  </div>
                  {currentNode.image ? <span className="pill">image</span> : null}
                </div>

                <Typewriter className="nodeText" text={currentNode.narration} speed={14} />


                {noChoicesAvailable ? (
                  <div className="callout">
                    <div className="calloutTitle">All choices are locked</div>
                    <div className="muted">
                      This scene generated guards (requirements) that you currently don’t meet. Toggle{' '}
                      <b>Ignore guards</b> to keep testing, or regenerate the scene with fewer guard constraints.
                    </div>
                  </div>
                ) : null}

                <div className="choices">
                  {availableChoices.map(({ choice: c, ok }) => {
                    const disabled = !ok
                    return (
                      <button
                        key={c.choiceId}
                        className={
                          'choice ' +
                          (disabled ? 'choice_disabled ' : '') +
                          (highlightGuards && disabled ? 'choice_locked' : 'choice_ok')
                        }
                        onClick={() => clickChoice(c)}
                        disabled={disabled}
                      >
                        <div className="choiceTop">
                          <div className="choiceText">{c.text}</div>
                          {c.moveType ? <span className="pill">{c.moveType}</span> : null}
                        </div>

                        {(c.guards && c.guards.length) || (c.effects && c.effects.length) ? (
                          <div className="choiceMeta">
                            {c.guards?.length ? (
                              <div className="metaBlock">
                                <div className="metaLabel">Requires</div>
                                <div className="metaRow">
                                  {c.guards.map((g, i) => (
                                    <span key={i} className="mini">
                                      {shortGuard(g)}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            ) : null}
                            {c.effects?.length ? (
                              <div className="metaBlock">
                                <div className="metaLabel">Effects</div>
                                <div className="metaRow">
                                  {c.effects.map((e, i) => {
                                    const s = shortEffect(e)
                                    return (
                                      <span key={i} className={`mini mini_${s.tone}`}>
                                        {s.label}
                                      </span>
                                    )
                                  })}
                                </div>
                              </div>
                            ) : null}
                          </div>
                        ) : null}
                      </button>
                    )
                  })}
                </div>
              </>
            ) : (
              <>
                <div className="nodeHeader">
                  <div className="nodeTitle">Unknown node</div>
                </div>
                <div className="muted">Current id: {currId}</div>
              </>
            )}
          </section>

          <aside className="card side">
  <div className="sideTitle">Run HUD</div>

  <div className="hudBlock">
    <div className="kicker">Now</div>
    <div className="hudNow">
      {currentEnding ? (
        <>
          <div className="hudNowTitle">Ending</div>
          <div className="hudNowValue">{currentEnding.title}</div>
          <span className={`badge badge_${currentEnding.type}`}>{currentEnding.type}</span>
        </>
      ) : currentNode ? (
        <>
          <div className="hudNowTitle">Node</div>
          <div className="hudNowValue">{currentNode.nodeId}</div>
          {currentNode.image ? <span className="pill">image</span> : null}
        </>
      ) : (
        <>
          <div className="hudNowTitle">Node</div>
          <div className="hudNowValue">Unknown</div>
        </>
      )}
    </div>
  </div>

  <div className="hudBlock">
    <div className="kicker">Objectives</div>
    <div className="hudBody">
      {Object.keys(state.goals).length === 0 ? (
        <div className="muted">No active objectives yet.</div>
      ) : (
        <div className="objectiveList">
          {Object.entries(state.goals)
            .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
            .slice(0, 8)
            .map(([k, v]) => (
              <div key={k} className="objectiveRow">
                <div className="objectiveKey">{k}</div>
                <div className="objectiveVal">{v}</div>
              </div>
            ))}
        </div>
      )}
    </div>
  </div>

  <div className="hudBlock">
    <div className="kicker">Journal</div>
    <div className="hudBody">
      {log.length === 0 ? (
        <div className="muted">Nothing yet.</div>
      ) : (
        <div className="journal">
          {log.slice(-7).reverse().map((x, i) => (
            <div key={i} className="journalLine">
              {x}
            </div>
          ))}
        </div>
      )}
    </div>
  </div>

  <div className="hudBlock">
    <div className="kicker">Tools</div>
    <div className="hudButtons">
      <button className="chip" onClick={() => setIgnoreGuards((v) => !v)}>
        {ignoreGuards ? 'Ignore guards: on' : 'Ignore guards: off'}
      </button>
      <button className="chip" onClick={() => setShowDebug((s) => !s)}>
        {showDebug ? 'Hide debug' : 'Show debug'}
      </button>
      <button
        className="chip"
        onClick={() => {
          if (!data) return
          setCurrId(data.nodes?.[0]?.nodeId ?? '')
          resetRuntime(data)
          setLog((l) => [...l, '⟲ Reset'])
        }}
        disabled={!data}
      >
        Reset run
      </button>
    </div>
  </div>
</aside>
        </main>
      )}

      <footer className="footer">Scene‑Lab Previewer · UI polish + guard/effect parsing</footer>
    </div>
  )
}
