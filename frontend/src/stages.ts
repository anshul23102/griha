import type { StationState } from './components/kit'
export const STAGES = ['data_integration', 'income', 'property', 'fraud', 'eligibility', 'policy', 'risk', 'compliance']
export const ST: Record<string, StationState> = { ok: 'ok', warn: 'warn', fail: 'fail', skipped: 'ok' }
