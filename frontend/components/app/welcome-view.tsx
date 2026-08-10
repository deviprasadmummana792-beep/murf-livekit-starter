import React from 'react';
import { Button } from '@/components/ui/button';
import {
  ShieldCheck,
  Landmark,
  PiggyBank,
  FileText,
  HelpCircle,
  Mic,
  MicOff,
  Loader2,
  Lock,
  Sparkles,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';

interface WelcomeViewProps {
  startButtonText?: string;
  onStartCall: () => void;
  isConnecting?: boolean;
  hasEnded?: boolean;
  micError?: boolean;
  onClearMicError?: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  isConnecting = false,
  hasEnded = false,
  micError = false,
  onClearMicError,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div
      ref={ref}
      className="relative min-h-screen w-full overflow-hidden bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-4 md:p-6 select-none"
    >
      {/* Ambient Background Glows */}
      <div className="pointer-events-none absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[550px] bg-gradient-to-tr from-blue-700/25 via-indigo-600/20 to-cyan-500/25 rounded-full blur-3xl animate-mesh-glow" />
      <div className="pointer-events-none absolute bottom-10 right-10 w-[350px] h-[350px] bg-blue-600/15 rounded-full blur-3xl" />

      {/* Main Glass Card Container */}
      <main className="relative z-10 max-w-3xl w-full glass-card rounded-3xl p-6 sm:p-8 md:p-10 shadow-2xl border border-white/10 flex flex-col items-center text-center space-y-6 md:space-y-8">
        
        {/* Top Trust Badge */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-300 text-xs font-medium tracking-wide">
          <Lock className="size-3.5 text-blue-400" />
          <span>Your privacy and security matter.</span>
        </div>

        {/* Animated Avatar / Logo Badge */}
        <div className="relative group">
          <div className="absolute -inset-1.5 rounded-full bg-gradient-to-r from-blue-500 via-indigo-500 to-cyan-400 blur-md opacity-80 group-hover:opacity-100 transition duration-500 animate-pulse-ring" />
          <div className="relative flex items-center justify-center size-20 sm:size-24 rounded-full bg-slate-900 border border-white/20 shadow-xl">
            <Sparkles className="size-10 sm:size-12 text-blue-400 animate-pulse" />
          </div>
        </div>

        {/* Header Branding */}
        <div className="space-y-2 max-w-xl">
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-100 to-blue-400 bg-clip-text text-transparent">
            FinVoice
          </h1>
          <h2 className="text-lg sm:text-xl font-semibold text-blue-300">
            AI Financial Support Assistant
          </h2>
          <p className="text-slate-300 text-xs sm:text-sm md:text-base leading-relaxed pt-1">
            Your voice-powered financial assistance. Get help with general financial information through a simple voice conversation.
          </p>
        </div>

        {/* Current State Badge Indicator */}
        <div className="w-full flex justify-center">
          {hasEnded ? (
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-slate-800/80 border border-slate-600 text-slate-300 text-xs font-semibold">
              <span className="size-2 rounded-full bg-slate-400" />
              ⚫ Conversation ended &mdash; Thank you for speaking with FinVoice.
            </div>
          ) : isConnecting ? (
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-semibold animate-pulse">
              <Loader2 className="size-3.5 text-amber-400 animate-spin" />
              🟡 Connecting to your financial assistant. Please wait...
            </div>
          ) : (
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">
              <span className="size-2 rounded-full bg-emerald-400 animate-ping" />
              🟢 Ready &mdash; Your financial assistant is ready.
            </div>
          )}
        </div>

        {/* Microphone Permission Error Card (if triggered) */}
        {micError ? (
          <div className="w-full bg-red-950/40 border border-red-500/40 rounded-2xl p-5 text-left space-y-3 animate-slide-up">
            <div className="flex items-center gap-3 text-red-400 font-bold text-base">
              <div className="size-9 rounded-xl bg-red-500/20 flex items-center justify-center shrink-0">
                <MicOff className="size-5 text-red-400" />
              </div>
              <h3>Microphone Access Required</h3>
            </div>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              Microphone permission is blocked. Please allow microphone access in your browser settings and try again.
            </p>
            <div className="pt-1 flex justify-end">
              <Button
                size="sm"
                onClick={() => {
                  if (onClearMicError) onClearMicError();
                  onStartCall();
                }}
                className="bg-red-600 hover:bg-red-500 text-white font-medium text-xs px-4 rounded-xl flex items-center gap-2"
              >
                <RefreshCw className="size-3.5" />
                Try Again
              </Button>
            </div>
          </div>
        ) : (
          /* Main Action Button */
          <div className="w-full flex flex-col items-center pt-1">
            <Button
              size="lg"
              disabled={isConnecting}
              onClick={onStartCall}
              className="group relative w-full sm:w-84 h-14 rounded-full bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-500 text-white font-bold text-sm tracking-wide shadow-xl shadow-blue-600/25 transition-all duration-300 hover:scale-105 active:scale-95 flex items-center justify-center gap-3 border border-white/20 disabled:border-slate-700 disabled:scale-100"
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
                  <span>{startButtonText || 'Start Conversation'}</span>
                </>
              )}
            </Button>
            <span className="text-xs text-slate-400 pt-2.5 font-normal">
              {hasEnded ? 'Click to start a new voice session' : 'Click to start real-time voice conversation'}
            </span>
          </div>
        )}

        {/* Example Capabilities Grid */}
        <div className="w-full text-left pt-2 space-y-2.5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 text-center">
            What FinVoice Can Help With
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 w-full">
            
            <div className="glass-card glass-card-hover rounded-2xl p-3.5 border border-white/10 flex items-start gap-3">
              <div className="size-8 rounded-xl bg-blue-500/20 text-blue-400 flex items-center justify-center shrink-0">
                <FileText className="size-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">General Information</h4>
                <p className="text-[11px] text-slate-400 leading-snug">Banking concepts, terms & basic rules</p>
              </div>
            </div>

            <div className="glass-card glass-card-hover rounded-2xl p-3.5 border border-white/10 flex items-start gap-3">
              <div className="size-8 rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center shrink-0">
                <Landmark className="size-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">Loan Information</h4>
                <p className="text-[11px] text-slate-400 leading-snug">Personal, home & education loan basics</p>
              </div>
            </div>

            <div className="glass-card glass-card-hover rounded-2xl p-3.5 border border-white/10 flex items-start gap-3">
              <div className="size-8 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                <PiggyBank className="size-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">Savings Guidance</h4>
                <p className="text-[11px] text-slate-400 leading-snug">FDs, RDs, interest rates & savings tips</p>
              </div>
            </div>

            <div className="glass-card glass-card-hover rounded-2xl p-3.5 border border-white/10 flex items-start gap-3">
              <div className="size-8 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center shrink-0">
                <ShieldCheck className="size-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">Govt Schemes</h4>
                <p className="text-[11px] text-slate-400 leading-snug">PM Jan Dhan, Sukanya Samriddhi & Mudra</p>
              </div>
            </div>

            <div className="glass-card glass-card-hover rounded-2xl p-3.5 border border-white/10 flex items-start gap-3 sm:col-span-2 lg:col-span-2">
              <div className="size-8 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center shrink-0">
                <HelpCircle className="size-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">Basic Account Support Guidance</h4>
                <p className="text-[11px] text-slate-400 leading-snug">General procedures for account opening, KYC & fraud prevention</p>
              </div>
            </div>

          </div>
        </div>

        {/* Financial Safety Notice Banner */}
        <div className="w-full bg-blue-950/30 border border-blue-500/20 rounded-2xl p-3.5 text-xs text-slate-300 text-left flex items-start gap-2.5">
          <AlertTriangle className="size-4 text-amber-400 shrink-0 mt-0.5" />
          <p className="text-[11px] leading-relaxed text-slate-300">
            <strong className="text-white">Safety Notice:</strong> FinVoice provides general financial information and guidance. It does not request OTPs, PINs, passwords, or account numbers, and it cannot approve loans or perform transactions.
          </p>
        </div>

      </main>

      {/* Footer */}
      <footer className="relative z-10 pt-6 text-center text-[11px] text-slate-500">
        FinVoice &bull; Powered by LiveKit, Murf Falcon TTS & Gemini
      </footer>
    </div>
  );
};
