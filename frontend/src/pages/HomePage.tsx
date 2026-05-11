import HealthBadge from '../components/HealthBadge';

interface Props {
  onStart: () => void;
}

export default function HomePage({ onStart }: Props) {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-slate-50 px-4 text-slate-900">
      <h1 className="text-4xl font-bold">PersonaLinguaLive</h1>
      <p className="mt-3 max-w-xl text-center text-slate-600">
        Anything you see can teach you English. 上传一张照片,把里面的物体变成英语对话伙伴。
      </p>
      <button
        type="button"
        onClick={onStart}
        className="mt-8 rounded-xl bg-sky-600 px-6 py-3 text-base font-semibold text-white shadow hover:bg-sky-700"
      >
        开始上传
      </button>
      <button
        type="button"
        onClick={onStart}
        className="mt-3 rounded-xl border border-indigo-300 px-6 py-3 text-base font-semibold text-indigo-600 hover:bg-indigo-50"
      >
        Browse Scenes
      </button>
      <div className="mt-4 flex gap-4 text-sm">
        <a href="#/history" className="text-indigo-600 hover:underline">
          History
        </a>
        <a href="#/vocab" className="text-indigo-600 hover:underline">
          Vocabulary
        </a>
      </div>
      <div className="mt-6">
        <HealthBadge />
      </div>
    </main>
  );
}
