'use client';

import { useMemo } from 'react';
import { TokenSource } from 'livekit-client';
import { useSession } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react/dist/ssr';
import type { AppConfig } from '@/app-config';
import { AgentSessionProvider } from '@/components/agents-ui/agent-session-provider';
import { StartAudioButton } from '@/components/agents-ui/start-audio-button';
import { ViewController } from '@/components/app/view-controller';
import { Toaster } from '@/components/ui/sonner';
import { useAgentErrors } from '@/hooks/useAgentErrors';
import { useDebugMode } from '@/hooks/useDebug';
import { getSandboxTokenSource } from '@/lib/utils';

const IN_DEVELOPMENT = process.env.NODE_ENV !== 'production';

function AppSetup() {
  useDebugMode({ enabled: IN_DEVELOPMENT });
  useAgentErrors();

  return null;
}

interface AppProps {
  appConfig: AppConfig;
}

/**
 * Returns a stable anonymous user ID stored in localStorage.
 * On first visit a UUID-style ID is generated and saved.
 * This persists across page refreshes and agent restarts (same browser).
 */
function getOrCreateUserId(): string {
  const KEY = 'finvoice_user_id';
  if (typeof window === 'undefined') return 'ssr-placeholder';
  let uid = localStorage.getItem(KEY);
  if (!uid) {
    // Simple UUID v4 generator — no external deps needed
    uid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
    localStorage.setItem(KEY, uid);
  }
  return uid;
}

export function App({ appConfig }: AppProps) {
  const tokenSource = useMemo(() => {
    return TokenSource.custom(async () => {
      const selectedLang = (typeof window !== 'undefined' && (window as any).__FINVOICE_SELECTED_LANGUAGE__) || 'English';
      const userId = getOrCreateUserId();
      const roomConfig = appConfig.agentName
        ? { agents: [{ agent_name: appConfig.agentName }] }
        : undefined;
      const res = await fetch('/api/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_config: roomConfig,
          language: selectedLang,
          user_id: userId,
        }),
      });
      if (!res.ok) {
        throw new Error(`Failed to fetch connection token: ${res.statusText}`);
      }
      return await res.json();
    });
  }, [appConfig]);

  const session = useSession(
    tokenSource,
    appConfig.agentName ? { agentName: appConfig.agentName } : undefined
  );

  return (
    <AgentSessionProvider session={session}>
      <AppSetup />
      <main className="min-h-screen w-full flex flex-col">
        <ViewController appConfig={appConfig} />
      </main>
      <StartAudioButton label="Start Audio" />
      <Toaster
        icons={{
          warning: <WarningIcon weight="bold" />,
        }}
        position="top-center"
        className="toaster group"
        style={
          {
            '--normal-bg': 'var(--popover)',
            '--normal-text': 'var(--popover-foreground)',
            '--normal-border': 'var(--border)',
          } as React.CSSProperties
        }
      />
    </AgentSessionProvider>
  );
}
