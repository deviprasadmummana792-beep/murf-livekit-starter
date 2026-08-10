'use client';

import React from 'react';
import type { AppConfig } from '@/app-config';
import { FinVoiceDashboard } from '@/components/app/finvoice-dashboard';

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  return <FinVoiceDashboard appConfig={appConfig} />;
}
