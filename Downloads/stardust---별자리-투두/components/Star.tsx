import React from 'react';
import { Task } from '../types';
import { DIFFICULTY_CONFIG, CATEGORY_HEX_COLORS } from '../constants';

interface StarProps {
  task: Task;
  onClick: (task: Task) => void;
  onDragStart: (e: React.MouseEvent | React.TouchEvent) => void;
  isDragging: boolean;
}

export const Star: React.FC<StarProps> = ({ task, onClick, onDragStart, isDragging }) => {
  const config = DIFFICULTY_CONFIG[task.difficulty];
  const colorHex = CATEGORY_HEX_COLORS[task.category];

  // Calculate dynamic styles
  const sizePx = task.completed ? config.size * 3 : config.size * 2; 
  const opacity = task.completed ? 1 : 0.4;
  
  return (
    <div
      onMouseDown={onDragStart}
      onTouchStart={onDragStart}
      onClick={(e) => {
        // Prevent click if it was a drag (simple heuristic or controlled by parent could be better, 
        // but for now relying on click firing after mouseup)
        onClick(task);
      }}
      className={`absolute transition-transform duration-75 group z-20 ${isDragging ? 'scale-125 cursor-grabbing z-50' : 'cursor-grab'}`}
      style={{
        left: `${task.position.x}%`,
        top: `${task.position.y}%`,
        transform: 'translate(-50%, -50%)',
        // When dragging, we remove the smooth transition on top/left to make it responsive
        transitionProperty: isDragging ? 'transform' : 'all',
        transitionDuration: isDragging ? '0s' : '0.7s',
      }}
    >
      {/* Touch Hit Area (Larger) */}
      <div className="absolute -inset-4 bg-transparent" />

      {/* The Glow Effect for completed stars */}
      {task.completed && (
        <div 
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full animate-pulse-slow pointer-events-none"
          style={{
            width: `${sizePx * 4}px`,
            height: `${sizePx * 4}px`,
            background: `radial-gradient(circle, ${colorHex}66 0%, transparent 70%)`
          }}
        />
      )}

      {/* The Core Star */}
      <div
        className={`rounded-full relative ${task.completed && !isDragging ? 'animate-twinkle' : ''}`}
        style={{
          width: `${sizePx}px`,
          height: `${sizePx}px`,
          backgroundColor: task.completed ? colorHex : '#ffffff',
          opacity: opacity,
          boxShadow: task.completed ? `0 0 10px 2px ${colorHex}` : 'none'
        }}
      >
         {/* Label on Hover */}
         <div className={`absolute top-full left-1/2 -translate-x-1/2 mt-2 transition-opacity whitespace-nowrap bg-black/80 px-2 py-1 rounded text-xs text-white pointer-events-none z-30 ${isDragging ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
          {task.title}
         </div>
      </div>
    </div>
  );
};