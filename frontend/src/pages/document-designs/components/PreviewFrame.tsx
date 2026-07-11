import { useEffect, useState } from "react";

interface PreviewFrameProps {
  blob: Blob | null;
  loading: boolean;
  error: string | null;
}

export function PreviewFrame({ blob, loading, error }: PreviewFrameProps) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!blob) {
      setObjectUrl(null);
      return;
    }

    const url = URL.createObjectURL(blob);
    setObjectUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [blob]);

  if (loading) {
    return (
      <div className="flex h-[600px] w-full items-center justify-center border border-outline-variant bg-surface-container-low rounded-lg p-lg text-sm text-secondary">
        <div className="text-center">
          <p className="animate-pulse font-medium">Generating composed PDF preview...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-[600px] w-full items-center justify-center border border-error/20 bg-error/5 rounded-lg p-lg text-sm text-error">
        <div className="text-center space-y-sm">
          <p className="font-bold">Preview Generation Failed</p>
          <pre className="max-w-md text-left font-mono text-xs whitespace-pre-wrap bg-background p-sm border border-error/10 rounded max-h-80 overflow-y-auto">
            {error}
          </pre>
        </div>
      </div>
    );
  }

  if (!objectUrl) {
    return (
      <div className="flex h-[600px] w-full items-center justify-center border border-outline-variant bg-surface-container-low rounded-lg p-lg text-sm text-on-surface-variant italic">
        Click "Preview PDF" to generate and display the layout previsualization.
      </div>
    );
  }

  return (
    <iframe
      src={objectUrl}
      className="h-[600px] w-full border border-outline-variant rounded-lg bg-surface-container-lowest"
      title="PDF Preview"
    />
  );
}
