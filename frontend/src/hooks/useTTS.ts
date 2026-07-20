import { useCallback, useRef, useState } from 'react';

/**
 * Browser Text-to-Speech hook using the Web Speech API.
 * Works with Chinese voices on modern browsers (Chrome, Edge, Safari).
 */
export function useTTS() {
  const [speaking, setSpeaking] = useState(false);
  const [paused, setPaused] = useState(false);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const speak = useCallback((text: string) => {
    if (!('speechSynthesis' in window)) return;

    const synth = window.speechSynthesis;

    // If already speaking, stop first
    if (synth.speaking || synth.pending) {
      synth.cancel();
    }

    // Clean text: remove JSON artifacts, emojis, and punctuation-only sections
    const cleanText = text
      .replace(/\{.*?\}/g, '')           // Remove JSON
      .replace(/[\p{Emoji}]/gu, '')      // Remove emojis
      .replace(/[★☆✨🌟💫⭐]/g, '')      // Common star emojis
      .trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utteranceRef.current = utterance;

    // Find a Chinese voice
    const voices = synth.getVoices();
    const chineseVoice = voices.find(
      (v) => v.lang.startsWith('zh') || v.name.includes('Chinese') || v.name.includes('TingTing') || v.name.includes('Yaoyao')
    );

    if (chineseVoice) {
      utterance.voice = chineseVoice;
    }
    utterance.lang = chineseVoice ? chineseVoice.lang : 'zh-CN';
    utterance.rate = 0.9;   // Slightly slower for children
    utterance.pitch = 1.1;  // Slightly higher, friendlier

    utterance.onstart = () => { setSpeaking(true); setPaused(false); };
    utterance.onend = () => { setSpeaking(false); setPaused(false); };
    utterance.onpause = () => { setPaused(true); };
    utterance.onresume = () => { setPaused(false); };
    utterance.onerror = () => { setSpeaking(false); setPaused(false); };

    synth.speak(utterance);
  }, []);

  const pause = useCallback(() => {
    window.speechSynthesis?.pause();
  }, []);

  const resume = useCallback(() => {
    window.speechSynthesis?.resume();
  }, []);

  const stop = useCallback(() => {
    window.speechSynthesis?.cancel();
    setSpeaking(false);
    setPaused(false);
  }, []);

  return { speak, pause, resume, stop, speaking, paused };
}
