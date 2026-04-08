import { LeftPanel } from './components/LeftPanel';
import { PreviewPlayer } from './components/PreviewPlayer';
import { CodeEditor } from './components/CodeEditor';

/**
 * App — 纯三栏布局容器，零业务逻辑。
 *
 * 重构前：345 行，6+ 职责（布局 / Timeline / Script / Player / AI 调用 / 派生计算）
 * 重构后：15 行，唯一职责 = 三栏 flex 布局
 *
 * 所有逻辑已分发到：
 * - LeftPanel        → 博文输入 / Timeline / 文案编辑台
 * - PreviewPlayer    → Remotion Player + usePlayerControl
 * - CodeEditor       → Monaco Editor
 */
export default function App() {
  return (
    <div className="flex h-screen w-full bg-[#0e0e11] text-gray-300 font-sans overflow-hidden">
      <LeftPanel />
      <PreviewPlayer />
      <CodeEditor />
    </div>
  );
}
