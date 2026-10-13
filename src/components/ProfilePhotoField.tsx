import { Camera } from 'lucide-react';
import { ProfileAvatar } from './ProfileAvatar';
import { ClickoLoader } from './ClickoLoader';

export function ProfilePhotoField({ src, initials, disabled, onSelect }: {
  src: string; initials: string; disabled: boolean; onSelect: (file?: File) => void;
}) {
  return <div className="clicko-profile-photo relative h-20 w-20 shrink-0 overflow-hidden rounded-2xl border border-white/[0.08] bg-white/[0.035]">
    <ProfileAvatar src={src} alt="Avatar da conta" className="h-full w-full" fallback={<span className="grid h-full w-full place-items-center text-[18px] font-semibold text-[rgba(255,255,255,0.72)]">{initials}</span>} />
    <span className="pointer-events-none absolute bottom-1 right-1 grid h-7 w-7 place-items-center rounded-lg border border-white/10 bg-black/80 text-[rgba(255,255,255,0.72)]">{disabled ? <ClickoLoader size="tiny" tone="dark" label="Salvando foto de perfil" /> : <Camera className="h-3.5 w-3.5" />}</span>
    <input aria-label="Alterar foto de perfil" type="file" accept="image/jpeg,image/png,image/webp" disabled={disabled}
      className="absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
      onChange={event => { const file = event.currentTarget.files?.[0]; event.currentTarget.value = ''; onSelect(file); }} />
  </div>;
}
