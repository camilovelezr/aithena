'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRabbitMQ } from '@/services/rabbitmq';
import StatusIndicator from './StatusIndicator';
import { API_URL } from '@/lib/env';
import { useApiHealth } from '@/services/api';

interface DebugSectionProps {
    title: string;
    children: React.ReactNode;
    defaultOpen?: boolean;
}

const DebugSection: React.FC<DebugSectionProps> = ({ title, children, defaultOpen = false }) => {
    const [isOpen, setIsOpen] = useState(defaultOpen);
    const contentRef = React.useRef<HTMLDivElement>(null);
    const [contentHeight, setContentHeight] = useState<number>(0);

    useEffect(() => {
        if (contentRef.current) {
            setContentHeight(contentRef.current.scrollHeight);
        }
    }, [children]);

    return (
        <div className="mb-4 rounded-xl overflow-hidden bg-white dark:bg-[#1e293b] border border-gray-200/50 dark:border-gray-700/50">
            <motion.button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full px-4 py-3 text-left flex justify-between items-center hover:bg-gray-100 dark:hover:bg-[#252f44] transition-colors focus-ring"
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                transition={{ duration: 0.2 }}
            >
                <span className="font-medium text-gray-900 dark:text-white">{title}</span>
                <motion.div
                    initial={false}
                    animate={{ rotate: isOpen ? 180 : 0 }}
                    transition={{ duration: 0.2, ease: [0.4, 0.0, 0.2, 1] }}
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="text-gray-500 dark:text-gray-400"
                    >
                        <path d="m6 9 6 6 6-6" />
                    </svg>
                </motion.div>
            </motion.button>
            <motion.div
                initial={false}
                animate={{
                    height: isOpen ? contentHeight : 0,
                    opacity: isOpen ? 1 : 0
                }}
                transition={{
                    duration: 0.3,
                    ease: [0.4, 0.0, 0.2, 1]
                }}
                className="overflow-hidden"
            >
                <div
                    ref={contentRef}
                    className="px-4 py-3 border-t border-gray-200/50 dark:border-gray-700/50 text-sm bg-gray-50 dark:bg-[#1a2234]"
                >
                    {children}
                </div>
            </motion.div>
        </div>
    );
};

interface SidebarProps {
    isOpen: boolean;
    onClose: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
    const { connected, statusUpdates, sendTestMessage, checkConnectionStatus } = useRabbitMQ();
    const { healthStatus, error: apiCheckError, loading: apiCheckLoading, refreshStatus } = useApiHealth(60000);

    // Force refresh of connection status
    const [connectionStatus, setConnectionStatus] = useState(connected);
    const [mounted, setMounted] = useState(false);

    // Client-side rendering only
    useEffect(() => {
        setMounted(true);
    }, []);

    // Force a connection check when the sidebar is opened
    useEffect(() => {
        if (isOpen) {
            // Force a heartbeat/check to make sure status is current
            const isConnected = checkConnectionStatus();
            console.log('Sidebar opened - immediate connection check:', isConnected);
            setConnectionStatus(isConnected);
        }
    }, [isOpen, checkConnectionStatus]);

    // Update connection status whenever the sidebar is opened or every 2 seconds
    useEffect(() => {
        if (isOpen) {
            // Check current connection status
            const checkConnection = () => {
                const isConnected = checkConnectionStatus();
                console.log('Debug panel - direct connection check:', isConnected);
                setConnectionStatus(isConnected);
            };

            // Set up interval to check connection
            const interval = setInterval(checkConnection, 2000);

            return () => clearInterval(interval);
        }
    }, [isOpen, checkConnectionStatus]);

    if (!mounted) return null;

    return (
        <>
            {/* Sidebar */}
            <motion.div
                className="fixed left-0 top-0 h-full w-80 bg-white dark:bg-[#1a2234] border-r border-gray-200/50 dark:border-gray-800/50 z-50 overflow-hidden"
                initial={{ x: '-100%' }}
                animate={{ x: isOpen ? 0 : '-100%' }}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            >
                <div className="h-full flex flex-col">
                    <div className="py-3 border-b border-gray-200/50 dark:border-gray-800/50">
                        <div className="h-14 px-4 flex items-center justify-between">
                            <motion.h2
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: 0.1 }}
                                className="text-xl font-bold text-gray-900 dark:text-white"
                            >
                                Debug Panel
                            </motion.h2>
                            <motion.button
                                onClick={onClose}
                                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-200 transition-colors text-gray-600 dark:text-gray-400 focus-ring"
                                whileHover={{ scale: 1.1 }}
                                whileTap={{ scale: 0.9 }}
                            >
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    width="18"
                                    height="18"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                >
                                    <path d="M18 6 6 18" />
                                    <path d="m6 6 12 12" />
                                </svg>
                            </motion.button>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                        <DebugSection title="RabbitMQ Status">
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className="text-gray-700 dark:text-gray-300">Connection:</span>
                                    <span className={`font-medium ${connectionStatus ? 'text-green-500' : 'text-red-500'}`}>
                                        {connectionStatus ? 'Connected' : 'Disconnected'}
                                    </span>
                                </div>
                                <motion.button
                                    onClick={() => sendTestMessage()}
                                    className="w-full bg-white hover:bg-gray-100 dark:bg-[#252f44] dark:hover:bg-[#2b374d] text-gray-900 dark:text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-ring"
                                    disabled={!connectionStatus}
                                    whileHover={connectionStatus ? { scale: 1.02 } : {}}
                                    whileTap={connectionStatus ? { scale: 0.98 } : {}}
                                >
                                    Send Test Message
                                </motion.button>
                            </div>
                        </DebugSection>

                        <DebugSection title="API Status">
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className="text-gray-700 dark:text-gray-300">Status:</span>
                                    <span className={`font-medium ${healthStatus.status === 'ok' ? 'text-green-500' : 'text-red-500'}`}>
                                        {healthStatus.status} {apiCheckLoading && '(checking...)'}
                                    </span>
                                </div>

                                {healthStatus.litellm && (
                                    <div className="flex items-center justify-between">
                                        <span className="text-gray-700 dark:text-gray-300">LiteLLM:</span>
                                        <span className={`font-medium ${healthStatus.litellm === 'connected' ? 'text-green-500' : 'text-red-500'}`}>
                                            {healthStatus.litellm}
                                        </span>
                                    </div>
                                )}

                                {healthStatus.api && (
                                    <div className="flex items-center justify-between">
                                        <span className="text-gray-700 dark:text-gray-300">API Server:</span>
                                        <span className={`font-medium ${healthStatus.api === 'running' ? 'text-green-500' : 'text-red-500'}`}>
                                            {healthStatus.api}
                                        </span>
                                    </div>
                                )}

                                {apiCheckError && (
                                    <div className="p-2 rounded-lg bg-red-100 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-xs">
                                        Error: {apiCheckError}
                                    </div>
                                )}

                                <motion.button
                                    onClick={refreshStatus}
                                    className="w-full bg-white hover:bg-gray-100 dark:bg-[#252f44] dark:hover:bg-[#2b374d] text-gray-900 dark:text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-ring"
                                    disabled={apiCheckLoading}
                                    whileHover={!apiCheckLoading ? { scale: 1.02 } : {}}
                                    whileTap={!apiCheckLoading ? { scale: 0.98 } : {}}
                                >
                                    {apiCheckLoading ? 'Checking...' : 'Refresh API Status'}
                                </motion.button>
                            </div>
                        </DebugSection>

                        <DebugSection title="Environment">
                            <div className="space-y-3 text-sm">
                                <div className="p-3 rounded-lg bg-white dark:bg-[#252f44]">
                                    <div className="text-gray-500 dark:text-gray-400 mb-1">API URL</div>
                                    <div className="text-gray-900 dark:text-white break-all font-mono text-xs">{API_URL}</div>
                                </div>
                                <div className="p-3 rounded-lg bg-white dark:bg-[#252f44]">
                                    <div className="text-gray-500 dark:text-gray-400 mb-1">Environment</div>
                                    <div className="text-gray-900 dark:text-white font-mono text-xs">{process.env.NODE_ENV}</div>
                                </div>
                            </div>
                        </DebugSection>

                        <DebugSection title="RabbitMQ Messages">
                            <div className="max-h-40 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-700 scrollbar-track-transparent rounded-lg">
                                {statusUpdates.length > 0 ? (
                                    <StatusIndicator
                                        statusUpdates={statusUpdates}
                                        visible={true}
                                        compact={true}
                                        showAll={true}
                                    />
                                ) : (
                                    <p className="text-gray-500 dark:text-gray-400 text-sm text-center py-4">No messages received yet</p>
                                )}
                            </div>
                        </DebugSection>
                    </div>
                </div>
            </motion.div>
        </>
    );
};

export default Sidebar; 