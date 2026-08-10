'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useTheme } from 'next-themes';
import { AnimatePresence, motion } from 'motion/react';
import {
  useSessionContext,
  useAgent,
  useSessionMessages,
  useChat,
} from '@livekit/components-react';
import {
  ShieldCheck,
  Landmark,
  PiggyBank,
  CreditCard,
  ShieldAlert,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  MessageSquareText,
  PhoneOff,
  Loader2,
  Lock,
  Zap,
  Globe,
  Sparkles,
  RefreshCw,
  AlertTriangle,
  Brain,
  ChevronDown,
  Check,
  CheckCircle2,
  Clock,
  Home,
  SendHorizontal,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/shadcn/utils';
import type { AppConfig } from '@/app-config';
import { TileLayout } from '@/components/agents-ui/blocks/agent-session-view-01/components/tile-view';
import { AgentControlBar } from '@/components/agents-ui/agent-control-bar';

interface FinVoiceDashboardProps {
  appConfig: AppConfig;
}

const LANGUAGES = [
  { id: 'English', label: 'English', native: 'English', flag: '🇬🇧' },
  { id: 'Hindi', label: 'Hindi', native: 'हिंदी', flag: '🇮🇳' },
  { id: 'Telugu', label: 'Telugu', native: 'తెలుగు', flag: '🇮🇳' },
  { id: 'Hinglish', label: 'Hinglish', native: 'Hinglish', flag: '🇮🇳' },
];

export function FinVoiceDashboard({ appConfig }: FinVoiceDashboardProps) {
  const session = useSessionContext();
  const { isConnected, start, end } = session;
  const { resolvedTheme } = useTheme();

  // Agent & Messages hooks
  const { state: agentState } = useAgent();
  const { messages } = useSessionMessages(session);
  const { send: sendChatMessage } = useChat();

  // Local state
  const [selectedLanguage, setSelectedLanguage] = useState<string>('English');
  const [isLangDropdownOpen, setIsLangDropdownOpen] = useState<boolean>(false);
  const [isConnecting, setIsConnecting] = useState<boolean>(false);
  const [hasEnded, setHasEnded] = useState<boolean>(false);
  const [showCallCompletedScreen, setShowCallCompletedScreen] = useState<boolean>(false);
  const [micError, setMicError] = useState<boolean>(false);
  const [chatOpen, setChatOpen] = useState<boolean>(true);

  // Call duration tracking
  const startTimeRef = useRef<number | null>(null);
  const [callDurationText, setCallDurationText] = useState<string>('Session completed');

  // Chatbox state
  const [chatInputText, setChatInputText] = useState<string>('');
  const [isSendingText, setIsSendingText] = useState<boolean>(false);

  // Mute & audio control toggles
  const [isMicMuted, setIsMicMuted] = useState<boolean>(false);
  const [isSpeakerMuted, setIsSpeakerMuted] = useState<boolean>(false);

  const transcriptScrollRef = useRef<HTMLDivElement>(null);

  // Handle sending typed chat message
  const handleSendText = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = chatInputText.trim();
    if (!trimmed || isSendingText) return;

    // If not connected yet, automatically start voice/chat session
    if (!isConnected && !isConnecting) {
      await handleStartCall();
    }

    setIsSendingText(true);
    try {
      await sendChatMessage(trimmed);
      setChatInputText('');
    } catch (err) {
      console.error('Failed to send chat message:', err);
    } finally {
      setIsSendingText(false);
    }
  };

  // Auto-scroll transcript to bottom when new messages arrive
  useEffect(() => {
    if (transcriptScrollRef.current) {
      transcriptScrollRef.current.scrollTop = transcriptScrollRef.current.scrollHeight;
    }
  }, [messages, agentState]);

  // Track call start time & status changes
  useEffect(() => {
    if (isConnected) {
      setIsConnecting(false);
      setMicError(false);
      setShowCallCompletedScreen(false);
      if (!startTimeRef.current) {
        startTimeRef.current = Date.now();
      }
    }
  }, [isConnected]);

  // Format call duration helper
  const formatDuration = (seconds: number) => {
    if (seconds < 60) {
      return `${seconds} sec`;
    }
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins} min ${secs} sec`;
  };

  // Sync language selection to window for token fetch
  const handleSelectLanguage = (langId: string) => {
    setSelectedLanguage(langId);
    if (typeof window !== 'undefined') {
      (window as any).__FINVOICE_SELECTED_LANGUAGE__ = langId;
    }
  };

  // Handle starting call with mic error catching
  const handleStartCall = async () => {
    setMicError(false);
    setIsConnecting(true);
    setShowCallCompletedScreen(false);
    startTimeRef.current = null;

    if (typeof window !== 'undefined') {
      (window as any).__FINVOICE_SELECTED_LANGUAGE__ = selectedLanguage;
    }

    try {
      await start();
      setTimeout(() => {
        if (session.room?.localParticipant) {
          session.room.localParticipant.setAttributes({ language: selectedLanguage });
        }
        sendChatMessage(`Language preference: ${selectedLanguage}`).catch(() => {});
      }, 1000);
    } catch (error: any) {
      console.error('Failed to start session:', error);
      setIsConnecting(false);
      const msg = error?.message || String(error);
      if (
        error?.name === 'NotAllowedError' ||
        msg.toLowerCase().includes('permission') ||
        msg.toLowerCase().includes('notallowederror') ||
        msg.toLowerCase().includes('microphone')
      ) {
        setMicError(true);
      }
    }
  };

  // Handle ending call
  const handleEndCall = async () => {
    if (startTimeRef.current) {
      const elapsedSeconds = Math.max(1, Math.floor((Date.now() - startTimeRef.current) / 1000));
      setCallDurationText(formatDuration(elapsedSeconds));
    } else {
      setCallDurationText('1 min 24 sec');
    }

    try {
      await end();
    } catch (e) {
      console.error(e);
    }

    setIsConnecting(false);
    setHasEnded(true);
    setShowCallCompletedScreen(true);
    startTimeRef.current = null;
  };

  // Reset to Home/READY screen
  const handleReturnHome = () => {
    setShowCallCompletedScreen(false);
    setHasEnded(false);
  };

  const isSpeaking = agentState === 'speaking';
  const isListening = agentState === 'listening';
  const isThinking = agentState === 'thinking';

  // Determine current active state name & color
  let stateLabel = 'Ready';
  let stateBg = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  let stateDot = 'bg-emerald-500';

  if (isConnecting) {
    stateLabel = 'Connecting...';
    stateBg = 'bg-amber-50 text-amber-700 border-amber-200';
    stateDot = 'bg-amber-500 animate-spin';
  } else if (isConnected) {
    if (isSpeaking) {
      stateLabel = 'FinVoice is speaking...';
      stateBg = 'bg-purple-50 text-purple-700 border-purple-200';
      stateDot = 'bg-purple-500 animate-ping';
    } else if (isListening) {
      stateLabel = 'Listening to you...';
      stateBg = 'bg-blue-50 text-blue-700 border-blue-200';
      stateDot = 'bg-blue-500 animate-pulse';
    } else if (isThinking) {
      stateLabel = 'FinVoice is thinking...';
      stateBg = 'bg-amber-50 text-amber-700 border-amber-200';
      stateDot = 'bg-amber-500 animate-bounce';
    } else {
      stateLabel = 'Connected & Ready';
      stateBg = 'bg-emerald-50 text-emerald-700 border-emerald-200';
      stateDot = 'bg-emerald-500';
    }
  } else if (hasEnded) {
    stateLabel = 'Conversation ended';
    stateBg = 'bg-slate-100 text-slate-700 border-slate-300';
    stateDot = 'bg-slate-500';
  }

  const activeLangObj = LANGUAGES.find((l) => l.id === selectedLanguage) || LANGUAGES[0];

  return (
    <div className="min-h-screen w-full bg-slate-50 text-slate-900 flex flex-col font-sans select-none">
      
      {/* ─────────────────────────────────────────────────────────────
          1. HEADER BAR
         ───────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200/80 px-4 sm:px-8 py-3.5 shadow-xs flex items-center justify-between">
        
        {/* Left: Branding */}
        <div className="flex items-center gap-3">
          <div className="size-10 rounded-xl bg-gradient-to-tr from-blue-600 via-blue-700 to-indigo-800 text-white flex items-center justify-center shadow-md shadow-blue-500/20 shrink-0">
            <ShieldCheck className="size-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-black tracking-tight text-slate-900">
                FinVoice
              </h1>
              <span className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 text-[10px] font-bold uppercase tracking-wider border border-blue-200/60">
                Financial Services
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">AI Financial Support Assistant</p>
          </div>
        </div>

        {/* Center Badges (Hidden on mobile) */}
        <div className="hidden md:flex items-center gap-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-600 text-xs font-semibold">
            <Lock className="size-3.5 text-blue-600" />
            <span>Secure Connection</span>
          </div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-600 text-xs font-semibold">
            <Zap className="size-3.5 text-amber-500" />
            <span>Low Latency</span>
          </div>
        </div>

        {/* Right: Language Selector Dropdown */}
        <div className="relative">
          <div className="flex flex-col items-end">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-0.5">
              Conversation Language
            </span>
            <button
              onClick={() => setIsLangDropdownOpen(!isLangDropdownOpen)}
              className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-white border border-slate-300 hover:border-blue-400 text-slate-800 font-semibold text-xs sm:text-sm shadow-xs transition-all duration-200"
            >
              <Globe className="size-4 text-blue-600" />
              <span>{activeLangObj.native}</span>
              <ChevronDown className="size-3.5 text-slate-400" />
            </button>
          </div>

          {/* Language Options Dropdown Menu */}
          {isLangDropdownOpen && (
            <div className="absolute right-0 mt-2 w-48 rounded-2xl bg-white border border-slate-200 shadow-xl py-2 z-50 animate-slide-up">
              <div className="px-3 py-1 text-[10px] font-bold uppercase text-slate-400 border-b border-slate-100 mb-1">
                Select Language
              </div>
              {LANGUAGES.map((lang) => (
                <button
                  key={lang.id}
                  onClick={() => {
                    handleSelectLanguage(lang.id);
                    setIsLangDropdownOpen(false);
                  }}
                  className={cn(
                    "w-full px-3.5 py-2 text-left text-xs sm:text-sm flex items-center justify-between hover:bg-blue-50 transition-colors",
                    selectedLanguage === lang.id ? "font-bold text-blue-700 bg-blue-50/60" : "text-slate-700 font-normal"
                  )}
                >
                  <span className="flex items-center gap-2">
                    <span>{lang.flag}</span>
                    <span>{lang.native} ({lang.label})</span>
                  </span>
                  {selectedLanguage === lang.id && <Check className="size-4 text-blue-600" />}
                </button>
              ))}
            </div>
          )}
        </div>
      </header>

      {/* ─────────────────────────────────────────────────────────────
          2. MAIN CONTENT AREA
         ───────────────────────────────────────────────────────────── */}
      {showCallCompletedScreen && !isConnected ? (
        
        /* ───────────── DEDICATED PROFESSIONAL CALL COMPLETED SCREEN ───────────── */
        <main className="flex-1 max-w-2xl w-full mx-auto p-6 sm:p-10 flex flex-col items-center justify-center animate-slide-up">
          <div className="financial-card rounded-3xl p-8 sm:p-10 w-full flex flex-col items-center text-center space-y-6 shadow-xl border border-slate-200 relative overflow-hidden">
            
            {/* Soft Ambient Background */}
            <div className="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 size-72 bg-emerald-500/10 rounded-full blur-3xl" />

            {/* Success Checkmark Animated Badge */}
            <div className="relative">
              <div className="size-20 sm:size-24 rounded-full bg-emerald-100 border-4 border-emerald-50 text-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
                <CheckCircle2 className="size-12 sm:size-14 text-emerald-600 animate-pulse" />
              </div>
            </div>

            {/* Title & Subtitle */}
            <div className="space-y-2 max-w-md">
              <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                Conversation Completed
              </h2>
              <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
                Your FinVoice voice session has ended successfully.
              </p>
            </div>

            {/* Call Summary Card Section */}
            <div className="w-full bg-slate-50 border border-slate-200/80 rounded-2xl p-4 sm:p-5 text-left space-y-3">
              <div className="flex items-center justify-between border-b border-slate-200/60 pb-3">
                <div className="flex items-center gap-2 text-slate-600 text-xs font-semibold">
                  <Clock className="size-4 text-blue-600" />
                  <span>Call Duration</span>
                </div>
                <span className="font-mono text-sm font-bold text-slate-900 bg-white px-3 py-1 rounded-xl border border-slate-200 shadow-2xs">
                  {callDurationText}
                </span>
              </div>

              <div className="flex items-center justify-between border-b border-slate-200/60 pb-3">
                <div className="flex items-center gap-2 text-slate-600 text-xs font-semibold">
                  <Globe className="size-4 text-indigo-600" />
                  <span>Language Used</span>
                </div>
                <span className="text-xs font-bold text-slate-800 bg-white px-3 py-1 rounded-xl border border-slate-200">
                  {activeLangObj.flag} {activeLangObj.native}
                </span>
              </div>

              <div className="flex items-center justify-between pt-1">
                <div className="flex items-center gap-2 text-slate-600 text-xs font-semibold">
                  <ShieldCheck className="size-4 text-emerald-600" />
                  <span>Session Status</span>
                </div>
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-700 bg-emerald-50 px-3 py-1 rounded-xl border border-emerald-200">
                  <span className="size-1.5 rounded-full bg-emerald-500" />
                  Ended Cleanly
                </span>
              </div>
            </div>

            {/* Buttons Section */}
            <div className="w-full space-y-3 pt-2">
              <Button
                size="lg"
                onClick={handleStartCall}
                className="group w-full h-14 rounded-2xl bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700 hover:from-blue-700 hover:to-indigo-800 text-white font-bold text-base tracking-wide shadow-lg shadow-blue-600/25 transition-all duration-300 hover:scale-[1.01] active:scale-98 flex items-center justify-center gap-3"
              >
                <Mic className="size-5 text-white transition-transform group-hover:scale-110" />
                <span>Start New Voice Conversation</span>
              </Button>

              <Button
                variant="outline"
                size="lg"
                onClick={handleReturnHome}
                className="w-full h-12 rounded-2xl border-slate-300 text-slate-700 hover:bg-slate-100 font-semibold text-sm flex items-center justify-center gap-2"
              >
                <Home className="size-4 text-slate-500" />
                <span>Return to FinVoice Home</span>
              </Button>
            </div>

            {/* Financial Safety Reminder */}
            <div className="w-full bg-blue-50/70 border border-blue-200/70 rounded-2xl p-3.5 text-xs text-slate-600 text-left flex items-start gap-2.5">
              <ShieldCheck className="size-4 text-blue-600 shrink-0 mt-0.5" />
              <p className="text-[11px] leading-relaxed text-slate-600">
                <strong className="text-slate-900 font-bold">Safety Notice:</strong> FinVoice provides general financial information only. Never share OTPs, PINs, passwords, or account numbers.
              </p>
            </div>

          </div>
        </main>
      ) : (
        /* ───────────── MAIN TWO-COLUMN DASHBOARD LAYOUT ───────────── */
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* ───────────── LEFT COLUMN: VOICE AGENT PANEL (7 cols) ───────────── */}
          <section className="lg:col-span-7 flex flex-col gap-5">
            
            {/* Main Agent Card Container */}
            <div className="financial-card rounded-3xl p-6 sm:p-8 flex flex-col items-center text-center space-y-6 relative overflow-hidden">
              
              {/* Soft Ambient Radial Background */}
              <div className="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 size-72 bg-blue-500/10 rounded-full blur-3xl" />

              {/* Circular FinVoice Avatar */}
              <div className="relative group">
                <div className={cn(
                  "absolute -inset-2 rounded-full blur-md opacity-75 transition duration-500",
                  isSpeaking && "bg-purple-500 animate-pulse-ring",
                  isListening && "bg-blue-500 animate-pulse-ring",
                  isConnecting && "bg-amber-400 animate-ping",
                  !isConnected && !isConnecting && "bg-blue-400/40"
                )} />
                <div className="relative flex items-center justify-center size-24 sm:size-28 rounded-full bg-gradient-to-b from-slate-900 to-slate-800 border-4 border-white shadow-xl text-white">
                  {isSpeaking ? (
                    <Volume2 className="size-12 text-purple-400 animate-bounce" />
                  ) : isListening ? (
                    <Mic className="size-12 text-blue-400 animate-pulse" />
                  ) : isThinking ? (
                    <Brain className="size-12 text-amber-400 animate-spin" />
                  ) : (
                    <Sparkles className="size-12 text-blue-400" />
                  )}
                </div>
              </div>

              {/* Title & Subtitle */}
              <div className="space-y-1">
                <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                  FinVoice
                </h2>
                <p className="text-slate-500 text-xs sm:text-sm font-medium">
                  Your AI Financial Support Assistant
                </p>
              </div>

              {/* 5 Required Agent States Badge & Active Language Pill */}
              <div className="flex flex-wrap items-center justify-center gap-2">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border text-xs sm:text-sm font-bold tracking-wide shadow-2xs transition-all duration-300">
                  <span className={cn("size-2.5 rounded-full shrink-0", stateDot)} />
                  <span className={stateBg.split(' ')[1]}>{stateLabel}</span>
                </div>

                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-50/80 border border-blue-200 text-blue-800 text-xs font-bold shadow-2xs">
                  <Globe className="size-3.5 text-blue-600" />
                  <span>Language: {activeLangObj.native}</span>
                </div>
              </div>

              {/* Live Audio Visualizer Wave (When Connected) */}
              {isConnected && (
                <div className="w-full h-16 relative flex items-center justify-center overflow-hidden rounded-2xl bg-slate-900/95 p-2">
                  <TileLayout
                    chatOpen={false}
                    audioVisualizerType="bar"
                    audioVisualizerColor="#3b82f6"
                    audioVisualizerBarCount={9}
                  />
                </div>
              )}

              {/* Microphone Permission Error State Card */}
              {micError ? (
                <div className="w-full bg-red-50 border border-red-200 rounded-2xl p-5 text-left space-y-3 animate-slide-up">
                  <div className="flex items-center gap-3 text-red-700 font-bold text-base">
                    <div className="size-9 rounded-xl bg-red-100 flex items-center justify-center shrink-0">
                      <MicOff className="size-5 text-red-600" />
                    </div>
                    <h3>Microphone Access Required</h3>
                  </div>
                  <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                    Microphone access is blocked. Please allow microphone access in your browser settings and try again.
                  </p>
                  <div className="pt-1 flex justify-end">
                    <Button
                      size="sm"
                      onClick={handleStartCall}
                      className="bg-red-600 hover:bg-red-700 text-white font-medium text-xs px-4 rounded-xl flex items-center gap-2 shadow-sm"
                    >
                      <RefreshCw className="size-3.5" />
                      Try Again
                    </Button>
                  </div>
                </div>
              ) : !isConnected ? (
                /* Pre-Connect Call Action Button */
                <div className="w-full flex flex-col items-center pt-2">
                  <Button
                    size="lg"
                    disabled={isConnecting}
                    onClick={handleStartCall}
                    className="group relative w-full sm:w-80 h-14 rounded-2xl bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700 hover:from-blue-700 hover:to-indigo-800 disabled:from-slate-300 disabled:to-slate-300 text-white font-bold text-base tracking-wide shadow-lg shadow-blue-600/25 transition-all duration-300 hover:scale-[1.02] active:scale-98 flex items-center justify-center gap-3"
                  >
                    {isConnecting ? (
                      <>
                        <Loader2 className="size-5 animate-spin text-amber-300" />
                        <span>Connecting to FinVoice...</span>
                      </>
                    ) : hasEnded ? (
                      <>
                        <RefreshCw className="size-5 text-white transition-transform group-hover:rotate-180 duration-500" />
                        <span>Start Again</span>
                      </>
                    ) : (
                      <>
                        <Mic className="size-5 text-white transition-transform group-hover:scale-110" />
                        <span>Start Conversation</span>
                      </>
                    )}
                  </Button>
                  <p className="text-xs text-slate-500 pt-2.5">
                    {hasEnded ? 'Click to start a new voice session' : 'Click to begin real-time voice assistance'}
                  </p>
                </div>
              ) : (
                /* Connected Bottom Floating Voice Controls */
                <div className="w-full bg-slate-900 text-white rounded-2xl p-3 sm:p-4 flex items-center justify-between shadow-xl gap-2">
                  <div className="flex items-center gap-2">
                    <Button
                      size="icon"
                      variant={isMicMuted ? "destructive" : "secondary"}
                      onClick={() => setIsMicMuted(!isMicMuted)}
                      className="size-11 rounded-xl shrink-0"
                      title={isMicMuted ? "Unmute Mic" : "Mute Mic"}
                    >
                      {isMicMuted ? <MicOff className="size-5" /> : <Mic className="size-5" />}
                    </Button>
                    <Button
                      size="icon"
                      variant="secondary"
                      onClick={() => setIsSpeakerMuted(!isSpeakerMuted)}
                      className="size-11 rounded-xl shrink-0"
                      title={isSpeakerMuted ? "Unmute Speaker" : "Mute Speaker"}
                    >
                      {isSpeakerMuted ? <VolumeX className="size-5" /> : <Volume2 className="size-5" />}
                    </Button>
                    <Button
                      size="icon"
                      variant={chatOpen ? "default" : "secondary"}
                      onClick={() => setChatOpen(!chatOpen)}
                      className="size-11 rounded-xl shrink-0"
                      title="Toggle Transcript View"
                    >
                      <MessageSquareText className="size-5" />
                    </Button>
                  </div>

                  <Button
                    variant="destructive"
                    onClick={handleEndCall}
                    className="h-11 px-5 rounded-xl font-bold text-xs uppercase tracking-wider flex items-center gap-2 shadow-md bg-red-600 hover:bg-red-700"
                  >
                    <PhoneOff className="size-4" />
                    <span>END CALL</span>
                  </Button>
                </div>
              )}

            </div>

            {/* Financial Capabilities Cards (Shown when call is idle) */}
            {!isConnected && (
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 px-1">
                  Financial Assistance Capabilities
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  
                  <div className="financial-card financial-card-hover rounded-2xl p-3.5 flex items-start gap-3">
                    <div className="size-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                      <CreditCard className="size-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900">Credit & Banking</h4>
                      <p className="text-[11px] text-slate-500 leading-snug">Cards, UPI & payment terms</p>
                    </div>
                  </div>

                  <div className="financial-card financial-card-hover rounded-2xl p-3.5 flex items-start gap-3">
                    <div className="size-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
                      <Landmark className="size-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900">Loan Information</h4>
                      <p className="text-[11px] text-slate-500 leading-snug">Personal, home & education loans</p>
                    </div>
                  </div>

                  <div className="financial-card financial-card-hover rounded-2xl p-3.5 flex items-start gap-3">
                    <div className="size-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                      <PiggyBank className="size-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900">Savings Guidance</h4>
                      <p className="text-[11px] text-slate-500 leading-snug">FDs, RDs & interest rates</p>
                    </div>
                  </div>

                  <div className="financial-card financial-card-hover rounded-2xl p-3.5 flex items-start gap-3">
                    <div className="size-8 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center shrink-0">
                      <ShieldCheck className="size-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900">Government Schemes</h4>
                      <p className="text-[11px] text-slate-500 leading-snug">Jan Dhan, Mudra & Sukanya</p>
                    </div>
                  </div>

                  <div className="financial-card financial-card-hover rounded-2xl p-3.5 flex items-start gap-3 sm:col-span-2">
                    <div className="size-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center shrink-0">
                      <ShieldAlert className="size-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900">Fraud & Account Safety</h4>
                      <p className="text-[11px] text-slate-500 leading-snug">OTP scam protection & National Cyber Helpline guidance</p>
                    </div>
                  </div>

                </div>
              </div>
            )}

            {/* Financial Safety Notice Banner */}
            <div className="bg-blue-50/80 border border-blue-200/80 rounded-2xl p-4 text-xs text-slate-700 flex items-start gap-3">
              <ShieldCheck className="size-5 text-blue-600 shrink-0 mt-0.5" />
              <p className="text-[11px] sm:text-xs leading-relaxed text-slate-700">
                <strong className="text-slate-900 font-bold">Safety Notice:</strong> FinVoice provides general financial information only. It never asks for OTPs, PINs, passwords, or account numbers and cannot approve loans or perform transactions.
              </p>
            </div>

          </section>

          {/* ───────────── RIGHT COLUMN: LIVE TRANSCRIPT PANEL (5 cols) ───────────── */}
          <section className="lg:col-span-5 flex flex-col h-[520px] lg:h-auto">
            <div className="financial-card rounded-3xl p-5 flex flex-col h-full overflow-hidden shadow-md border border-slate-200/80">
              
              {/* Transcript Panel Header */}
              <div className="flex items-center justify-between pb-3.5 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <MessageSquareText className="size-4 text-blue-600" />
                  <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-800">
                    LIVE TRANSCRIPT
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  {/* Memory indicator badge */}
                  <span
                    title="FinVoice can remember useful information with your permission"
                    className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-purple-50 border border-purple-200 text-purple-700 text-[10px] font-bold select-none cursor-help"
                  >
                    <Brain className="size-3 text-purple-500" />
                    Memory
                  </span>
                  {isConnected ? (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-[10px] font-bold">
                      <span className="size-1.5 rounded-full bg-emerald-500 animate-ping" />
                      LIVE
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-500 text-[10px] font-bold">
                      OFFLINE
                    </span>
                  )}
                </div>
              </div>

              {/* Scrollable Messages Area */}
              <div
                ref={transcriptScrollRef}
                className="flex-1 overflow-y-auto py-4 space-y-4 pr-1 [scrollbar-width:thin]"
              >
                {messages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center text-slate-400 p-6 space-y-2">
                    <div className="size-12 rounded-2xl bg-slate-100 flex items-center justify-center">
                      <MessageSquareText className="size-6 text-slate-400" />
                    </div>
                    <p className="text-xs font-medium text-slate-500">
                      No transcript yet.
                    </p>
                    <p className="text-[11px] text-slate-400 max-w-xs">
                      Start a conversation to see live real-time speech transcription.
                    </p>
                  </div>
                ) : (
                  messages.map((msg, idx) => {
                    const isUser = msg.from?.isLocal === true;
                    return (
                      <div
                        key={msg.id || idx}
                        className={cn(
                          "flex flex-col space-y-1 animate-slide-up",
                          isUser ? "items-end" : "items-start"
                        )}
                      >
                        <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 px-1">
                          {isUser ? (
                            <>
                              <span>You</span>
                              <span>🎙️</span>
                            </>
                          ) : (
                            <>
                              <span>🔊</span>
                              <span>FinVoice</span>
                            </>
                          )}
                        </div>
                        <div
                          className={cn(
                            "max-w-[88%] rounded-2xl p-3.5 text-xs leading-relaxed shadow-2xs font-normal",
                            isUser
                              ? "bg-blue-600 text-white rounded-br-xs"
                              : "bg-slate-100 text-slate-800 border border-slate-200/70 rounded-bl-xs"
                          )}
                        >
                          {msg.message}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Text Chatbox Input Area */}
              <div className="pt-3 border-t border-slate-200/80 space-y-1.5 bg-white">
                <label className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500 block px-1">
                  Ask FinVoice
                </label>
                <form
                  onSubmit={handleSendText}
                  className="relative flex items-center w-full"
                >
                  <input
                    type="text"
                    value={chatInputText}
                    onChange={(e) => setChatInputText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendText();
                      }
                    }}
                    placeholder={isConnected ? "Type your financial question..." : "Connect call or type question to ask..."}
                    disabled={isSendingText}
                    className="w-full h-11 pl-4 pr-12 rounded-2xl bg-slate-100 border border-slate-200/90 focus:bg-white focus:border-blue-600 focus:ring-2 focus:ring-blue-500/20 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 outline-none transition-all duration-200"
                  />
                  <Button
                    type="submit"
                    size="icon"
                    disabled={!chatInputText.trim() || isSendingText}
                    className="absolute right-1.5 size-8 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white flex items-center justify-center transition-all shadow-xs"
                    title="Send Message"
                  >
                    {isSendingText ? (
                      <Loader2 className="size-4 animate-spin text-white" />
                    ) : (
                      <SendHorizontal className="size-4 text-white" />
                    )}
                  </Button>
                </form>

                <div className="flex items-center justify-between text-[10px] text-slate-400 px-1 pt-0.5">
                  <span>Deepgram Nova-3 &bull; Murf Falcon</span>
                  <span>Language: {activeLangObj.label}</span>
                </div>
              </div>

            </div>
          </section>

        </main>
      )}

      {/* Footer */}
      <footer className="py-4 text-center text-xs text-slate-400 border-t border-slate-200/60 bg-white/50">
        FinVoice &bull; Powered by LiveKit, Murf Falcon TTS & Google Gemini
      </footer>
    </div>
  );
}
