export enum Difficulty {
  EASY = '쉬움',
  MEDIUM = '보통',
  HARD = '어려움',
}

export enum Category {
  WORK = '업무',
  STUDY = '공부',
  HEALTH = '운동',
  LIFE = '생활',
  CREATIVE = '창작',
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  category: Category;
  difficulty: Difficulty;
  completed: boolean;
  createdAt: number;
  completedAt?: number;
  deadline?: number;
  // Visual properties
  position: { x: number; y: number }; // Percentages (0-100)
}

export type ViewMode = 'UNIVERSE' | 'LIST' | 'PROFILE';
export type TimeScope = 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'METEOR';

export interface StarConfig {
  size: number;
  color: string;
  glow: string;
}