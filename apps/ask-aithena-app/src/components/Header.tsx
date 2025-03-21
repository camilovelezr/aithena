'use client';

import React, { FC } from 'react';
import { AIMode } from '@/lib/types';
import { motion } from 'framer-motion';
import ThemeToggle from './ThemeToggle';

interface HeaderProps {
    currentMode: AIMode;
    onModeChange: (mode: AIMode) => void;
    onToggleSidebar: () => void;
}

const Header: FC<HeaderProps> = ({ currentMode, onModeChange, onToggleSidebar }) => {
    return (
        <motion.header
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="bg-white dark:bg-[#1a2234] sticky top-0 z-50 border-b border-gray-200/50 dark:border-gray-800/50 py-3"
        >
            <div className="container mx-auto px-4 flex items-center justify-between h-14">
                <div className="flex items-center gap-3">
                    <motion.button
                        onClick={onToggleSidebar}
                        className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white p-2 rounded-lg transition-colors hover:bg-gray-100 dark:hover:bg-[#252f44] focus-ring"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="20"
                            height="20"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        >
                            <line x1="3" y1="12" x2="21" y2="12" />
                            <line x1="3" y1="6" x2="21" y2="6" />
                            <line x1="3" y1="18" x2="21" y2="18" />
                        </svg>
                    </motion.button>
                    <motion.div
                        initial={{ scale: 0.5, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ delay: 0.1 }}
                        className="flex items-center gap-3"
                    >
                        <span className="material-symbols-outlined text-primary-500 dark:text-primary-400" style={{
                            fontSize: '24px',
                            transition: 'none !important',
                        }}>
                            owl
                        </span>
                        <motion.h1
                            className="text-xl font-bold text-gray-900 dark:text-white"
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.2 }}
                        >
                            Ask Aithena
                        </motion.h1>
                    </motion.div>
                </div>

                <div className="flex items-center gap-3">
                    <ThemeToggle />
                    <div className="p-1 bg-gray-100 dark:bg-[#0f172a] rounded-lg border border-gray-200/50 dark:border-gray-800/50 shadow-sm flex items-center">
                        <ModeButton
                            mode="owl"
                            currentMode={currentMode}
                            onModeChange={onModeChange}
                            label="Owl"
                        />
                        <ModeButton
                            mode="shield"
                            currentMode={currentMode}
                            onModeChange={onModeChange}
                            label="Shield"
                        />
                        <ModeButton
                            mode="aegis"
                            currentMode={currentMode}
                            onModeChange={onModeChange}
                            label="Aegis"
                        />
                    </div>
                </div>
            </div>
        </motion.header>
    );
};

interface ModeButtonProps {
    mode: AIMode;
    currentMode: AIMode;
    onModeChange: (mode: AIMode) => void;
    label: string;
}

const ModeButton: FC<ModeButtonProps> = ({
    mode,
    currentMode,
    onModeChange,
    label,
}) => {
    const isActive = mode === currentMode;

    return (
        <motion.button
            onClick={() => onModeChange(mode)}
            className={`relative px-3 py-1.5 rounded-md text-sm transition-all duration-200 focus-ring ${isActive
                ? 'text-white font-medium'
                : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'
                }`}
            whileHover={!isActive ? { scale: 1.05 } : {}}
            whileTap={!isActive ? { scale: 0.95 } : {}}
        >
            <span className="relative z-10">{label}</span>
            {isActive && (
                <motion.div
                    layoutId="activeMode"
                    className="absolute inset-0 rounded-md shadow-md dark:shadow-lg dark:shadow-primary-500/20"
                    style={{
                        background: 'linear-gradient(135deg, var(--primary-color) 0%, #0284c7 100%)',
                    }}
                    initial={false}
                    transition={{
                        type: 'spring',
                        stiffness: 200,
                        damping: 20
                    }}
                />
            )}
        </motion.button>
    );
};

export default Header; 