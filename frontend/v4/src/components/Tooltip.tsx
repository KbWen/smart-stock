import React, { useId, useState } from 'react';

interface TooltipProps {
    content: string;
    children: React.ReactNode;
}

const Tooltip: React.FC<TooltipProps> = ({ content, children }) => {
    const [isVisible, setIsVisible] = useState(false);
    const tooltipId = useId();

    const handleToggle = (e: React.MouseEvent<HTMLDivElement>) => {
        e.stopPropagation();
        e.preventDefault();
        setIsVisible((prev) => !prev);
    };

    return (
        <div
            className="relative inline-block cursor-help group"
            tabIndex={0}
            onMouseEnter={() => setIsVisible(true)}
            onMouseLeave={() => setIsVisible(false)}
            onFocus={() => setIsVisible(true)}
            onBlur={() => setIsVisible(false)}
            onClick={handleToggle}
            aria-describedby={isVisible ? tooltipId : undefined}
        >
            {children}
            {isVisible && (
                <div
                    id={tooltipId}
                    role="tooltip"
                    className="absolute z-50 px-3 py-2 text-xs font-medium text-white bg-dark-card border border-dark-border rounded-lg shadow-2xl -top-1 left-1/2 transform -translate-x-1/2 -translate-y-full mb-2 w-48 transition-opacity duration-200 pointer-events-none"
                >
                    {content}
                    <div className="absolute w-2 h-2 bg-dark-card border-b border-r border-dark-border transform rotate-45 left-1/2 -translate-x-1/2 -bottom-1"></div>
                </div>
            )}
        </div>
    );
};

export default Tooltip;
