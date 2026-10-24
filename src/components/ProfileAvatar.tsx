import React from 'react';

/** Retains the existing frame and restores its initials/icon if a URL fails. */
export function ProfileAvatar({ src, fallback, className = '', alt = '' }: {
  src?: string; fallback: React.ReactNode; className?: string; alt?: string;
}) {
  const [failed, setFailed] = React.useState<string>();
  return src && failed !== src
    ? <img key={src} src={src} alt={alt} className={`clicko-profile-avatar ${className}`} style={{ objectFit: 'cover', borderRadius: 'inherit' }} onError={() => setFailed(src)} />
    : <>{fallback}</>;
}
