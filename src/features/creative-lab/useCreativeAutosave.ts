import React from 'react';
import { BackendRequestError } from '../../api/client';
import {
  productApi,
  type CreativeCanvas,
  type CreativeRecord,
} from '../../api/productApi';

export type CreativeAutosaveStatus = 'idle' | 'dirty' | 'saving' | 'saved' | 'conflict' | 'error';

interface CreativeAutosaveOptions {
  delay?: number;
  enabled?: boolean;
  onSaved?: (creative: CreativeRecord) => void;
}

export function useCreativeAutosave(initial: CreativeRecord, options: CreativeAutosaveOptions = {}) {
  const delay = options.delay ?? 900;
  const enabled = options.enabled ?? true;
  const onSaved = options.onSaved;
  const [creative, setCreative] = React.useState(initial);
  const [document, setDocumentState] = React.useState<CreativeCanvas>(initial.document);
  const [status, setStatus] = React.useState<CreativeAutosaveStatus>('idle');
  const [error, setError] = React.useState<string>();
  const documentRef = React.useRef(document);
  const updatedAtRef = React.useRef(initial.updatedAt);
  const revisionRef = React.useRef(0);
  const savedRevisionRef = React.useRef(0);
  const savingRef = React.useRef(false);

  React.useEffect(() => {
    setCreative(initial);
    setDocumentState(initial.document);
    documentRef.current = initial.document;
    updatedAtRef.current = initial.updatedAt;
    revisionRef.current = 0;
    savedRevisionRef.current = 0;
    savingRef.current = false;
    setStatus('idle');
    setError(undefined);
  }, [initial.id]);

  const setDocument = React.useCallback((next: CreativeCanvas | ((current: CreativeCanvas) => CreativeCanvas)) => {
    setDocumentState((current) => {
      const value = typeof next === 'function' ? next(current) : next;
      documentRef.current = value;
      return value;
    });
    revisionRef.current += 1;
    setError(undefined);
    setStatus('dirty');
  }, []);

  const saveNow = React.useCallback(async () => {
    if (savingRef.current || revisionRef.current === savedRevisionRef.current) return creative;
    const targetRevision = revisionRef.current;
    if (!enabled) {
      savedRevisionRef.current = targetRevision;
      setStatus('saved');
      return creative;
    }
    savingRef.current = true;
    setStatus('saving');
    setError(undefined);
    try {
      const saved = await productApi.updateCreative(initial.id, {
        document: documentRef.current,
        expectedUpdatedAt: updatedAtRef.current,
      });
      setCreative(saved);
      updatedAtRef.current = saved.updatedAt;
      savedRevisionRef.current = targetRevision;
      const hasNewChanges = revisionRef.current !== targetRevision;
      setStatus(hasNewChanges ? 'dirty' : 'saved');
      onSaved?.(saved);
      return saved;
    } catch (requestError) {
      if (requestError instanceof BackendRequestError && requestError.status === 409) {
        setStatus('conflict');
        setError('Há uma versão mais recente deste documento. Recarregue para comparar antes de continuar.');
      } else {
        setStatus('error');
        setError(requestError instanceof Error ? requestError.message : 'Falha ao salvar o documento criativo.');
      }
      throw requestError;
    } finally {
      savingRef.current = false;
    }
  }, [creative, enabled, initial.id, onSaved]);

  React.useEffect(() => {
    if (!enabled || status !== 'dirty') return;
    const timer = window.setTimeout(() => { void saveNow().catch(() => undefined); }, delay);
    return () => window.clearTimeout(timer);
  }, [delay, enabled, saveNow, status]);

  React.useEffect(() => {
    const warnUnsaved = (event: BeforeUnloadEvent) => {
      if (!['dirty', 'saving'].includes(status)) return;
      event.preventDefault();
    };
    window.addEventListener('beforeunload', warnUnsaved);
    return () => window.removeEventListener('beforeunload', warnUnsaved);
  }, [status]);

  const reload = React.useCallback(async () => {
    const latest = await productApi.getCreative(initial.id);
    setCreative(latest);
    setDocumentState(latest.document);
    documentRef.current = latest.document;
    updatedAtRef.current = latest.updatedAt;
    revisionRef.current = 0;
    savedRevisionRef.current = 0;
    setError(undefined);
    setStatus('idle');
    return latest;
  }, [initial.id]);

  return {
    creative,
    document,
    status,
    error,
    isDirty: revisionRef.current !== savedRevisionRef.current,
    setDocument,
    saveNow,
    reload,
  };
}
