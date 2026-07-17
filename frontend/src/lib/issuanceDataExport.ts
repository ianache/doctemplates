import JSZip from "jszip";

import type { DocumentIssuanceDetail, DocumentTracelog } from "./documentIssuances";

export type DataExportSection = "input_data" | "metadata_values" | "tracelogs";

export type DataExportSelection = Record<DataExportSection, boolean>;

export const DEFAULT_DATA_EXPORT_SELECTION: DataExportSelection = {
  input_data: true,
  metadata_values: false,
  tracelogs: false,
};

const SECTION_FILENAMES: Record<DataExportSection, string> = {
  input_data: "input_data.json",
  metadata_values: "metadata_values.json",
  tracelogs: "tracelogs.json",
};

export function selectedDataExportSections(selection: DataExportSelection): DataExportSection[] {
  return (Object.keys(selection) as DataExportSection[]).filter((section) => selection[section]);
}

function sectionPayload(
  section: DataExportSection,
  detail: DocumentIssuanceDetail,
  tracelogs: DocumentTracelog[],
): unknown {
  if (section === "input_data") return detail.input_data;
  if (section === "metadata_values") return detail.metadata_values ?? {};
  return tracelogs;
}

function jsonBlob(value: unknown): Blob {
  return new Blob([`${JSON.stringify(value, null, 2)}\n`], { type: "application/json" });
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export async function downloadIssuanceDataExport(
  detail: DocumentIssuanceDetail,
  tracelogs: DocumentTracelog[],
  selection: DataExportSelection,
): Promise<void> {
  const sections = selectedDataExportSections(selection);
  if (sections.length === 0) {
    throw new Error("Choose at least one data section to download.");
  }

  if (sections.length === 1) {
    const section = sections[0];
    triggerDownload(jsonBlob(sectionPayload(section, detail, tracelogs)), SECTION_FILENAMES[section]);
    return;
  }

  const archive = new JSZip();
  sections.forEach((section) => {
    archive.file(SECTION_FILENAMES[section], `${JSON.stringify(sectionPayload(section, detail, tracelogs), null, 2)}\n`);
  });
  const blob = await archive.generateAsync({ type: "blob" });
  triggerDownload(blob, `issuance-${detail.id}-data.zip`);
}
