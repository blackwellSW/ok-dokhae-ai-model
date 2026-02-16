import React, { useEffect, useState } from 'react';

interface NotificationProps {
  message: string;
  duration?: number;
  onClose: () => void;
}

export const Notification: React.FC<NotificationProps> = ({ message, duration = 3000, onClose }) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Start animation
    requestAnimationFrame(() => {
        setIsVisible(true);
    });

    const timer = setTimeout(() => {
      setIsVisible(false);
      // Wait for fade out animation to finish before calling onClose
      setTimeout(onClose, 500); 
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  return (
    <div 
      className={`fixed top-32 left-1/2 transform -translate-x-1/2 z-[70] max-w-[90%] w-auto`}
    >
      <div 
        className={`
          px-6 py-4 rounded-2xl bg-space-800/80 backdrop-blur-md border border-white/20 shadow-[0_0_20px_rgba(255,255,255,0.15)]
          transition-all duration-700 ease-out flex flex-col items-center text-center
          ${isVisible ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 -translate-y-8 scale-95'}
        `}
      >
        <span className="text-xl mb-1">✨</span>
        <p className="text-white text-sm font-medium leading-relaxed font-display tracking-wide">
          {message}
        </p>
      </div>
    </div>
  );
};