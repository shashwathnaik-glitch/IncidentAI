import React from 'react';
import { Inbox } from 'lucide-react';
import { Button } from './Button';

/**
 * Reusable Empty State Component
 */
export const EmptyState = ({
  icon: Icon = Inbox,
  title = 'No Records Found',
  description = 'There are no items matching your request.',
  actionLabel = null,
  onAction = null,
  actionIcon = null,
  className = ''
}) => {
  return (
    <div className={`p-12 text-center bg-slate-900/60 rounded-3xl border border-slate-800 backdrop-blur-xl text-slate-400 space-y-4 max-w-md mx-auto ${className}`}>
      <div className="w-14 h-14 bg-slate-800/80 border border-slate-700/60 rounded-2xl flex items-center justify-center mx-auto text-slate-400">
        <Icon className="w-7 h-7" />
      </div>

      <div>
        <h3 className="text-base font-bold text-slate-200">{title}</h3>
        <p className="text-xs text-slate-400 mt-1 leading-relaxed">{description}</p>
      </div>

      {actionLabel && onAction && (
        <Button
          variant="primary"
          size="sm"
          onClick={onAction}
          icon={actionIcon}
        >
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
