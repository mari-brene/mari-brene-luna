import type { TimerAtivo } from "../tipos";
import { formatarRestante, usarRelogio } from "../usarTimers";

interface Props {
  timers: TimerAtivo[];
  aoCancelar: (id: string) => void;
}

export function Timers({ timers, aoCancelar }: Props) {
  const agora = usarRelogio(timers.length > 0);
  if (timers.length === 0) return null;

  return (
    <ul className="timers" aria-label="Timers ativos">
      {timers.map((t) => (
        <li key={t.id} className="timer">
          <span aria-hidden="true">⏳</span>
          <span className="timer-tempo">{formatarRestante(t.fim - agora)}</span>
          <button type="button" className="timer-cancelar" onClick={() => aoCancelar(t.id)} aria-label="Cancelar timer">
            ×
          </button>
        </li>
      ))}
    </ul>
  );
}
