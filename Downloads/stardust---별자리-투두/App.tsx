import React, { useState, useEffect, useMemo } from 'react';
import { Task, ViewMode, Category, Difficulty, TimeScope } from './types';
import { Navigation } from './components/Navigation';
import { ConstellationCanvas } from './components/ConstellationCanvas';
import { TaskList } from './components/TaskList';
import { AddTaskModal } from './components/AddTaskModal';
import { WelcomeOverlay } from './components/WelcomeOverlay';
import { Notification } from './components/Notification';
import { EMOTIONAL_MESSAGES } from './constants';

// Helper to generate non-overlapping random positions
const getRandomPosition = () => {
  const padding = 15;
  return {
    x: Math.random() * (100 - padding * 2) + padding,
    y: Math.random() * (100 - padding * 2) + padding,
  };
};

// Date helpers
const isSameDay = (d1: number, d2: number) => {
    const date1 = new Date(d1);
    const date2 = new Date(d2);
    return date1.getFullYear() === date2.getFullYear() &&
           date1.getMonth() === date2.getMonth() &&
           date1.getDate() === date2.getDate();
};

const isSameWeek = (d1: number, d2: number) => {
    const date1 = new Date(d1);
    const date2 = new Date(d2);
    // Simple week check (starts on Sunday)
    const oneJan = new Date(date1.getFullYear(), 0, 1);
    const numberOfDays = Math.floor((date1.getTime() - oneJan.getTime()) / (24 * 60 * 60 * 1000));
    const week1 = Math.ceil((date1.getDay() + 1 + numberOfDays) / 7);

    const oneJan2 = new Date(date2.getFullYear(), 0, 1);
    const numberOfDays2 = Math.floor((date2.getTime() - oneJan2.getTime()) / (24 * 60 * 60 * 1000));
    const week2 = Math.ceil((date2.getDay() + 1 + numberOfDays2) / 7);

    return date1.getFullYear() === date2.getFullYear() && week1 === week2;
};

const isSameMonth = (d1: number, d2: number) => {
    const date1 = new Date(d1);
    const date2 = new Date(d2);
    return date1.getFullYear() === date2.getFullYear() &&
           date1.getMonth() === date2.getMonth();
};

const INITIAL_TASKS: Task[] = [
  {
    id: '1',
    title: 'UI 디자인 시안 작업',
    category: Category.CREATIVE,
    difficulty: Difficulty.HARD,
    completed: true,
    createdAt: Date.now(), // Today
    completedAt: Date.now(),
    position: { x: 20, y: 30 }
  },
  {
    id: '2',
    title: '아침 조깅',
    category: Category.HEALTH,
    difficulty: Difficulty.MEDIUM,
    completed: true,
    createdAt: Date.now(), // Today
    completedAt: Date.now(),
    position: { x: 45, y: 40 }
  },
  {
    id: '3',
    title: '지난주 보고서 작성',
    category: Category.WORK,
    difficulty: Difficulty.MEDIUM,
    completed: true,
    createdAt: Date.now() - 3 * 24 * 60 * 60 * 1000, // 3 days ago
    completedAt: Date.now() - 3 * 24 * 60 * 60 * 1000,
    position: { x: 70, y: 60 }
  },
  {
    id: '4',
    title: '다음 달 계획',
    category: Category.LIFE,
    difficulty: Difficulty.EASY,
    completed: false,
    createdAt: Date.now() - 15 * 24 * 60 * 60 * 1000, // 15 days ago
    position: { x: 30, y: 80 }
  },
  // Add a sample overdue incomplete task
  {
    id: '5',
    title: '읽다 만 책 완독하기',
    category: Category.STUDY,
    difficulty: Difficulty.EASY,
    completed: false,
    createdAt: Date.now() - 2 * 24 * 60 * 60 * 1000, // 2 days ago
    position: { x: 60, y: 20 }
  }
];

export default function App() {
  const [tasks, setTasks] = useState<Task[]>(INITIAL_TASKS);
  const [viewMode, setViewMode] = useState<ViewMode>('UNIVERSE');
  const [timeScope, setTimeScope] = useState<TimeScope>('DAILY');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showWelcome, setShowWelcome] = useState(true);
  const [notification, setNotification] = useState<string | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem('stardust_tasks');
    const visited = localStorage.getItem('stardust_visited');
    if (saved) {
      setTasks(JSON.parse(saved));
    }
    if (visited) {
      setShowWelcome(false);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('stardust_tasks', JSON.stringify(tasks));
  }, [tasks]);

  const showRandomNotification = (type: 'created' | 'completed') => {
    const messages = EMOTIONAL_MESSAGES[type];
    const message = messages[Math.floor(Math.random() * messages.length)];
    setNotification(message);
  };

  const handleAddTask = (newTaskData: Omit<Task, 'id' | 'createdAt' | 'position' | 'completed'>) => {
    const newTask: Task = {
      ...newTaskData,
      id: crypto.randomUUID(),
      createdAt: Date.now(),
      completed: false,
      position: getRandomPosition(),
    };
    setTasks(prev => [...prev, newTask]);
    setTimeScope('DAILY'); // Switch to daily to see new task
    setViewMode('UNIVERSE');
    
    // Trigger emotional message
    showRandomNotification('created');
  };

  const handleToggleTask = (id: string) => {
    setTasks(prev => prev.map(t => {
      if (t.id === id) {
        const newCompleted = !t.completed;
        
        // If task is being completed, trigger emotional message
        if (newCompleted) {
          showRandomNotification('completed');
        }

        return {
          ...t,
          completed: newCompleted,
          completedAt: newCompleted ? Date.now() : undefined
        };
      }
      return t;
    }));
  };

  const handleDeleteTask = (id: string) => {
    setTasks(prev => prev.filter(t => t.id !== id));
  };

  const handleTaskMove = (id: string, x: number, y: number) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, position: { x, y } } : t));
  };

  const filteredTasks = useMemo(() => {
    const now = new Date();
    // Reset time to start of day for comparison
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    
    return tasks.filter(task => {
        const dateToCheck = task.createdAt;

        if (timeScope === 'METEOR') {
            // Overdue and not completed
            return task.createdAt < startOfToday && !task.completed;
        }

        if (timeScope === 'DAILY') return isSameDay(dateToCheck, now.getTime());
        if (timeScope === 'WEEKLY') return isSameWeek(dateToCheck, now.getTime());
        if (timeScope === 'MONTHLY') return isSameMonth(dateToCheck, now.getTime());
        return true;
    });
  }, [tasks, timeScope]);

  return (
    <div className="relative w-screen h-screen bg-space-900 text-white overflow-hidden font-sans selection:bg-star-purple selection:text-white">
      
      {showWelcome && <WelcomeOverlay onDismiss={() => {
          setShowWelcome(false);
          localStorage.setItem('stardust_visited', 'true');
      }} />}

      {/* Notification Layer */}
      {notification && (
        <Notification 
          message={notification} 
          onClose={() => setNotification(null)} 
        />
      )}

      <main className="w-full h-full relative">
        {viewMode === 'UNIVERSE' && (
          <ConstellationCanvas 
            tasks={filteredTasks} 
            timeScope={timeScope}
            onTimeScopeChange={setTimeScope}
            onTaskClick={(task) => handleToggleTask(task.id)} 
            onTaskMove={handleTaskMove}
          />
        )}

        {viewMode === 'LIST' && (
          <TaskList 
            tasks={filteredTasks} 
            onToggle={handleToggleTask}
            onDelete={handleDeleteTask}
          />
        )}

        {viewMode === 'PROFILE' && (
            <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center">
                <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-purple-500 to-blue-500 mb-4 shadow-lg shadow-purple-500/30"></div>
                <h2 className="text-2xl font-display font-bold">탐험가</h2>
                <p className="text-slate-400 mt-2">레벨 {Math.floor(tasks.filter(t=>t.completed).length / 5) + 1} 별지기</p>
                
                <div className="mt-8 grid grid-cols-2 gap-4 w-full max-w-xs">
                    <div className="bg-space-800 p-4 rounded-xl border border-white/5">
                        <div className="text-3xl font-bold text-white">{tasks.filter(t => t.completed).length}</div>
                        <div className="text-xs text-slate-500 uppercase tracking-wide">밝힌 별</div>
                    </div>
                    <div className="bg-space-800 p-4 rounded-xl border border-white/5">
                        <div className="text-3xl font-bold text-white">{tasks.length}</div>
                        <div className="text-xs text-slate-500 uppercase tracking-wide">전체 별</div>
                    </div>
                </div>
                
                <div className="mt-8 text-sm text-slate-500 max-w-xs leading-relaxed">
                   팁: 우주 화면에서 별을 드래그하여<br/>나만의 별자리를 그려보세요.
                </div>
            </div>
        )}
      </main>

      <Navigation 
        currentView={viewMode} 
        onChangeView={setViewMode} 
        onAddTask={() => setIsModalOpen(true)} 
      />

      <AddTaskModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        onAdd={handleAddTask} 
      />
    </div>
  );
}