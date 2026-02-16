import React from 'react';
import { ViewMode } from '../types';
import { LayoutDashboard, Telescope, PlusCircle, User, ListTodo } from 'lucide-react';

interface NavigationProps {
  currentView: ViewMode;
  onChangeView: (view: ViewMode) => void;
  onAddTask: () => void;
}

export const Navigation: React.FC<NavigationProps> = ({ currentView, onChangeView, onAddTask }) => {
  return (
    <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 w-[90%] max-w-md bg-space-800/80 backdrop-blur-md border border-white/10 rounded-full px-6 py-3 shadow-2xl z-50 flex items-center justify-between">
      
      <button 
        onClick={() => onChangeView('UNIVERSE')}
        className={`flex flex-col items-center gap-1 transition-colors ${currentView === 'UNIVERSE' ? 'text-white' : 'text-slate-500 hover:text-slate-300'}`}
      >
        <Telescope size={24} />
      </button>

      <button 
        onClick={() => onChangeView('LIST')}
        className={`flex flex-col items-center gap-1 transition-colors ${currentView === 'LIST' ? 'text-white' : 'text-slate-500 hover:text-slate-300'}`}
      >
        <ListTodo size={24} />
      </button>

      <button 
        onClick={onAddTask}
        className="transform -translate-y-4 bg-white text-space-900 rounded-full p-3 shadow-lg hover:scale-105 transition-transform"
      >
        <PlusCircle size={32} />
      </button>

      <button 
        className={`flex flex-col items-center gap-1 transition-colors text-slate-500 hover:text-slate-300 cursor-not-allowed opacity-50`}
        title="커뮤니티 (준비 중)"
      >
        <LayoutDashboard size={24} />
      </button>

      <button 
        onClick={() => onChangeView('PROFILE')}
        className={`flex flex-col items-center gap-1 transition-colors ${currentView === 'PROFILE' ? 'text-white' : 'text-slate-500 hover:text-slate-300'}`}
      >
        <User size={24} />
      </button>
    </div>
  );
};