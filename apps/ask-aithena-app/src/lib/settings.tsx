'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

interface AppSettings {
    similarity_n: number;
    // Add more global settings here as needed
}

interface SettingsContextType {
    settings: AppSettings;
    updateSettings: (newSettings: Partial<AppSettings>) => void;
}

// Default settings
const defaultSettings: AppSettings = {
    similarity_n: 10,
};

// Create context with default values
const SettingsContext = createContext<SettingsContextType>({
    settings: defaultSettings,
    updateSettings: () => { },
});

// Custom hook to use settings
export const useSettings = () => useContext(SettingsContext);

export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    // Initialize state from localStorage if available, otherwise use defaults
    const [settings, setSettings] = useState<AppSettings>(() => {
        if (typeof window === 'undefined') return defaultSettings;

        const savedSettings = localStorage.getItem('app_settings');
        if (savedSettings) {
            try {
                return { ...defaultSettings, ...JSON.parse(savedSettings) };
            } catch (e) {
                console.error('Failed to parse settings from localStorage', e);
                return defaultSettings;
            }
        }
        return defaultSettings;
    });

    // Save settings to localStorage when they change
    useEffect(() => {
        if (typeof window !== 'undefined') {
            localStorage.setItem('app_settings', JSON.stringify(settings));
        }
    }, [settings]);

    // Function to update settings
    const updateSettings = (newSettings: Partial<AppSettings>) => {
        setSettings(prevSettings => ({
            ...prevSettings,
            ...newSettings,
        }));
    };

    return (
        <SettingsContext.Provider value={{ settings, updateSettings }}>
            {children}
        </SettingsContext.Provider>
    );
};

export default SettingsProvider; 