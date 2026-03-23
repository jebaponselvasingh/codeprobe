import { useEffect } from 'react';
import { useProfileStore } from '../../stores/profileStore';

interface Props {
  value: string | null;
  onChange: (id: string | null) => void;
  style?: React.CSSProperties;
}

export function RubricSelector({ value, onChange, style }: Props) {
  const { rubrics, fetchRubrics } = useProfileStore();

  useEffect(() => {
    if (rubrics.length === 0) fetchRubrics();
  }, []);

  return (
    <select value={value || ''} onChange={e => onChange(e.target.value || null)} style={style}>
      <option value="">No Rubric</option>
      {rubrics.map(r => (
        <option key={r.id} value={r.id}>{r.name}</option>
      ))}
    </select>
  );
}
