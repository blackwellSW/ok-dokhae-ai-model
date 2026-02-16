import { Category, Difficulty, StarConfig } from './types';

export const CATEGORY_COLORS: Record<Category, string> = {
  [Category.WORK]: 'text-star-blue bg-star-blue/20 shadow-star-blue',
  [Category.STUDY]: 'text-star-purple bg-star-purple/20 shadow-star-purple',
  [Category.HEALTH]: 'text-star-green bg-star-green/20 shadow-star-green',
  [Category.LIFE]: 'text-star-orange bg-star-orange/20 shadow-star-orange',
  [Category.CREATIVE]: 'text-star-gold bg-star-gold/20 shadow-star-gold',
};

// Hex codes for Canvas rendering
export const CATEGORY_HEX_COLORS: Record<Category, string> = {
  [Category.WORK]: '#60A5FA',
  [Category.STUDY]: '#C084FC',
  [Category.HEALTH]: '#4ADE80',
  [Category.LIFE]: '#FB923C',
  [Category.CREATIVE]: '#FDE047',
};

export const DIFFICULTY_CONFIG: Record<Difficulty, StarConfig> = {
  [Difficulty.EASY]: { size: 4, color: 'opacity-70', glow: 'shadow-sm' },
  [Difficulty.MEDIUM]: { size: 6, color: 'opacity-90', glow: 'shadow-md' },
  [Difficulty.HARD]: { size: 10, color: 'opacity-100', glow: 'shadow-lg' },
};

export const MESSAGES = {
  empty: "오늘은 우주가 조용하네요.",
  progress: "별들이 형성되고 있습니다...",
  goodJob: "하늘이 점점 밝아지고 있어요!",
  excellent: "웅장한 별자리입니다!",
};

export const EMOTIONAL_MESSAGES = {
  created: [
    "당신의 새로운 다짐이 별이 되어 떠올랐습니다.",
    "이 작은 별이 당신의 밤을 묵묵히 지켜줄 거예요.",
    "우주에 새로운 빛을 심으셨군요. 시작이 반입니다.",
    "무언가를 시작하는 당신의 마음이 가장 아름답습니다.",
    "오늘의 작은 노력이 내일의 찬란한 은하수가 될 것입니다."
  ],
  completed: [
    "오늘 하루도 정말 고생 많았어요. 당신의 우주가 한층 더 밝아졌습니다.",
    "지친 하루 끝에 당신이 피운 별빛이 작은 위로가 되길 바랍니다.",
    "당신의 성실함이 밤하늘에 아름다운 궤적을 남겼습니다.",
    "잠시 쉬어가도 좋아요. 당신의 별들은 언제나 여기서 빛날 테니까요.",
    "오늘 당신이 이루어낸 빛은 결코 사라지지 않습니다. 편안한 밤 되세요."
  ]
};