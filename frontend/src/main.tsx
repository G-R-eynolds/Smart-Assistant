import React from 'react';
import { createRoot } from 'react-dom/client';
import { GraphViewer } from './graph/GraphViewer';

const App: React.FC = () => {
  return (
    <div style={{height: '100vh', width: '100vw'}}>
      <GraphViewer />
    </div>
  );
};

createRoot(document.getElementById('root')!).render(<App />);
