'use client';

import React, { FC, useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { StatusUpdate } from '@/lib/types';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

interface ProcessingStatusCardProps {
    statusUpdates: StatusUpdate[];
    visible: boolean;
    responseStartTime?: Date;
}

// Map of status keys to user-friendly messages
const statusLabels: Record<string, string> = {
    'retrieve_context': 'Retrieving relevant documents...',
    'analyzing_query': 'Analyzing your query...',
    'finding_relevant_documents': 'Finding relevant documents...',
    'rerank_context_one_step': 'Reviewing documents for relevance...',
    'aegis_rerank_context': 'Carefully reviewing every document retrieved...',
    'preparing_response': 'Preparing response...',
    'test_message': '🧪 Test message received!',
    'responding': 'Generating response...',
};

const ProcessingStatusCard: FC<ProcessingStatusCardProps> = ({
    statusUpdates,
    visible,
    responseStartTime,
}) => {
    const [expanded, setExpanded] = useState(false);
    const [currentMessage, setCurrentMessage] = useState('');
    const [previousMessage, setPreviousMessage] = useState('');
    const [transitioning, setTransitioning] = useState(false);
    const timeoutRef = useRef<NodeJS.Timeout | null>(null);
    const historyListRef = useRef<HTMLDivElement>(null);

    // Scroll to bottom of history list when expanded changes or new items are added
    useEffect(() => {
        if (expanded && historyListRef.current) {
            // Scroll to the bottom to show newest messages
            historyListRef.current.scrollTop = historyListRef.current.scrollHeight;
        }
    }, [expanded, statusUpdates]);

    // Calculate thinking time if we have a responseStartTime
    const calculateThinkingTime = () => {
        if (!responseStartTime || statusUpdates.length === 0) return null;

        const firstUpdateTime = statusUpdates[0].timestamp;
        const thinkingTimeMs = responseStartTime.getTime() - firstUpdateTime.getTime();
        const thinkingTimeSec = thinkingTimeMs / 1000;

        // Return thinking time with one decimal place
        return thinkingTimeSec.toFixed(1);
    };

    const thinkingTime = calculateThinkingTime();

    // Process status updates to get messages
    useEffect(() => {
        if (statusUpdates.length === 0 || !visible) {
            setCurrentMessage('');
            setPreviousMessage('');
            return;
        }

        const latestUpdate = statusUpdates[statusUpdates.length - 1];

        // First check if we have a direct message from the update (added by RabbitMQ service)
        if (latestUpdate.message) {
            if (currentMessage !== latestUpdate.message) {
                // If we already have a current message, move it to previous
                if (currentMessage) {
                    setPreviousMessage(currentMessage);
                    setTransitioning(true);
                }

                // Set the new message
                setCurrentMessage(latestUpdate.message);

                // Clear transition state after animation
                if (timeoutRef.current) clearTimeout(timeoutRef.current);
                timeoutRef.current = setTimeout(() => {
                    setTransitioning(false);
                }, 500); // match transition duration
            }
            return;
        }

        // If no direct message, try to parse status if it's a JSON string
        const statusKey = latestUpdate.status.trim();
        try {
            const parsedStatus = JSON.parse(statusKey);
            if (parsedStatus.message && typeof parsedStatus.message === 'string') {
                // If we already have a current message, move it to previous
                if (currentMessage !== parsedStatus.message) {
                    if (currentMessage) {
                        setPreviousMessage(currentMessage);
                        setTransitioning(true);
                    }

                    // Set the new message
                    setCurrentMessage(parsedStatus.message);

                    // Clear transition state after animation
                    if (timeoutRef.current) clearTimeout(timeoutRef.current);
                    timeoutRef.current = setTimeout(() => {
                        setTransitioning(false);
                    }, 500); // match transition duration
                }
                return;
            }
        } catch (e) {
            // Not JSON, continue with normal status mapping
        }

        // Get message from status labels or use raw status
        const newMessage = statusLabels[statusKey] || `${statusKey}`;

        // Only update if message changed
        if (newMessage !== currentMessage) {
            // Move current message to previous
            if (currentMessage) {
                setPreviousMessage(currentMessage);
                setTransitioning(true);
            }

            // Set new message
            setCurrentMessage(newMessage);

            // Clear transition state after animation
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            timeoutRef.current = setTimeout(() => {
                setTransitioning(false);
            }, 500); // match transition duration
        }
    }, [statusUpdates, visible, currentMessage]);

    // Clean up timeout on unmount
    useEffect(() => {
        return () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
        };
    }, []);

    if (!visible || statusUpdates.length === 0) return null;

    return (
        <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-2 mt-1 px-4"
        >
            <div className="relative rounded-lg border border-gray-200 dark:border-gray-700/50 bg-gray-50/90 dark:bg-gray-800/30 shadow-sm overflow-hidden backdrop-blur-sm">
                {/* Header with current status and toggle */}
                <div
                    className="p-3 flex items-center justify-between cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700/20 transition-colors duration-200"
                    onClick={() => setExpanded(!expanded)}
                >
                    <div className="flex-1 overflow-hidden relative h-6">
                        {/* Previous message (fading out) */}
                        <AnimatePresence>
                            {transitioning && previousMessage && (
                                <motion.div
                                    key="previous"
                                    initial={{ opacity: 1, x: 0 }}
                                    animate={{ opacity: 0, x: -30 }}
                                    exit={{ opacity: 0, x: -30 }}
                                    transition={{ duration: 0.35 }}
                                    className="absolute inset-0 flex items-center text-gray-600 dark:text-gray-300 text-sm"
                                >
                                    {previousMessage}
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* Current message (fading in) */}
                        <motion.div
                            key="current"
                            initial={{ opacity: transitioning ? 0 : 1, x: transitioning ? 30 : 0 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.5 }}
                            className="absolute inset-0 flex items-center text-gray-700 dark:text-gray-200 text-sm"
                        >
                            <span className="relative mr-2 h-2 w-2 flex-shrink-0">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-500"></span>
                            </span>
                            {currentMessage}
                        </motion.div>
                    </div>
                    <div className="text-gray-500 dark:text-gray-400 ml-2">
                        {expanded ?
                            <ChevronUpIcon className="h-4 w-4" /> :
                            <ChevronDownIcon className="h-4 w-4" />
                        }
                    </div>
                </div>

                {/* Expanded view with history */}
                <AnimatePresence>
                    {expanded && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.3 }}
                        >
                            <div className="px-3 pb-3 border-t border-gray-200 dark:border-gray-700">
                                <div
                                    ref={historyListRef}
                                    className="pt-2 space-y-2 max-h-48 overflow-y-auto"
                                >
                                    {/* Display in chronological order - oldest first, newest last */}
                                    {statusUpdates.map((update, index) => {
                                        // First check if we have a direct message from the update
                                        let displayMessage = update.message;

                                        // If no direct message, try to parse status if it's a JSON string
                                        if (!displayMessage) {
                                            try {
                                                const parsedStatus = JSON.parse(update.status.trim());
                                                displayMessage = parsedStatus.message || statusLabels[parsedStatus.status] || parsedStatus.status;
                                            } catch {
                                                displayMessage = statusLabels[update.status.trim()] || update.status;
                                            }
                                        }

                                        // Skip empty messages
                                        if (!displayMessage) return null;

                                        return (
                                            <div key={index} className="flex items-start text-xs">
                                                <span className="h-1.5 w-1.5 rounded-full bg-gray-400 dark:bg-gray-500 mt-1.5 mr-2 flex-shrink-0"></span>
                                                <div className="flex-1">
                                                    <div className="text-gray-700 dark:text-gray-300">{displayMessage}</div>
                                                    <div className="text-gray-500 dark:text-gray-400 text-xs mt-0.5">
                                                        {update.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>

                                {/* Thinking time footer */}
                                {thinkingTime && (
                                    <div className="mt-3 pt-2 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400 flex items-center justify-center">
                                        <svg className="w-3 h-3 mr-1" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M12 8V12L15 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                                            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
                                        </svg>
                                        Thought for {thinkingTime} seconds
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </motion.div>
    );
};

export default ProcessingStatusCard; 