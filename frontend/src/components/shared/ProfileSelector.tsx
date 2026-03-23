import { useEffect } from 'react';
import { useProfileStore } from '../../stores/profileStore';

interface Props {
  value: string;
  onChange: (id: string) => void;
  style?: React.CSSProperties;
}

export function ProfileSelector({ value, onChange, style }: Props) {
  const { profiles, fetchProfiles } = useProfileStore();

  useEffect(() => {
    if (profiles.length === 0) fetchProfiles();
  }, []);

  return (
    <select value={value} onChange={e => onChange(e.target.value)} style={style}>
      {profiles.map(p => (
        <option key={p.id} value={p.id}>{p.name}</option>
      ))}
    </select>
  );
}
