import React from 'react';

interface WelcomeOverlayProps {
  onDismiss: () => void;
}

export const WelcomeOverlay: React.FC<WelcomeOverlayProps> = ({ onDismiss }) => {
  return (
    <div className="fixed inset-0 z-[100] bg-space-900/90 backdrop-blur-md flex items-center justify-center p-6 text-center animate-fade-in">
        <div className="max-w-md">
            <h1 className="text-4xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-300 via-purple-300 to-white mb-4">
                Stardust에 오신 것을<br/>환영합니다
            </h1>
            <p className="text-slate-300 text-lg mb-8 leading-relaxed">
                당신의 할 일은 태어나기를 기다리는 별들입니다.<br/>
                할 일을 완료하여 우주를 밝히고<br/>아름다운 별자리를 만들어보세요.
            </p>
            <button 
                onClick={onDismiss}
                className="bg-white text-space-900 font-bold px-8 py-3 rounded-full hover:scale-105 transition-transform shadow-[0_0_20px_rgba(255,255,255,0.3)]"
            >
                여정 시작하기
            </button>
        </div>
    </div>
  );
};