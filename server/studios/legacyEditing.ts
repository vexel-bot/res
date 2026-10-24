import type { Request, Response } from 'express';
import { assertGovernanceAccess, type authenticate } from '../governance';

/** Old URL-only requests cannot bind a scoped document, revision and immutable assets.
 * Keep an explicit compatibility tombstone; never charge or pretend to edit a file.
 */
export function retiredEditing(module: 'create-image' | 'create-video', permission: 'content.create' | 'content.edit' = 'content.edit') {
  return (req: Request, res: Response) => {
    const auth = (req as Parameters<typeof authenticate>[0]).auth!;
    try { assertGovernanceAccess(auth, { module, permission, clientId: req.body?.clientId || null }); }
    catch (error) {
      const failure = error as Error & { status?: number; code?: string };
      return res.status(failure.status || 403).json({ error: failure.message, code: failure.code });
    }
    return res.status(410).json({
      success: false, code: 'LEGACY_EDITING_RETIRED',
      error: 'Esta rota não executa edição. Abra o Studios e use um projeto com materiais autorizados.',
      replacement: module === 'create-video' ? '/api/v1/studios/v1/video/documents/{documentId}/render-jobs' : '/api/v1/studios/v1/documents/{documentId}/editing-ai-jobs',
    });
  };
}
