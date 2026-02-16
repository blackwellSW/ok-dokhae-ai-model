import React, { useState, useRef, useEffect } from 'react';
import { Task, TimeScope } from '../types';
import { Star } from './Star';
import { Sparkles } from 'lucide-react';

interface ConstellationCanvasProps {
  tasks: Task[];
  timeScope: TimeScope;
  onTimeScopeChange: (scope: TimeScope) => void;
  onTaskClick: (task: Task) => void;
  onTaskMove: (id: string, x: number, y: number) => void;
}

export const ConstellationCanvas: React.FC<ConstellationCanvasProps> = ({ 
  tasks, 
  timeScope,
  onTimeScopeChange,
  onTaskClick,
  onTaskMove
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);

  // Logic to create lines: Connect completed tasks chronologically
  const completedTasks = tasks
    .filter(t => t.completed && t.completedAt)
    .sort((a, b) => (a.completedAt || 0) - (b.completedAt || 0));

  // --- Drag & Drop Handlers ---
  const handleDragStart = (id: string, e: React.MouseEvent | React.TouchEvent) => {
    // Stop propagation so we don't trigger background clicks if any
    e.stopPropagation(); 
    setDraggingId(id);
  };

  const handleDragMove = (e: React.MouseEvent | React.TouchEvent) => {
    if (!draggingId || !containerRef.current) return;

    const container = containerRef.current.getBoundingClientRect();
    let clientX, clientY;

    if ('touches' in e) {
      clientX = e.touches[0].clientX;
      clientY = e.touches[0].clientY;
    } else {
      clientX = (e as React.MouseEvent).clientX;
      clientY = (e as React.MouseEvent).clientY;
    }

    // Calculate percentage position
    let x = ((clientX - container.left) / container.width) * 100;
    let y = ((clientY - container.top) / container.height) * 100;

    // Clamp to 0-100%
    x = Math.max(0, Math.min(100, x));
    y = Math.max(0, Math.min(100, y));

    onTaskMove(draggingId, x, y);
  };

  const handleDragEnd = () => {
    setDraggingId(null);
  };

  // Attach global event listeners for smooth dragging even if mouse leaves the star element
  useEffect(() => {
    if (draggingId) {
      window.addEventListener('mousemove', handleDragMove as any);
      window.addEventListener('mouseup', handleDragEnd);
      window.addEventListener('touchmove', handleDragMove as any, { passive: false });
      window.addEventListener('touchend', handleDragEnd);
    }

    return () => {
      window.removeEventListener('mousemove', handleDragMove as any);
      window.removeEventListener('mouseup', handleDragEnd);
      window.removeEventListener('touchmove', handleDragMove as any);
      window.removeEventListener('touchend', handleDragEnd);
    };
  }, [draggingId]);

  const getTitle = () => {
    switch(timeScope) {
      case 'DAILY': return '오늘의 하늘';
      case 'WEEKLY': return '주간 은하수';
      case 'MONTHLY': return '월간 우주';
      case 'METEOR': return '별똥별 보관소';
      default: return '나의 우주';
    }
  };

  const getDescription = () => {
    if (timeScope === 'METEOR') {
       return `${tasks.length}개의 미완성 별들이 떠돌고 있습니다`;
    }
    return `${completedTasks.length}개의 별이 빛나고 있습니다`;
  };

  return (
    <div 
      ref={containerRef}
      className={`absolute inset-0 w-full h-full overflow-hidden bg-gradient-to-b touch-none transition-colors duration-1000 ${
        timeScope === 'METEOR' 
        ? 'from-[#0f0c1b] via-[#2a1b3d] to-[#0f0c1b]' // Darker/Purplish for Meteors
        : 'from-space-900 via-[#1a1f35] to-space-900'
      }`}
    >
      
      {/* Background Static Stars (Decorations) */}
      <div className="absolute inset-0 opacity-30 pointer-events-none">
        {[...Array(50)].map((_, i) => (
          <div
            key={`bg-star-${i}`}
            className={`absolute bg-white rounded-full ${timeScope === 'METEOR' ? 'animate-pulse' : 'animate-twinkle'}`}
            style={{
              width: Math.random() * 2 + 'px',
              height: Math.random() * 2 + 'px',
              left: Math.random() * 100 + '%',
              top: Math.random() * 100 + '%',
              animationDelay: Math.random() * 5 + 's',
              opacity: Math.random(),
            }}
          />
        ))}
      </div>

      {/* SVG Layer for Constellation Lines */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
        {completedTasks.map((task, index) => {
          if (index === 0) return null;
          const prevTask = completedTasks[index - 1];
          return (
            <line
              key={`link-${prevTask.id}-${task.id}`}
              x1={`${prevTask.position.x}%`}
              y1={`${prevTask.position.y}%`}
              x2={`${task.position.x}%`}
              y2={`${task.position.y}%`}
              stroke="white"
              strokeOpacity="0.15"
              strokeWidth="1"
              strokeDasharray="4 4" 
            >
              <animate attributeName="stroke-opacity" values="0.1;0.3;0.1" dur="4s" repeatCount="indefinite" />
            </line>
          );
        })}
      </svg>

      {/* Interactive Stars Layer */}
      {tasks.map(task => (
        <Star 
          key={task.id} 
          task={task} 
          onClick={onTaskClick} 
          onDragStart={(e) => handleDragStart(task.id, e)}
          isDragging={draggingId === task.id}
        />
      ))}

      {/* Header UI Layer */}
      <div className="absolute top-0 left-0 w-full p-6 z-40 flex flex-col gap-4 pointer-events-none">
        
        {/* Title & Stats */}
        <div className="flex justify-between items-start">
            <div className="pointer-events-auto">
                <h1 className="text-4xl font-display font-light text-white/90 tracking-wide drop-shadow-md flex items-center gap-3">
                    {getTitle()}
                    {timeScope === 'METEOR' && <Sparkles size={24} className="text-star-gold animate-pulse" />}
                </h1>
                <p className="text-white/50 text-sm mt-1">
                    {getDescription()}
                </p>
                {timeScope !== 'METEOR' && (
                  <p className="text-white/30 text-xs mt-2">
                    * 별을 드래그해서 위치를 옮길 수 있습니다
                  </p>
                )}
            </div>
        </div>

        {/* Time Scope Tabs */}
        <div className="flex flex-wrap gap-2 self-start pointer-events-auto">
          <div className="flex bg-space-800/50 backdrop-blur-md rounded-full p-1 border border-white/10 shadow-lg">
              {(['DAILY', 'WEEKLY', 'MONTHLY'] as TimeScope[]).map((scope) => (
                  <button
                      key={scope}
                      onClick={() => onTimeScopeChange(scope)}
                      className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all ${
                          timeScope === scope 
                          ? 'bg-white text-space-900 shadow-sm' 
                          : 'text-slate-400 hover:text-white'
                      }`}
                  >
                      {scope === 'DAILY' ? '오늘' : scope === 'WEEKLY' ? '이번 주' : '이번 달'}
                  </button>
              ))}
          </div>
          
          {/* Meteor Tab (Separate visually) */}
          <button
            onClick={() => onTimeScopeChange('METEOR')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium transition-all border shadow-lg ${
                timeScope === 'METEOR'
                ? 'bg-star-purple text-white border-star-purple shadow-star-purple/30'
                : 'bg-space-800/50 backdrop-blur-md text-slate-300 border-white/10 hover:border-star-purple/50 hover:text-star-purple'
            }`}
          >
            <Sparkles size={12} />
            별똥별
          </button>
        </div>

      </div>

    </div>
  );
};