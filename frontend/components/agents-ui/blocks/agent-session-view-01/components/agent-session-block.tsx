'use client';

import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, type MotionProps, motion } from 'motion/react';
import { useAgent, useSessionContext, useSessionMessages } from '@livekit/components-react';
import { Mic, Volume2, Brain, AlertTriangle, ShieldCheck } from 'lucide-react';
import { AgentChatTranscript } from '@/components/agents-ui/agent-chat-transcript';
import {
  AgentControlBar,
  type AgentControlBarControls,
} from '@/components/agents-ui/agent-control-bar';
import { Shimmer } from '@/components/ai-elements/shimmer';
import { cn } from '@/lib/shadcn/utils';
import { TileLayout } from './tile-view';

const MotionMessage = motion.create(Shimmer);

const BOTTOM_VIEW_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      translateY: '0%',
    },
    hidden: {
      opacity: 0,
      translateY: '100%',
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.3,
    delay: 0.5,
    ease: 'easeOut',
  },
};

const CHAT_MOTION_PROPS: MotionProps = {
  variants: {
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeOut',
        duration: 0.3,
      },
    },
    visible: {
      opacity: 1,
      transition: {
        delay: 0.2,
        ease: 'easeOut',
        duration: 0.3,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

const SHIMMER_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      transition: {
        ease: 'easeIn',
        duration: 0.5,
        delay: 0.8,
      },
    },
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeIn',
        duration: 0.5,
        delay: 0,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

export interface AgentSessionView_01Props {
  preConnectMessage?: string;
  supportsChatInput?: boolean;
  supportsVideoInput?: boolean;
  supportsScreenShare?: boolean;
  isPreConnectBufferEnabled?: boolean;
  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;
  className?: string;
  onDisconnectComplete?: () => void;
}

export function AgentSessionView_01({
  preConnectMessage = "FinVoice is listening. Ask any loan, savings, scheme, or general banking question...",
  supportsChatInput = true,
  supportsVideoInput = false,
  supportsScreenShare = false,
  isPreConnectBufferEnabled = true,
  audioVisualizerType,
  audioVisualizerColor,
  audioVisualizerColorShift,
  audioVisualizerBarCount,
  audioVisualizerGridRowCount,
  audioVisualizerGridColumnCount,
  audioVisualizerRadialBarCount,
  audioVisualizerRadialRadius,
  audioVisualizerWaveLineWidth,
  ref,
  className,
  onDisconnectComplete,
  ...props
}: React.ComponentProps<'section'> & AgentSessionView_01Props) {
  const session = useSessionContext();
  const { messages } = useSessionMessages(session);
  const [chatOpen, setChatOpen] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { state: agentState } = useAgent();

  const controls: AgentControlBarControls = {
    leave: true,
    microphone: true,
    chat: supportsChatInput,
    camera: false,
    screenShare: false,
  };

  useEffect(() => {
    const lastMessage = messages.at(-1);
    const lastMessageIsLocal = lastMessage?.from?.isLocal === true;

    if (scrollAreaRef.current && lastMessageIsLocal) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  const isSpeaking = agentState === 'speaking';
  const isListening = agentState === 'listening';
  const isThinking = agentState === 'thinking';

  const handleDisconnect = async () => {
    try {
      await session.end();
    } catch (e) {
      console.error(e);
    }
    if (onDisconnectComplete) {
      onDisconnectComplete();
    }
  };

  return (
    <section
      ref={ref}
      className={cn('relative z-10 h-full w-full overflow-hidden bg-slate-950 text-slate-100 select-none flex flex-col', className)}
      {...props}
    >
      {/* Background Ambient Glow Effects */}
      <div className="pointer-events-none absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-tr from-blue-700/20 via-indigo-600/20 to-cyan-500/20 rounded-full blur-3xl animate-mesh-glow" />

      {/* Top Header Bar */}
      <header className="absolute top-3 inset-x-3 sm:top-4 sm:inset-x-4 md:inset-x-8 z-30 flex items-center justify-between glass-card rounded-2xl px-4 sm:px-6 py-2.5 sm:py-3 border border-white/10 shadow-xl">
        <div className="flex items-center gap-3">
          <div className={cn(
            "relative flex items-center justify-center size-9 sm:size-10 rounded-full bg-slate-900 border border-white/20 transition-all duration-300",
            isSpeaking && "animate-speaking-glow border-purple-400",
            isListening && "border-blue-400 shadow-lg shadow-blue-500/20"
          )}>
            <span className="text-xs sm:text-sm font-black bg-gradient-to-r from-blue-400 via-indigo-300 to-cyan-300 bg-clip-text text-transparent">FV</span>
          </div>
          <div>
            <h2 className="text-xs sm:text-sm font-bold text-white tracking-wide">FinVoice</h2>
            <p className="text-[10px] sm:text-[11px] text-slate-400">AI Financial Support Assistant</p>
          </div>
        </div>

        {/* Live Speaker / State Indicator */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Active Speaker Badge */}
          <div className={cn(
            "flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold tracking-wide border transition-all duration-300",
            isSpeaking && "bg-purple-500/20 border-purple-400/60 text-purple-300 animate-pulse shadow-md shadow-purple-500/20",
            isListening && "bg-blue-500/20 border-blue-400/60 text-blue-300 animate-listening-ripple",
            isThinking && "bg-amber-500/20 border-amber-400/60 text-amber-300",
            !isSpeaking && !isListening && !isThinking && "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
          )}>
            {isSpeaking && (
              <>
                <Volume2 className="size-3.5 text-purple-300 animate-bounce" />
                <span className="hidden xs:inline">🔊 FinVoice is speaking...</span>
                <span className="xs:hidden">🔊 Speaking</span>
              </>
            )}
            {isListening && (
              <>
                <Mic className="size-3.5 text-blue-300 animate-pulse" />
                <span className="hidden xs:inline">🔵 Listening to you...</span>
                <span className="xs:hidden">🔵 Listening</span>
              </>
            )}
            {isThinking && (
              <>
                <Brain className="size-3.5 text-amber-300 animate-spin" />
                <span className="hidden xs:inline">🧠 FinVoice is thinking...</span>
                <span className="xs:hidden">🧠 Thinking</span>
              </>
            )}
            {!isSpeaking && !isListening && !isThinking && (
              <>
                <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>🟢 Ready</span>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Dynamic Status Banner (Centered below header) */}
      <div className="absolute top-20 inset-x-0 z-20 flex flex-col items-center pointer-events-none px-4">
        {isListening && (
          <div className="glass-card px-4 py-1.5 rounded-full border border-blue-400/30 text-blue-200 text-xs font-medium flex items-center gap-2 animate-slide-up shadow-lg">
            <Mic className="size-3.5 text-blue-400 animate-pulse" />
            <span>Speak naturally. I&apos;m listening.</span>
          </div>
        )}
        {isSpeaking && (
          <div className="glass-card px-4 py-1.5 rounded-full border border-purple-400/30 text-purple-200 text-xs font-medium flex items-center gap-2 animate-slide-up shadow-lg">
            {/* Animated Equalizer Bars */}
            <div className="flex items-end gap-0.5 h-3">
              <span className="w-0.5 bg-purple-400 h-full rounded-full eq-bar eq-bar-1" />
              <span className="w-0.5 bg-purple-400 h-full rounded-full eq-bar eq-bar-2" />
              <span className="w-0.5 bg-purple-400 h-full rounded-full eq-bar eq-bar-3" />
              <span className="w-0.5 bg-purple-400 h-full rounded-full eq-bar eq-bar-4" />
              <span className="w-0.5 bg-purple-400 h-full rounded-full eq-bar eq-bar-5" />
            </div>
            <span>Please wait while FinVoice responds.</span>
          </div>
        )}
      </div>

      {/* Transcript Chat Overlay */}
      <div className="absolute top-24 bottom-[145px] flex w-full flex-col md:bottom-[175px] z-20 px-4">
        <AnimatePresence>
          {chatOpen && (
            <motion.div
              {...CHAT_MOTION_PROPS}
              className="flex h-full w-full flex-col gap-4 space-y-3 transition-opacity duration-300 ease-out glass-card rounded-3xl p-4 sm:p-6 border border-white/10 shadow-2xl"
            >
              <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Conversation Transcript</span>
                <span className="text-[10px] text-blue-400 font-medium">FinVoice Live</span>
              </div>
              <AgentChatTranscript
                agentState={agentState}
                messages={messages}
                className="mx-auto w-full max-w-2xl [&_.is-user>div]:rounded-2xl [&_.is-user>div]:bg-blue-600/30 [&_.is-user>div]:border [&_.is-user>div]:border-blue-400/30 [&_.is-assistant>div]:rounded-2xl [&_.is-assistant>div]:bg-indigo-950/60 [&_.is-assistant>div]:border [&_.is-assistant>div]:border-indigo-500/30 [&>div>div]:px-4 md:[&>div>div]:px-6"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Main Visualizer & Tile Layout */}
      <div className={cn("h-full w-full transition-all duration-500", isSpeaking && "scale-[1.02]")}>
        <TileLayout
          chatOpen={chatOpen}
          audioVisualizerType={audioVisualizerType}
          audioVisualizerColor={audioVisualizerColor}
          audioVisualizerColorShift={audioVisualizerColorShift}
          audioVisualizerBarCount={audioVisualizerBarCount}
          audioVisualizerRadialBarCount={audioVisualizerRadialBarCount}
          audioVisualizerRadialRadius={audioVisualizerRadialRadius}
          audioVisualizerGridRowCount={audioVisualizerGridRowCount}
          audioVisualizerGridColumnCount={audioVisualizerGridColumnCount}
          audioVisualizerWaveLineWidth={audioVisualizerWaveLineWidth}
        />
      </div>

      {/* Bottom Financial Safety Strip */}
      <div className="absolute bottom-[92px] inset-x-0 z-30 flex justify-center px-4 pointer-events-none">
        <div className="glass-card max-w-xl w-full py-1.5 px-3 rounded-full border border-blue-500/20 text-[10px] text-slate-400 text-center flex items-center justify-center gap-1.5 shadow-md">
          <ShieldCheck className="size-3.5 text-blue-400 shrink-0" />
          <span className="truncate">FinVoice provides general info only &bull; Never shares OTPs/PINs</span>
        </div>
      </div>

      {/* Bottom Floating Glass Control Bar */}
      <motion.div
        {...BOTTOM_VIEW_MOTION_PROPS}
        className="absolute inset-x-3 bottom-3 z-50 md:inset-x-12"
      >
        {/* Pre-connect Buffer Message */}
        {isPreConnectBufferEnabled && (
          <AnimatePresence>
            {messages.length === 0 && (
              <MotionMessage
                key="pre-connect-message"
                duration={2}
                aria-hidden={messages.length > 0}
                {...SHIMMER_MOTION_PROPS}
                className="pointer-events-none mx-auto block w-full max-w-2xl pb-2 text-center text-xs md:text-sm font-medium text-blue-300/90"
              >
                {preConnectMessage}
              </MotionMessage>
            )}
          </AnimatePresence>
        )}
        <div className="relative mx-auto max-w-2xl glass-card rounded-full p-2.5 border border-white/15 shadow-2xl backdrop-blur-2xl">
          <AgentControlBar
            variant="livekit"
            controls={controls}
            isChatOpen={chatOpen}
            isConnected={session.isConnected}
            onDisconnect={handleDisconnect}
            onIsChatOpenChange={setChatOpen}
          />
        </div>
      </motion.div>
    </section>
  );
}
