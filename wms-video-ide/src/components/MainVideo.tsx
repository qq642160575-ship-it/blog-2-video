import React from 'react';
import { Series, AbsoluteFill, useCurrentFrame, interpolate, spring } from 'remotion';
import { LiveProvider, LiveError, LivePreview } from 'react-live';
import type { Scene } from '../types/scene';

// 将 marks 锚点数据注入沙盒引擎
const EngineScene: React.FC<{ code: string; marks: Record<string, number> }> = ({ code, marks }) => {
  const scope = { React, AbsoluteFill, useCurrentFrame, interpolate, spring, marks };

  return (
    <LiveProvider code={code} scope={scope} noInline={true}>
      <LivePreview />
      <LiveError
        style={{
          backgroundColor: '#fee2e2',
          color: '#b91c1c',
          padding: '20px',
          height: '100%',
          fontSize: '24px',
          zIndex: 9999,
        }}
      />
    </LiveProvider>
  );
};

export const MainVideo: React.FC<{ scenes: Scene[] }> = ({ scenes }) => {
  return (
    <Series>
      {scenes.map((scene) => (
        <Series.Sequence key={scene.id} durationInFrames={scene.durationInFrames}>
          <EngineScene code={scene.code} marks={scene.marks} />
        </Series.Sequence>
      ))}
    </Series>
  );
};
