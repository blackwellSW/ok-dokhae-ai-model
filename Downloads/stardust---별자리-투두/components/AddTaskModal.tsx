import React, { useState } from 'react';
import { Category, Difficulty, Task } from '../types';
import { X, Calendar } from 'lucide-react';
import { CATEGORY_HEX_COLORS } from '../constants';

interface AddTaskModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (task: Omit<Task, 'id' | 'createdAt' | 'position' | 'completed'>) => void;
}

export const AddTaskModal: React.FC<AddTaskModalProps> = ({ isOpen, onClose, onAdd }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<Category>(Category.WORK);
  const [difficulty, setDifficulty] = useState<Difficulty>(Difficulty.MEDIUM);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    
    onAdd({
      title,
      description,
      category,
      difficulty,
    });
    
    // Reset and close
    setTitle('');
    setDescription('');
    setCategory(Category.WORK);
    setDifficulty(Difficulty.MEDIUM);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-end sm:items-center justify-center pointer-events-none">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm pointer-events-auto" onClick={onClose} />
      
      <div className="w-full sm:w-[500px] bg-space-800 border-t sm:border border-white/10 sm:rounded-2xl p-6 pointer-events-auto transform transition-transform duration-300 animate-slide-up shadow-2xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-display font-semibold text-white">새로운 별</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">별의 이름 (할 일)</label>
            <input
              autoFocus
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-space-900 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-star-blue transition-colors"
              placeholder="무엇을 이루고 싶나요?"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">카테고리 (색상)</label>
            <div className="flex flex-wrap gap-2">
              {Object.values(Category).map((cat) => (
                <button
                  type="button"
                  key={cat}
                  onClick={() => setCategory(cat)}
                  className={`px-3 py-1.5 rounded-full text-sm border transition-all ${
                    category === cat
                      ? 'bg-white/10 border-white text-white shadow-inner'
                      : 'bg-transparent border-white/10 text-slate-400 hover:border-white/30'
                  }`}
                  style={{ borderColor: category === cat ? CATEGORY_HEX_COLORS[cat] : '' }}
                >
                  <span className="w-2 h-2 rounded-full inline-block mr-2" style={{ backgroundColor: CATEGORY_HEX_COLORS[cat] }}></span>
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">밝기 (난이도)</label>
            <div className="grid grid-cols-3 gap-3">
              {Object.values(Difficulty).map((diff) => (
                <button
                  type="button"
                  key={diff}
                  onClick={() => setDifficulty(diff)}
                  className={`py-2 rounded-lg text-sm border text-center transition-all ${
                    difficulty === diff
                      ? 'bg-white text-space-900 border-white font-medium'
                      : 'bg-space-900 border-white/10 text-slate-400'
                  }`}
                >
                  {diff}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={!title.trim()}
            className="w-full bg-white text-space-900 font-bold py-4 rounded-xl mt-4 hover:bg-slate-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            별 생성하기
          </button>
        </form>
      </div>
    </div>
  );
};