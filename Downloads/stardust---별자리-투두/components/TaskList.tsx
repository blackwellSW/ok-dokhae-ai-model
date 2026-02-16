import React, { useMemo } from 'react';
import { Task, Category } from '../types';
import { CheckCircle2, Circle, Trash2, CalendarDays } from 'lucide-react';
import { CATEGORY_HEX_COLORS } from '../constants';

interface TaskListProps {
  tasks: Task[];
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
}

export const TaskList: React.FC<TaskListProps> = ({ tasks, onToggle, onDelete }) => {
  
  const sortedTasks = useMemo(() => {
    return [...tasks].sort((a, b) => {
        // Sort by completion status (incomplete first) then by date
        if (a.completed === b.completed) {
            return b.createdAt - a.createdAt;
        }
        return a.completed ? 1 : -1;
    });
  }, [tasks]);

  const formatDate = (ts: number) => {
    return new Intl.DateTimeFormat('ko-KR', { month: 'long', day: 'numeric' }).format(new Date(ts));
  };

  return (
    <div className="w-full h-full bg-space-900 overflow-y-auto px-4 pt-20 pb-32 no-scrollbar">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-3xl font-display font-bold text-white mb-6">별의 기록</h2>
        
        {tasks.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                <p>아직 은하수에 별이 없습니다.</p>
                <p className="text-sm mt-2">+ 버튼을 눌러 별을 띄워보세요.</p>
            </div>
        ) : (
            <div className="space-y-3">
            {sortedTasks.map(task => (
                <div 
                key={task.id}
                className={`group relative flex items-center p-4 rounded-xl border transition-all duration-300 ${
                    task.completed 
                    ? 'bg-space-800/50 border-white/5 opacity-60' 
                    : 'bg-space-800 border-white/10 hover:border-white/20'
                }`}
                >
                <button
                    onClick={() => onToggle(task.id)}
                    className="mr-4 transition-transform active:scale-90"
                >
                    {task.completed ? (
                    <CheckCircle2 size={24} color={CATEGORY_HEX_COLORS[task.category]} />
                    ) : (
                    <Circle size={24} className="text-slate-500 hover:text-white" />
                    )}
                </button>

                <div className="flex-1">
                    <h3 className={`font-medium text-base ${task.completed ? 'text-slate-400 line-through' : 'text-white'}`}>
                    {task.title}
                    </h3>
                    <div className="flex items-center gap-3 mt-1">
                        <span 
                            className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded border border-white/10 text-slate-300"
                        >
                            {task.category}
                        </span>
                        <div className="flex items-center text-xs text-slate-500">
                            <CalendarDays size={12} className="mr-1" />
                            {formatDate(task.createdAt)}
                        </div>
                    </div>
                </div>

                <button 
                    onClick={() => onDelete(task.id)}
                    className="opacity-0 group-hover:opacity-100 p-2 text-slate-600 hover:text-red-400 transition-all"
                >
                    <Trash2 size={18} />
                </button>
                </div>
            ))}
            </div>
        )}
      </div>
    </div>
  );
};