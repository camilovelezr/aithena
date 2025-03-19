'use client';

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import MessageItem from './MessageItem';
import StatusIndicator from './StatusIndicator';
import { useChatStore } from '@/store/chatStore';
import { askAithena, parseStreamingResponse } from '@/services/api';
import { useRabbitMQ } from '@/services/rabbitmq';
import { AIMode } from '@/lib/types';

interface ChatProps {
    mode: AIMode;
}

const Chat: React.FC<ChatProps> = ({ mode }) => {
    const [query, setQuery] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const { messages, loading, error, addMessage, updateLastAssistantMessage, addReferencesToLastAssistantMessage, setLoading, setError } = useChatStore();
    const { clearStatusUpdates, statusUpdates } = useRabbitMQ();

    // Track if we should hide status updates (after responding status is received)
    const [hideStatusAfterResponding, setHideStatusAfterResponding] = useState(false);
    const [mounted, setMounted] = useState(false);

    // Calculate the line height of the textarea dynamically
    const [lineHeight, setLineHeight] = useState(20); // Default estimate
    const maxLines = 10; // Show scrollbar after ~10 lines

    // Reset hide status when starting a new query
    useEffect(() => {
        // Mark as mounted to prevent hydration issues
        setMounted(true);

        if (!loading) {
            setHideStatusAfterResponding(false);
        }

        // Calculate accurate line height when component mounts
        if (mounted && textareaRef.current) {
            // Create a single line of text to measure height
            const originalValue = textareaRef.current.value;
            textareaRef.current.value = 'x';
            textareaRef.current.style.height = 'auto';
            const singleLineHeight = textareaRef.current.scrollHeight;

            // Add a new line to measure the difference
            textareaRef.current.value = 'x\nx';
            textareaRef.current.style.height = 'auto';
            const doubleLineHeight = textareaRef.current.scrollHeight;

            // Calculate actual line height
            const calculatedLineHeight = doubleLineHeight - singleLineHeight;
            setLineHeight(calculatedLineHeight > 0 ? calculatedLineHeight : 20);

            // Restore original value
            textareaRef.current.value = originalValue;
            resizeTextarea();
        }
    }, [loading, mounted]);

    // Resize textarea based on content
    const resizeTextarea = () => {
        if (!textareaRef.current) return;

        const textarea = textareaRef.current;
        textarea.style.height = 'auto';

        const maxHeight = lineHeight * maxLines;
        const newHeight = Math.min(textarea.scrollHeight, maxHeight);
        textarea.style.height = newHeight + 'px';

        // Add or remove overflow class based on content height
        if (textarea.scrollHeight > maxHeight) {
            textarea.classList.add('overflow');
        } else {
            textarea.classList.remove('overflow');
        }
    };

    // Check for 'responding' status and hide indicator when found
    useEffect(() => {
        if (statusUpdates.length > 0) {
            const latestStatus = statusUpdates[statusUpdates.length - 1].status;
            if (latestStatus === 'responding') {
                setHideStatusAfterResponding(true);
            }
        }
    }, [statusUpdates]);

    // Scroll to bottom when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim() || loading) return;

        // Store query before clearing the input
        const submittedQuery = query;

        // Clear input immediately
        setQuery('');

        // Clear previous status updates
        clearStatusUpdates();

        // Add user message
        addMessage({ content: submittedQuery, role: 'user' });

        // Create empty assistant message to show typing indicator
        addMessage({ content: '', role: 'assistant' });

        // Set loading state
        setLoading(true);
        setError(null);

        try {
            const response = await askAithena(submittedQuery, mode);

            // Start streaming
            const streamParser = parseStreamingResponse(response);
            let fullText = '';
            let referencesPart = '';
            let captureReferences = false;

            for await (const chunk of streamParser) {
                if (captureReferences) {
                    // Already in references mode, continue collecting
                    referencesPart += chunk;
                } else if (chunk.includes('\n\n\n')) {
                    // Found the separator, split the chunk
                    captureReferences = true;
                    const [beforeSeparator, afterSeparator] = chunk.split('\n\n\n', 2);
                    // Preserve line breaks exactly as they come from the LLM
                    fullText += beforeSeparator;
                    if (afterSeparator) {
                        referencesPart = afterSeparator;
                    }
                    updateLastAssistantMessage(fullText);
                } else {
                    // Normal content - preserve original formatting including line breaks
                    fullText += chunk;
                    updateLastAssistantMessage(fullText);
                }
            }

            // Apply references if found
            if (referencesPart.trim()) {
                console.log("References found, length:", referencesPart.trim().length);

                try {
                    // Parse the JSON references
                    const referencesData = JSON.parse(referencesPart.trim());
                    console.log("Parsed references data:", referencesData);

                    // Pass the structured data directly to the store
                    addReferencesToLastAssistantMessage(referencesPart.trim());
                } catch (error) {
                    console.error("Failed to parse references JSON:", error);

                    // Fallback to old format handling if JSON parsing fails
                    let cleanedReferences = referencesPart.trim();
                    console.log("Falling back to text references format:", cleanedReferences);

                    // Format as HTML for backwards compatibility
                    cleanedReferences = `<div class="legacy-references-format">${cleanedReferences}</div>`;
                    addReferencesToLastAssistantMessage(cleanedReferences);
                }
            } else {
                console.warn("No references found in response");
            }
        } catch (err) {
            setError('Failed to get response. Please try again.');
            console.error('Error during chat:', err);
        } finally {
            setLoading(false);
        }
    };

    // Don't render anything until mounted to prevent hydration mismatch
    if (!mounted) return null;

    return (
        <div className="flex flex-col h-full relative">
            <div className="flex-1 overflow-y-auto [&::-webkit-scrollbar]:w-[60px] [&::-webkit-scrollbar-thumb]:bg-gray-500 dark:[&::-webkit-scrollbar-thumb]:bg-gray-600 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:border-[24px] [&::-webkit-scrollbar-thumb]:border-solid [&::-webkit-scrollbar-thumb]:border-transparent [&::-webkit-scrollbar-thumb]:bg-clip-padding [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:min-h-[40px]">
                {messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full px-4">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5 }}
                            className="text-center max-w-xl w-full mx-auto bg-white dark:bg-[#1a2234] rounded-2xl shadow-lg shadow-black/5 dark:shadow-black/20 p-6 backdrop-blur-sm border border-gray-100 dark:border-gray-800/50"
                        >
                            <div className="mb-6">
                                <h2 className="text-3xl font-bold mb-3 text-gray-900 dark:text-white">Welcome to AskAithena</h2>
                                <p className="text-gray-600 dark:text-gray-300 text-lg leading-relaxed">
                                    Your intelligent research assistant. Ask any question and I'll provide detailed, evidence-based answers with references to scientific sources.
                                </p>
                            </div>
                            {/* <div className="space-y-3">
                                <motion.div
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: 0.2 }}
                                    className="text-left p-4 rounded-xl bg-gradient-to-r from-gray-50 to-gray-100 dark:from-[#141b2d] dark:to-[#1a2234] cursor-pointer hover:shadow-md transition-all duration-300"
                                    onClick={() => {
                                        setQuery("How does Aithena's context retrieval work?");
                                        setTimeout(() => {
                                            handleSubmit({ preventDefault: () => { } } as React.FormEvent);
                                        }, 100);
                                    }}
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 rounded-lg bg-primary-500/10 dark:bg-primary-400/10">
                                            <svg className="w-5 h-5 text-primary-500 dark:text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                            </svg>
                                        </div>
                                        <span className="text-gray-800 dark:text-gray-200">How does Aithena's context retrieval work?</span>
                                    </div>
                                </motion.div>
                                <motion.div
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: 0.4 }}
                                    className="text-left p-4 rounded-xl bg-gradient-to-r from-gray-50 to-gray-100 dark:from-[#141b2d] dark:to-[#1a2234] cursor-pointer hover:shadow-md transition-all duration-300"
                                    onClick={() => {
                                        setQuery("What's the difference between Owl, Shield, and Aegis modes?");
                                        setTimeout(() => {
                                            handleSubmit({ preventDefault: () => { } } as React.FormEvent);
                                        }, 100);
                                    }}
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 rounded-lg bg-primary-500/10 dark:bg-primary-400/10">
                                            <svg className="w-5 h-5 text-primary-500 dark:text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                            </svg>
                                        </div>
                                        <span className="text-gray-800 dark:text-gray-200">What's the difference between Owl, Shield, and Aegis modes?</span>
                                    </div>
                                </motion.div>
                            </div> */}
                        </motion.div>
                    </div>
                ) : (
                    <div className="pt-4 pb-2 px-4">
                        <div className="max-w-4xl mx-auto">
                            {messages.map((message) => {
                                // Don't show the last assistant message if we haven't received 'responding' status yet
                                if (loading && message.role === 'assistant' && message === messages[messages.length - 1] && !hideStatusAfterResponding) {
                                    return null;
                                }
                                return <MessageItem key={message.id} message={message} />;
                            })}
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <AnimatePresence>
                {loading && !hideStatusAfterResponding && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 20 }}
                        className="flex justify-center"
                    >
                        <div className="w-full max-w-4xl px-4">
                            <StatusIndicator
                                statusUpdates={statusUpdates}
                                visible={loading && statusUpdates.length > 0}
                            />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {error && (
                <div className="flex justify-center">
                    <div className="w-full max-w-4xl px-4">
                        <div className="bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-600 text-red-800 dark:text-red-200 p-3 rounded-md mb-4">
                            {error}
                        </div>
                    </div>
                </div>
            )}

            <div className="pt-4 pb-2 px-4">
                <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
                    <div className="relative flex items-center gap-2">
                        <div className="flex-1 relative flex items-center">
                            <textarea
                                ref={textareaRef}
                                value={query}
                                onChange={(e) => {
                                    setQuery(e.target.value);
                                    resizeTextarea();
                                }}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSubmit(e as unknown as React.FormEvent);
                                    }
                                }}
                                placeholder={`Ask a question in ${mode} mode...`}
                                className="w-full bg-white dark:bg-[#1a2234] border border-gray-200 dark:border-gray-800/50 text-gray-900 dark:text-white px-4 py-3.5 pr-12 rounded-xl focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none resize-none min-h-[50px] overflow-hidden shadow-sm transition-[background,border,shadow] duration-200 ease-in-out hover:shadow-md [&.overflow]:overflow-y-auto [&.overflow]:scrollbar [&.overflow]:scrollbar-w-3 [&.overflow]:scrollbar-thumb-gray-300 dark:[&.overflow]:scrollbar-thumb-gray-600 [&.overflow]:scrollbar-track-transparent [&.overflow]:hover:scrollbar-thumb-gray-400 dark:[&.overflow]:hover:scrollbar-thumb-gray-500"
                                disabled={loading}
                                rows={1}
                            />
                            {!loading && query.trim() && (
                                <motion.div
                                    initial={{ scale: 0.8, opacity: 0 }}
                                    animate={{ scale: 1, opacity: 1 }}
                                    exit={{ scale: 0.8, opacity: 0 }}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 z-10"
                                >
                                    <button
                                        type="submit"
                                        aria-label="Send message"
                                        className="p-3 rounded-full text-gray-900 dark:text-white transition-all duration-200 active:scale-95 cursor-pointer"
                                        onClick={(e) => {
                                            e.preventDefault();
                                            handleSubmit(e);
                                        }}
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                            <path d="m22 2-7 20-4-9-9-4Z" />
                                            <path d="M22 2 11 13" />
                                        </svg>
                                    </button>
                                </motion.div>
                            )}
                            {loading && (
                                <motion.div
                                    initial={{ scale: 0.8, opacity: 0 }}
                                    animate={{ scale: 1, opacity: 1 }}
                                    exit={{ scale: 0.8, opacity: 0 }}
                                    className="absolute right-2 top-1/2 -translate-y-1/2"
                                >
                                    <div className="p-2.5">
                                        <svg className="animate-spin h-[18px] w-[18px] text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                    </div>
                                </motion.div>
                            )}
                        </div>
                    </div>
                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="mt-2 text-xs text-gray-500 dark:text-gray-400"
                    >
                        Press Enter to send, Shift + Enter for new line
                    </motion.p>
                </form>
            </div>
        </div>
    );
};

// interface SuggestedQuestionProps {
//     text: string;
//     onClick: () => void;
// }

// const SuggestedQuestion: React.FC<SuggestedQuestionProps> = ({ text, onClick }) => (
//     <button
//         onClick={onClick}
//         className="text-left p-3 border border-gray-700 rounded-md bg-dark-100 hover:bg-dark-100/70 transition-colors text-gray-300"
//     >
//         {text}
//     </button>
// );

export default Chat; 