import { useEffect, useState } from 'react';
import { API_BASE } from '../constants/config';

interface HealthStatus {
  ok: boolean;
  ollama: boolean;
  models: string[];
  active_model: string;
}

export function useHealthCheck() {
  const [status, setStatus] = useState<HealthStatus | null>(null);

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`);
        if (res.ok) {
          setStatus(await res.json());
        } else {
          setStatus({ ok: false, ollama: false, models: [], active_model: '' });
        }
      } catch {
        setStatus({ ok: false, ollama: false, models: [], active_model: '' });
      }
    };
    check();
    const interval = setInterval(check, 30_000);
    return () => clearInterval(interval);
  }, []);

  return status;
}
