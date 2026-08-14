import React from 'react';

/**
 * Reusable Loading Skeleton Component with pulse animation
 */
export const Skeleton = ({
  variant = 'text',
  className = '',
  count = 1
}) => {
  const variantStyles = {
    text: 'h-4 w-full rounded-md bg-slate-800/80',
    title: 'h-6 w-3/4 rounded-lg bg-slate-800/80',
    avatar: 'h-10 w-10 rounded-full bg-slate-800/80',
    card: 'h-40 w-full rounded-2xl bg-slate-900/60 border border-slate-800/80',
    button: 'h-10 w-28 rounded-xl bg-slate-800/80'
  };

  const elements = Array.from({ length: count });

  return (
    <>
      {elements.map((_, idx) => (
        <div
          key={idx}
          className={`animate-pulse ${variantStyles[variant] || variantStyles.text} ${className}`}
        />
      ))}
    </>
  );
};
