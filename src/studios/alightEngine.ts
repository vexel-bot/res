// Discovery describes the local installation; it is never render qualification.
export type AlightApplicationProbe = {
  package: string;
  installed: boolean | null;
  version: string | null;
  installer: string | null;
  connectedDevices: number;
  observationKind: "adb_package_probe";
  observedAtUnix: number;
};
