export function videoOutputUrl(
  assetId: string,
  workspaceId: string,
  clientId?: string,
) {
  return `/api/v1/studios/v1/video/library/${encodeURIComponent(assetId)}/content?workspaceId=${encodeURIComponent(workspaceId)}${clientId ? `&clientId=${encodeURIComponent(clientId)}` : ""}`;
}
