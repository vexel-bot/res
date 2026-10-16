import React from 'react';
import { DepartmentStudio } from '../studios/department/DepartmentStudio';
import type { Post } from '../types';

export type StudioModuleId = 'create' | 'edit_image' | 'edit_video' | 'matrix' | 'briefing';
export interface StudioViewProps {
  onSavePost: (post: Partial<Post>) => void;
  initialMode?: StudioModuleId;
}
/** Legacy navigation aliases share the client-facing creative department. */
export function StudioView({ initialMode }: StudioViewProps) {
  return <DepartmentStudio mode={initialMode === 'edit_video' ? 'video' : initialMode === 'edit_image' ? 'visual' : undefined} />;
}
