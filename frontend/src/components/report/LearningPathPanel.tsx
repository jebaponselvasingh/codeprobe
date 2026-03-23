import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from 'recharts'

interface LearningItem {
  day: string
  topic: string
  why: string
  exercise: string
  estimated_hours: number
}

interface Week {
  week: number
  focus: string
  items: LearningItem[]
}

interface LearningPath {
  weeks: Week[]
  skill_gaps: Record<string, number>
}

function SkillGapRadar({ skillGaps }: { skillGaps: Record<string, number> }) {
  const data = Object.entries(skillGaps).map(([cat, score]) => ({
    subject: cat.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    score: Math.round(score * 10) / 10,
    fullMark: 10,
  }))

  return (
    <div className="card">
      <h3 className="text-sm font-medium mb-4" style={{ color: 'var(--text-secondary)' }}>
        SKILL GAP RADAR
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data}>
          <PolarGrid stroke="var(--border)" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
          />
          <PolarRadiusAxis
            domain={[0, 10]}
            tick={{ fill: 'var(--text-muted, #666)', fontSize: 10 }}
          />
          <Radar
            name="Score"
            dataKey="score"
            stroke="var(--accent-blue, #4f8ff7)"
            fill="var(--accent-blue, #4f8ff7)"
            fillOpacity={0.3}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}

function LearningItemCard({ item }: { item: LearningItem }) {
  return (
    <div
      className="rounded-lg p-4 flex flex-col gap-3"
      style={{ background: 'var(--bg-primary)', border: '1px solid var(--border)' }}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="text-xs font-medium" style={{ color: 'var(--text-muted, #999)' }}>
            Day {item.day}
          </span>
          <h4 className="font-semibold text-sm mt-0.5" style={{ color: 'var(--text-primary)' }}>
            {item.topic}
          </h4>
        </div>
        <span
          className="text-xs px-2 py-1 rounded-full flex-shrink-0"
          style={{ background: 'rgba(79,143,247,0.1)', color: 'var(--accent-blue)' }}
        >
          ~{item.estimated_hours}h
        </span>
      </div>

      {/* Why it matters */}
      <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
        <span className="font-medium">Why: </span>
        {item.why}
      </p>

      {/* Exercise callout box */}
      <div
        className="rounded-lg p-3 text-sm"
        style={{ background: 'rgba(79,143,247,0.08)', borderLeft: '3px solid var(--accent-blue)' }}
      >
        <span
          className="font-medium text-xs block mb-1"
          style={{ color: 'var(--accent-blue)' }}
        >
          EXERCISE
        </span>
        <p style={{ color: 'var(--text-secondary)' }}>{item.exercise}</p>
      </div>
    </div>
  )
}

function WeekPlan({ week }: { week: Week }) {
  return (
    <div className="card flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <span
          className="px-2 py-0.5 rounded text-xs font-bold"
          style={{ background: 'var(--accent-blue)', color: '#fff' }}
        >
          WEEK {week.week}
        </span>
        <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
          Focus:{' '}
          {week.focus
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase())}
        </span>
      </div>
      {(week.items || []).map((item, i) => (
        <LearningItemCard key={i} item={item} />
      ))}
    </div>
  )
}

export function LearningPathPanel({ data }: { data: LearningPath }) {
  return (
    <div className="flex flex-col gap-6">
      <SkillGapRadar skillGaps={data.skill_gaps} />
      {data.weeks.map(week => (
        <WeekPlan key={week.week} week={week} />
      ))}
    </div>
  )
}
