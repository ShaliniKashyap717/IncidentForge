import { useState, useEffect, useCallback, useRef } from 'react';
import { FullInvestigationState, TimelineEvent } from '../types/api';

interface UseInvestigationStreamOptions {
  investigationId: string | null;
  onEvent?: (event: TimelineEvent) => void;
  onStateChange?: (state: FullInvestigationState) => void;
  onComplete?: (state: FullInvestigationState) => void;
  onError?: (error: Error) => void;
}

export function useInvestigationStream({
  investigationId,
  onEvent,
  onStateChange,
  onComplete,
  onError,
}: UseInvestigationStreamOptions) {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<TimelineEvent | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    if (!investigationId || eventSourceRef.current) return;

    try {
      const eventSource = new EventSource(`/api/v1/investigations/${investigationId}/stream`);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setConnected(true);
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'event' && data.data) {
            setLastEvent(data.data);
            onEvent?.(data.data);
          } else if (data.type === 'state' && data.data) {
            onStateChange?.(data.data);
          } else if (data.type === 'complete' && data.data) {
            onStateChange?.(data.data);
            onComplete?.(data.data);
            disconnect();
          }
        } catch (err) {
          console.error('Failed to parse SSE message:', err);
        }
      };

      eventSource.onerror = (err) => {
        console.error('SSE error:', err);
        setConnected(false);
        onError?.(new Error('SSE connection lost'));
        scheduleReconnect();
      };
    } catch (err) {
      onError?.(err instanceof Error ? err : new Error('Failed to connect'));
    }
  }, [investigationId, onEvent, onStateChange, onComplete, onError]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setConnected(false);
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) return;
    reconnectTimeoutRef.current = window.setTimeout(() => {
      reconnectTimeoutRef.current = null;
      connect();
    }, 2000);
  }, [connect]);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect, disconnect]);

  return { connected, lastEvent, reconnect: connect };
}