import { useCallback, useEffect, useState } from 'react';
import { fetchSlots } from '../api/client';
import type { Slot } from '../types/api';

const POLL_INTERVAL_MS = 10_000;

export interface UseSlotsResult {
  slots: Slot[];
  lastUpdated: string | null;
  isStale: boolean;
}

function formatTime(date: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(date);
}

/** Poll GET /slots every 10 seconds, retaining the last good result on errors. */
export function useSlots(): UseSlotsResult {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [isStale, setIsStale] = useState(false);

  const pollSlots = useCallback(async () => {
    try {
      const latestSlots = await fetchSlots();
      setSlots(latestSlots);
      setLastUpdated(formatTime(new Date()));
      setIsStale(false);
    } catch {
      // Keep the last successful data and timestamp; show that it's stale.
      setIsStale(true);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    const poll = async () => {
      try {
        const latestSlots = await fetchSlots();
        if (!isMounted) return;

        setSlots(latestSlots);
        setLastUpdated(formatTime(new Date()));
        setIsStale(false);
      } catch {
        if (isMounted) {
          // Never clear last-known-good slots if the request fails.
          setIsStale(true);
        }
      }
    };

    void poll();
    const intervalId = window.setInterval(() => {
      void poll();
    }, POLL_INTERVAL_MS);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, []);

  return { slots, lastUpdated, isStale };
}
