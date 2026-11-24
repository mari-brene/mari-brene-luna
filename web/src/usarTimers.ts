import { useCallback, useEffect, useRef, useState } from "react";
import type { TimerAtivo } from "./tipos";

/** Timers do navegador (setTimeout), com lista para a interface mostrar a contagem. */
export function usarTimers(aoDisparar: (timer: TimerAtivo) => void) {
  const [timers, setTimers] = useState<TimerAtivo[]>([]);
  const handles = useRef(new Map<string, number>());
  const disparar = useRef(aoDisparar);
  disparar.current = aoDisparar;

  const adicionar = useCallback((timer: TimerAtivo) => {
    const handle = window.setTimeout(() => {
      handles.current.delete(timer.id);
      setTimers((lista) => lista.filter((t) => t.id !== timer.id));
      disparar.current(timer);
    }, Math.max(0, timer.fim - Date.now()));
    handles.current.set(timer.id, handle);
    setTimers((lista) => [...lista, timer].sort((a, b) => a.fim - b.fim));
  }, []);

  const cancelar = useCallback((id: string) => {
    const handle = handles.current.get(id);
    if (handle !== undefined) window.clearTimeout(handle);
    handles.current.delete(id);
    setTimers((lista) => lista.filter((t) => t.id !== id));
  }, []);

  const cancelarTodos = useCallback(() => {
    handles.current.forEach((h) => window.clearTimeout(h));
    handles.current.clear();
    setTimers([]);
  }, []);

  useEffect(() => () => handles.current.forEach((h) => window.clearTimeout(h)), []);

  return { timers, adicionar, cancelar, cancelarTodos };
}

/**
 * Re-renderiza a cada 250 ms enquanto `ativo` e devolve o horário atual.
 * O horário é lido na renderização, então nunca fica "parado" desde a montagem.
 */
export function usarRelogio(ativo: boolean): number {
  const [, setTique] = useState(0);
  useEffect(() => {
    if (!ativo) return;
    const id = window.setInterval(() => setTique((t) => t + 1), 250);
    return () => window.clearInterval(id);
  }, [ativo]);
  return Date.now();
}

export function formatarRestante(ms: number): string {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const dois = (n: number) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${dois(m)}:${dois(s)}` : `${dois(m)}:${dois(s)}`;
}
