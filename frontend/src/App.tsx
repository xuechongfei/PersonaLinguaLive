import { useEffect, useState } from 'react';
import HomePage from './pages/HomePage';
import StudioPage from './pages/StudioPage';
import HistoryPage from './pages/HistoryPage';
import VocabPage from './pages/VocabPage';

type Route = 'home' | 'studio' | 'history' | 'vocab';

function readRoute(): Route {
  const h = window.location.hash;
  if (h === '#/studio') return 'studio';
  if (h === '#/history') return 'history';
  if (h === '#/vocab') return 'vocab';
  return 'home';
}

export default function App() {
  const [route, setRoute] = useState<Route>(readRoute());

  useEffect(() => {
    const onHash = () => setRoute(readRoute());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  if (route === 'studio') return <StudioPage />;
  if (route === 'history') return <HistoryPage />;
  if (route === 'vocab') return <VocabPage />;
  return (
    <HomePage
      onStart={() => {
        window.location.hash = '#/studio';
      }}
    />
  );
}
