import { Panel } from '../components/Panel'

export default function AboutPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <Panel title="What HYBRID actually does">
        <div className="space-y-3 text-[14px] text-slate-300 leading-relaxed">
          <p>
            Every request pending at the disk is one of two kinds: real-time (a multimedia stream
            with a deadline) or best-effort (a database read or write with none). HYBRID keeps two
            separate sub-schedulers — SCAN-EDF for real-time, C-LOOK for best-effort — and arbitrates
            between them in rounds.
          </p>
          <p>
            Each round of length T gets split into an RT budget and a BE budget, sized by
            <code className="font-data text-amber-400 mx-1">rt_fraction</code>. Whichever class has
            budget left gets served from; if a request overruns its budget (it must run to
            completion — this scheduler is non-preemptive), the overrun becomes debt subtracted from
            that class's next round.
          </p>
          <p>
            Every five rounds, a feedback controller looks back: if too many deadlines were missed,
            it raises <code className="font-data text-amber-400 mx-1">rt_fraction</code>; if misses
            were rare but the database queue got slow, it lowers it. Two separate thresholds (not
            one) prevent it from oscillating every window.
          </p>
          <p>
            Best-effort requests can still starve under sustained RT pressure, so any BE request
            waiting past an aging threshold is escalated and served immediately — up to a capped
            number per round, so this escape hatch can't itself swallow the whole round.
          </p>
        </div>
      </Panel>

      <Panel title="Why not just use EDF?">
        <p className="text-[14px] text-slate-300 leading-relaxed">
          EDF alone ignores seek cost entirely — it happily jerks the head across the disk to serve
          the two nearest deadlines even when a same-urgency request sits right next to the head.
          SCAN-EDF fixes that within the RT class by grouping requests that are equally urgent and
          picking the nearest one first. But neither EDF nor SCAN-EDF know that a database workload
          exists at all — left alone with a mixed workload, either would starve every OLTP/OLAP
          request behind a continuous stream of deadlines. That's the problem HYBRID's budget split
          and aging queue exist to solve.
        </p>
      </Panel>

      <Panel title="Why non-preemptive?">
        <p className="text-[14px] text-slate-300 leading-relaxed">
          A real disk head physically can't abandon an in-flight seek or transfer — there's no
          software equivalent of a context switch mid-rotation. Modelling it as preemptible would
          understate real scheduling cost and make every algorithm look better than it would be on
          real hardware.
        </p>
      </Panel>

      <Panel title="Why this all collapses on SSDs">
        <p className="text-[14px] text-slate-300 leading-relaxed">
          Every seek-optimising scheduler here — SCAN, C-SCAN, LOOK, C-LOOK — exists to minimize
          physical head travel. An SSD has no head. Switch the disk model to SSD and seek time and
          rotational delay both go to zero; every scheduler's ordering still runs, but their
          performance converges, because the thing they were all optimising for no longer costs
          anything. That's exactly what the HDD-vs-SSD preset is built to show.
        </p>
      </Panel>

      <Panel title="Honest limitations">
        <ul className="text-[14px] text-slate-300 leading-relaxed list-disc list-inside space-y-1">
          <li>No real hardware — this is a discrete-event simulation, not a kernel patch or a driver.</li>
          <li>No on-disk cache modelling, no NCQ, no filesystem layer.</li>
          <li>Linear cylinder-to-LBA mapping (real disks are far messier).</li>
          <li>Rotational latency is averaged, not modelled as an actual platter position.</li>
          <li>A result set where HYBRID wins every single metric on every workload would be a sign
            of a bug or a rigged workload — the Comparison page is built to show it losing where it
            genuinely does.</li>
        </ul>
      </Panel>
    </div>
  )
}
