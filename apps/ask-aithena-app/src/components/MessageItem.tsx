'use client';

import React, { FC, useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { Message } from '@/lib/types';
import { useMarkdown } from '@/lib/hooks/useMarkdown';

// Define reference type
interface Reference {
    index: number;
    title: string;
    authors: string[];
    year: string | number;
    doi: string;
    id: string;
    score: number | null;
}

interface MessageItemProps {
    message: Message;
}

const MessageItem: FC<MessageItemProps> = ({ message }) => {
    const isUser = message.role === 'user';
    const [mounted, setMounted] = useState(false);
    const { processMarkdown } = useMarkdown();
    const [references, setReferences] = useState<Reference[]>([]);
    const messageContentRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        setMounted(true);

        // Parse references when component mounts
        if (message.references && !isUser) {
            try {
                const refs = JSON.parse(message.references) as Reference[];
                setReferences(refs);
            } catch (e) {
                console.error("Failed to parse references:", e);
            }
        }
    }, [message.references, isUser]);

    // Process citations after content is rendered
    useEffect(() => {
        if (mounted && !isUser && messageContentRef.current) {
            // Find all citation patterns in text nodes
            const findAndProcessCitations = () => {
                // Create a map of reference indexes for quick lookup
                const refMap = new Map(references.map(ref => [ref.index.toString(), ref]));

                // A flag to track if any citations were processed
                let citationsProcessed = false;

                // Process text nodes within the content
                const walkTextNodes = (node: Node) => {
                    if (node.nodeType === Node.TEXT_NODE) {
                        const text = node.textContent || '';
                        let modifiedText = text;
                        const fragment = document.createDocumentFragment();
                        let hasChanges = false;

                        // Combined regex for both patterns
                        // Matches both (1) and (1, 2, 3) patterns
                        const combinedRegex = /\((\d+(?:\s*,\s*\d+)*)\)/g;
                        let match;
                        let lastIndex = 0;

                        while ((match = combinedRegex.exec(text)) !== null) {
                            hasChanges = true;
                            citationsProcessed = true;
                            const fullMatch = match[0];  // e.g. "(1)" or "(1, 4, 9)"
                            const citationContent = match[1]; // e.g. "1" or "1, 4, 9"
                            const matchIndex = match.index;

                            // Add text before the citation
                            if (matchIndex > lastIndex) {
                                fragment.appendChild(document.createTextNode(text.substring(lastIndex, matchIndex)));
                            }

                            // Check if this is a grouped citation or individual citation
                            if (citationContent.includes(',')) {
                                // Grouped citation like (1, 4, 9)
                                const groupSpan = document.createElement('span');
                                groupSpan.className = 'citation-group';
                                groupSpan.style.opacity = '1'; // Set initial opacity

                                // Add opening parenthesis
                                groupSpan.appendChild(document.createTextNode('('));

                                // Process each number in the group
                                const citationNumbers = citationContent.split(',').map(n => n.trim());
                                citationNumbers.forEach((num, idx) => {
                                    const ref = refMap.get(num);

                                    // Create span for this citation
                                    const citationSpan = document.createElement('span');
                                    citationSpan.className = 'citation-ref';
                                    citationSpan.setAttribute('data-citation-id', num);
                                    citationSpan.textContent = num;
                                    citationSpan.style.opacity = '1'; // Set initial opacity

                                    // Add hover/click events if we have a matching reference
                                    if (ref) {
                                        addCitationEvents(citationSpan, ref);
                                    }

                                    // Add the citation span to the group
                                    groupSpan.appendChild(citationSpan);

                                    // Add comma if not the last item
                                    if (idx < citationNumbers.length - 1) {
                                        groupSpan.appendChild(document.createTextNode(', '));
                                    }
                                });

                                // Add closing parenthesis
                                groupSpan.appendChild(document.createTextNode(')'));

                                // Add the group span to the fragment
                                fragment.appendChild(groupSpan);
                            } else {
                                // Individual citation like (1)
                                const citationNumber = citationContent;

                                // Create the citation span
                                const citationSpan = document.createElement('span');
                                citationSpan.className = 'citation-ref';
                                citationSpan.setAttribute('data-citation-id', citationNumber);
                                citationSpan.textContent = fullMatch;
                                citationSpan.style.opacity = '1'; // Set initial opacity

                                // Add hover events only if we have a matching reference
                                const ref = refMap.get(citationNumber);
                                if (ref) {
                                    addCitationEvents(citationSpan, ref);
                                }

                                // Add the citation span to the fragment
                                fragment.appendChild(citationSpan);
                            }

                            // Update the last index
                            lastIndex = matchIndex + fullMatch.length;
                        }

                        // If we found matches, add any remaining text and replace the node
                        if (hasChanges) {
                            if (lastIndex < text.length) {
                                fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
                            }

                            node.parentNode?.replaceChild(fragment, node);
                            return true;
                        }
                    } else {
                        // Don't process code blocks or pre elements
                        const element = node as HTMLElement;
                        if (element.tagName === 'CODE' || element.tagName === 'PRE') {
                            return false;
                        }

                        // Process children recursively
                        const childNodes = Array.from(node.childNodes);
                        for (const child of childNodes) {
                            walkTextNodes(child);
                        }
                    }
                    return false;
                };

                // Helper function to add citation events (hover and click)
                const addCitationEvents = (citationSpan: HTMLElement, ref: Reference) => {
                    // Add hover events
                    citationSpan.addEventListener('mouseenter', (e) => {
                        createTooltip(e, ref);
                    });

                    citationSpan.addEventListener('mouseleave', () => {
                        removeTooltips();
                    });

                    // Add click event to open references and scroll to the citation
                    citationSpan.addEventListener('click', () => {
                        removeTooltips();

                        // Find the references details element
                        const detailsElement = document.querySelector('.references-content')?.parentElement;
                        if (detailsElement && detailsElement instanceof HTMLDetailsElement) {
                            // Open the details if it's closed
                            if (!detailsElement.open) {
                                detailsElement.open = true;
                            }

                            // Wait a tiny bit for the details to expand
                            setTimeout(() => {
                                // Find the reference element by index
                                const refElement = document.querySelector(`.reference-item[data-ref-index="${ref.index}"]`);
                                if (refElement) {
                                    // Scroll the reference into view with smooth behavior
                                    refElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                    // Add a temporary highlight effect
                                    refElement.classList.add('highlight-reference');
                                    setTimeout(() => {
                                        refElement.classList.remove('highlight-reference');
                                    }, 2000);
                                }
                            }, 50);
                        }
                    });

                    // Change cursor to indicate it's clickable
                    citationSpan.style.cursor = 'pointer';
                };

                // Start processing from the content root
                if (messageContentRef.current) {
                    walkTextNodes(messageContentRef.current);
                }
            };

            // Create tooltip for a reference
            const createTooltip = (e: MouseEvent, ref: Reference) => {
                // Remove existing tooltips first
                removeTooltips();

                const element = e.currentTarget as HTMLElement;

                // Create tooltip
                const tooltip = document.createElement('div');
                tooltip.className = 'citation-tooltip absolute z-50 bg-white/95 dark:bg-gray-950/98 shadow-lg rounded-md p-3.5 text-sm max-w-xs backdrop-blur-sm';

                // Position the tooltip based on element position
                const rect = element.getBoundingClientRect();
                const scrollTop = window.scrollY || document.documentElement.scrollTop;
                const scrollLeft = window.scrollX || document.documentElement.scrollLeft;

                // Calculate position to avoid going off-screen
                const viewportWidth = window.innerWidth;
                let left = rect.right + 5 + scrollLeft;

                // If tooltip would go off right edge, place it to the left of the citation
                if (left + 300 > viewportWidth) {
                    left = rect.left - 305 + scrollLeft;
                }

                tooltip.style.top = `${rect.top + scrollTop - 5}px`;
                tooltip.style.left = `${left}px`;

                tooltip.innerHTML = `
                    <div class="font-medium text-gray-900 dark:text-gray-100">${ref.title}</div>
                    ${ref.year ? `<div class="text-gray-700 dark:text-gray-300 text-xs mt-1">(${ref.year})</div>` : ''}
                    ${ref.authors && ref.authors.length > 0
                        ? `<div class="text-gray-700 dark:text-gray-300 text-xs mt-1.5 line-clamp-1">${ref.authors.join(', ')}</div>`
                        : ''}
                `;

                document.body.appendChild(tooltip);
            };

            // Remove all tooltips
            const removeTooltips = () => {
                const tooltips = document.querySelectorAll('.citation-tooltip');
                tooltips.forEach(t => t.remove());
            };

            // Run our citation processor with a short delay to ensure content is rendered
            setTimeout(findAndProcessCitations, 100);

            // Add listener for sidebar toggle to reprocess citations
            const handleReprocessCitations = () => {
                // Instead of removing and recreating all citation spans (which causes jerking),
                // we'll use a more efficient approach
                if (messageContentRef.current) {
                    // First, make all citations temporarily invisible to prevent flickering
                    const existingCitations = messageContentRef.current.querySelectorAll('.citation-ref, .citation-group');
                    existingCitations.forEach(citation => {
                        if (citation instanceof HTMLElement) {
                            // Save original opacity to restore later
                            citation.dataset.originalOpacity = citation.style.opacity || '1';
                            // Fade out smoothly
                            citation.style.transition = 'opacity 0.1s ease';
                            citation.style.opacity = '0';
                        }
                    });

                    // Wait for fade out to complete, then reprocess
                    setTimeout(() => {
                        // Now we can safely reprocess the citations
                        // Store the scroll position to restore it later
                        const scrollTop = window.scrollY || document.documentElement.scrollTop;

                        // Reset the HTML to remove citation spans
                        existingCitations.forEach(citation => {
                            const parent = citation.parentNode;
                            if (parent && parent instanceof HTMLElement && parent.classList && parent.classList.contains('citation-group')) {
                                // If this is in a citation group, replace the whole group with its text content
                                const textContent = parent.textContent || '';
                                const textNode = document.createTextNode(textContent);
                                parent.parentNode?.replaceChild(textNode, parent);
                            } else if (parent) {
                                // Otherwise just replace the citation with its text content
                                const textContent = citation.textContent || '';
                                const textNode = document.createTextNode(textContent);
                                parent.replaceChild(textNode, citation);
                            }
                        });

                        // Re-run the citation processor
                        findAndProcessCitations();

                        // Restore scroll position to prevent page jump
                        window.scrollTo({
                            top: scrollTop,
                            behavior: 'auto' // Use 'auto' to prevent animation
                        });

                        // Fade in the new citations
                        setTimeout(() => {
                            const newCitations = messageContentRef.current?.querySelectorAll('.citation-ref, .citation-group');
                            if (newCitations) {
                                newCitations.forEach(citation => {
                                    if (citation instanceof HTMLElement) {
                                        citation.style.transition = 'opacity 0.2s ease';
                                        citation.style.opacity = '0';
                                        // Trigger reflow
                                        citation.offsetHeight;
                                        // Fade in
                                        citation.style.opacity = '1';
                                    }
                                });
                            }
                        }, 0);
                    }, 100);
                }
            };

            document.addEventListener('reprocessCitations', handleReprocessCitations);

            // Clean up when unmounting
            return () => {
                removeTooltips();
                document.removeEventListener('reprocessCitations', handleReprocessCitations);
            };
        }
    }, [mounted, references, isUser]);

    // Don't render until client-side
    if (!mounted) return null;

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="mb-8 w-full"
            layout={false}
        >
            <div className="px-4">
                <motion.div
                    initial={{ opacity: 0, x: isUser ? 20 : -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 }}
                    className={`text-base font-medium mb-2 text-gray-700 dark:text-gray-300 flex items-baseline gap-2 ${isUser ? 'justify-end' : ''}`}
                    layout={false}
                >
                    {isUser ? (
                        <>
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                                {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                            <span>You</span>
                        </>
                    ) : (
                        <>
                            <span>Aithena</span>
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                                {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                        </>
                    )}
                </motion.div>

                <div className={`flex ${isUser ? 'justify-end' : ''}`}>
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        layout={false}
                        className={`p-5 rounded-2xl ${isUser
                            ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white shadow-lg inline-block max-w-[85%]'
                            : 'bg-white dark:bg-gray-800/80 text-gray-800 dark:text-gray-100 shadow-lg shadow-gray-500/10 dark:shadow-gray-900/20 border border-gray-100 dark:border-gray-700'
                            }`}
                    >
                        <div
                            ref={messageContentRef}
                            className={`${isUser ? 'text-gray-900 dark:text-white text-right' : 'text-gray-800 dark:text-gray-100'}`}
                        >
                            <ReactMarkdown
                                rehypePlugins={[rehypeHighlight, rehypeKatex]}
                                remarkPlugins={[remarkGfm, remarkMath]}
                                className={`prose dark:prose-invert max-w-none text-base whitespace-pre-line break-words ${isUser ? '!text-gray-900 dark:!text-white prose-headings:text-gray-900 dark:prose-headings:text-white prose-strong:text-gray-900 dark:prose-strong:text-white prose-code:text-gray-900 dark:prose-code:text-white' : ''}`}
                                components={{
                                    h1: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement> & { children: React.ReactNode }) => (
                                        <h1 className="text-2xl font-bold mt-3 mb-2 first:mt-0" {...props}>{children}</h1>
                                    ),
                                    h2: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement> & { children: React.ReactNode }) => (
                                        <h2 className="text-xl font-bold mt-3 mb-1.5" {...props}>{children}</h2>
                                    ),
                                    h3: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement> & { children: React.ReactNode }) => (
                                        <h3 className="text-lg font-bold mt-2 mb-1" {...props}>{children}</h3>
                                    ),
                                    h4: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement> & { children: React.ReactNode }) => (
                                        <h4 className="text-base font-bold mt-2 mb-1" {...props}>{children}</h4>
                                    ),
                                    h5: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement> & { children: React.ReactNode }) => (
                                        <h5 className="text-sm font-bold mt-2 mb-1" {...props}>{children}</h5>
                                    ),
                                    h6: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement> & { children: React.ReactNode }) => (
                                        <h6 className="text-sm font-bold mt-2 mb-1" {...props}>{children}</h6>
                                    ),
                                    p: ({ children, ...props }: React.HTMLAttributes<HTMLParagraphElement> & { children: React.ReactNode }) => (
                                        <p className="mt-0 mb-2 last:mb-0" {...props}>{children}</p>
                                    ),
                                    code: ({ className, children, inline, ...props }: { className?: string; children: React.ReactNode; inline?: boolean }) => {
                                        const match = /language-(\w+)/.exec(className || '');
                                        const language = match ? match[1] : '';

                                        return (
                                            <code
                                                className={`${className ?? ''} ${inline
                                                    ? `${isUser ? 'bg-gray-200 dark:bg-white/20' : 'bg-black/10 dark:bg-white/10'} rounded px-1.5 py-0.5`
                                                    : `${isUser ? 'bg-gray-200 dark:bg-white/20' : 'bg-black/5 dark:bg-white/5'} block rounded-lg p-3 my-2 language-${language}`
                                                    }`}
                                                {...props}
                                            >
                                                {children}
                                            </code>
                                        );
                                    },
                                    table: ({ children, ...props }: React.HTMLAttributes<HTMLTableElement> & { children: React.ReactNode }) => (
                                        <div className="overflow-x-auto my-3">
                                            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700" {...props}>
                                                {children}
                                            </table>
                                        </div>
                                    ),
                                    a: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { children: React.ReactNode; href?: string }) => (
                                        <a
                                            href={href}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-primary-500 hover:text-primary-600 dark:text-primary-400 dark:hover:text-primary-300 transition-colors"
                                            {...props}
                                        >
                                            {children}
                                        </a>
                                    ),
                                    li: ({ children, ...props }: React.LiHTMLAttributes<HTMLLIElement> & { children: React.ReactNode }) => (
                                        <li className="my-0.5" {...props}>
                                            {children}
                                        </li>
                                    ),
                                    ul: ({ children, ...props }: React.HTMLAttributes<HTMLUListElement> & { children: React.ReactNode }) => (
                                        <ul className="list-disc pl-6 my-1.5" {...props}>
                                            {children}
                                        </ul>
                                    ),
                                    ol: ({ children, ...props }: React.HTMLAttributes<HTMLOListElement> & { children: React.ReactNode }) => (
                                        <ol className="list-decimal pl-6 my-1.5" {...props}>
                                            {children}
                                        </ol>
                                    )
                                }}
                            >
                                {processMarkdown(message.content)}
                            </ReactMarkdown>

                            {/* Add CSS for citation hover effect */}
                            <style jsx global>{`
                                .citation-ref {
                                    color: #0070f3;
                                    cursor: pointer;
                                    font-weight: 600;
                                    position: relative;
                                    transition: all 0.3s ease;
                                    padding: 0 2px;
                                    border-radius: 3px;
                                    opacity: 1;
                                    will-change: opacity, background-color;
                                }
                                
                                .citation-group {
                                    display: inline;
                                    transition: opacity 0.3s ease;
                                    will-change: opacity;
                                }
                                
                                .citation-ref:hover {
                                    background-color: rgba(0, 112, 243, 0.1);
                                }
                                
                                .highlight-reference {
                                    animation: highlightFade 2s ease-out;
                                }
                                
                                @keyframes highlightFade {
                                    0%, 20% {
                                        background-color: rgba(0, 112, 243, 0.15);
                                    }
                                    100% {
                                        background-color: transparent;
                                    }
                                }
                                
                                .citation-tooltip {
                                    position: fixed;
                                    z-index: 9999;
                                    pointer-events: none;
                                    max-width: 300px;
                                    transition: all 0.2s ease;
                                    box-shadow: 0 10px 25px -5px rgba(0,0,0,0.2), 0 5px 10px -5px rgba(0,0,0,0.1);
                                    border: 1px solid rgba(226, 232, 240, 0.8);
                                    border-radius: 8px;
                                    animation: tooltipFadeIn 0.2s ease-out;
                                    backdrop-filter: blur(8px);
                                    -webkit-backdrop-filter: blur(8px);
                                    will-change: transform, opacity;
                                }
                                
                                .details-reset summary {
                                    list-style: none;
                                }
                                
                                .details-reset summary::-webkit-details-marker {
                                    display: none;
                                }
                                
                                .details-reset summary::before {
                                    content: '▼';
                                    display: inline-block;
                                    width: 20px;
                                    height: 20px;
                                    margin-left: 12px;
                                    margin-right: 16px;
                                    color: #64748b;
                                    font-size: 10px;
                                    text-align: center;
                                    transform: rotate(-90deg);
                                    transition: transform 0.2s ease;
                                }
                                
                                .details-reset[open] summary::before {
                                    transform: rotate(0deg);
                                }
                                
                                @keyframes tooltipFadeIn {
                                    from {
                                        opacity: 0;
                                        transform: translateY(5px);
                                    }
                                    to {
                                        opacity: 1;
                                        transform: translateY(0);
                                    }
                                }
                                
                                @media (prefers-color-scheme: dark) {
                                    .citation-ref {
                                        color: #60a5fa;
                                    }
                                    
                                    .citation-ref:hover {
                                        background-color: rgba(96, 165, 250, 0.1);
                                    }
                                    
                                    .citation-tooltip {
                                        border-color: rgba(17, 24, 39, 0.8);
                                        box-shadow: 0 10px 25px -5px rgba(0,0,0,0.6), 0 5px 10px -5px rgba(0,0,0,0.5);
                                    }
                                    
                                    .details-reset summary::before {
                                        color: #94a3b8;
                                    }
                                }
                            `}</style>
                        </div>
                    </motion.div>
                </div>

                {message.references && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                        className="mt-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 overflow-hidden"
                    >
                        <details className="overflow-hidden details-reset">
                            <summary className="font-medium text-sm pl-6 pr-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors flex items-center text-gray-700 dark:text-gray-300">
                                <div className="ml-4 flex items-center gap-3">
                                    <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                                    </svg>
                                    References
                                </div>
                            </summary>
                            <div
                                className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 border-t border-gray-200 dark:border-gray-800 references-content overflow-auto space-y-4"
                                style={{ maxHeight: '800px' }}
                            >
                                {(() => {
                                    try {
                                        // Try to parse as JSON
                                        const references = JSON.parse(message.references);

                                        return (
                                            <div className="references-list space-y-6">
                                                {references.map((ref: any) => (
                                                    <div
                                                        key={ref.id}
                                                        className="reference-item"
                                                        data-ref-index={ref.index}
                                                    >
                                                        <div className="flex gap-3 mb-2">
                                                            <div className="flex-shrink-0 w-6 text-gray-400">{ref.index}</div>
                                                            <div className="flex-1">
                                                                <div className="flex items-baseline gap-2 flex-wrap">
                                                                    <div className="font-medium text-gray-900 dark:text-gray-100">
                                                                        {ref.title}
                                                                    </div>
                                                                    {ref.year && (
                                                                        <div className="text-gray-500 text-xs whitespace-nowrap">
                                                                            ({ref.year})
                                                                        </div>
                                                                    )}
                                                                </div>

                                                                {ref.authors && ref.authors.length > 0 && (
                                                                    <div className="text-gray-500 text-sm mt-1">
                                                                        {ref.authors.join(', ')}
                                                                    </div>
                                                                )}

                                                                {ref.doi && (
                                                                    <div className="text-gray-500 text-sm mt-1">
                                                                        <span className="text-gray-400">DOI:</span>
                                                                        <a
                                                                            href={ref.doi.startsWith('http') ? ref.doi : `https://doi.org/${ref.doi}`}
                                                                            className="ml-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                                                                            target="_blank"
                                                                            rel="noopener noreferrer"
                                                                        >
                                                                            {ref.doi}
                                                                        </a>
                                                                    </div>
                                                                )}

                                                                <div className="text-gray-500 text-sm mt-1">
                                                                    <span className="text-gray-400">ID:</span>
                                                                    <a
                                                                        href={ref.id.startsWith('http') ? ref.id : `https://${ref.id}`}
                                                                        className="ml-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                                                                        target="_blank"
                                                                        rel="noopener noreferrer"
                                                                    >
                                                                        {ref.id}
                                                                    </a>
                                                                </div>

                                                                {ref.score !== null && (
                                                                    <div className="text-gray-500 text-sm mt-1">
                                                                        <span className="text-gray-400">Relevance:</span>
                                                                        <span className="ml-1">{typeof ref.score === 'number' ? ref.score.toFixed(2) : ref.score}</span>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        );
                                    } catch (e) {
                                        // Fallback to direct HTML rendering for legacy format
                                        return (
                                            <div className="references-wrapper" dangerouslySetInnerHTML={{
                                                __html: message.references
                                            }} />
                                        );
                                    }
                                })()}
                            </div>
                        </details>
                    </motion.div>
                )}
            </div>
        </motion.div>
    );
};

const UserIcon: FC = () => (
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
        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
    </svg>
);

const AithenaIcon: FC = () => (
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
        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
        <path d="M12 9v4" />
        <path d="M12 17h.01" />
    </svg>
);

export default MessageItem; 