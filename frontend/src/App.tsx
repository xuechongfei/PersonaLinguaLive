import { useEffect, useState } from 'react';
import HomePage from './pages/HomePage';
import StudioPage from './pages/StudioPage';

type Route = 'home' | 'studio';

function readRoute(): Route {
  return window.location.hash === '#/studio' ? 'studio' : 'home';
}

export default function App() {
  const [route, setRoute] = useState<Route>(readRoute());

  useEffect(() => {
    const onHash = () => setRoute(readRoute());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  if (route === 'studio') return <StudioPage />;
  return (
    <HomePage
      onStart={() => {
        window.location.hash = '#/studio';
      }}
    />
  );
}
