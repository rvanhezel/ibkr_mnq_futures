import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Sidebar from './components/Sidebar';

const App = () => {
  const [systemError, setSystemError] = useState(null);
  const [systemSuccess, setSystemSuccess] = useState(null);

  return (
    <Router>
      <div className="flex h-screen">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route 
              path="/" 
              element={
                <Dashboard 
                  systemError={systemError} 
                  setSystemError={setSystemError}
                  systemSuccess={systemSuccess}
                  setSystemSuccess={setSystemSuccess}
                />
              } 
            />
            <Route 
              path="/settings" 
              element={
                <Settings 
                  setSystemError={setSystemError}
                  setSystemSuccess={setSystemSuccess}
                />
              } 
            />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App; 