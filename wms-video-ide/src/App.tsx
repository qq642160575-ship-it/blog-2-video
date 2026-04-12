import { LeftPanel } from './components/LeftPanel';
import { PreviewPlayer } from './components/PreviewPlayer';
import { CodeEditor } from './components/CodeEditor';

export default function App() {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#0e0e11] font-sans text-gray-300">
      <LeftPanel />
      <PreviewPlayer />
      <CodeEditor />
    </div>
  );
}
