import React, { useMemo } from 'react';
import Editor from '@monaco-editor/react';

interface ArtifactViewerProps {
  artifact: any;
  label: string;
}

export const ArtifactViewer: React.FC<ArtifactViewerProps> = ({ artifact, label }) => {
  const codeString = useMemo(() => {
    try {
      return JSON.stringify(artifact, null, 2) || '{}';
    } catch {
      return '{}';
    }
  }, [artifact]);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-gray-800 bg-[#18181b] px-4 py-2">
        <span className="text-xs font-semibold text-gray-400">产物查阅: {label}</span>
      </div>
      <div className="flex-1 bg-[#1e1e1e]">
        <Editor
          height="100%"
          defaultLanguage="json"
          theme="vs-dark"
          value={codeString}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 13,
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            wordWrap: 'on',
            padding: { top: 16 },
            smoothScrolling: true,
            scrollBeyondLastLine: false,
          }}
        />
      </div>
    </div>
  );
};
