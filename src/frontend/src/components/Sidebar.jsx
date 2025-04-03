import { Link } from 'react-router-dom';

const Sidebar = () => {
  return (
    <div className="w-64 h-screen bg-gray-800 text-white p-4">
      <div className="text-xl font-bold mb-8">MNQ Trading</div>
      <nav>
        <ul className="space-y-4">
          <li>
            <Link 
              to="/" 
              className="block py-2 px-4 rounded hover:bg-gray-700 transition-colors"
            >
              Dashboard
            </Link>
          </li>
          <li>
            <Link 
              to="/settings" 
              className="block py-2 px-4 rounded hover:bg-gray-700 transition-colors"
            >
              Settings
            </Link>
          </li>
        </ul>
      </nav>
    </div>
  );
};

export default Sidebar; 