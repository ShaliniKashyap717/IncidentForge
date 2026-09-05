import { Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { NewInvestigation } from './pages/NewInvestigation';
import { InvestigationDetail } from './pages/InvestigationDetail';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/new" element={<NewInvestigation />} />
        <Route path="/investigations/:investigationId" element={<InvestigationDetail />} />
      </Routes>
    </Layout>
  );
}

export default App;