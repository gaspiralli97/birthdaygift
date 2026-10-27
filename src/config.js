// Configuration. Values come from the environment; secrets never live in this repo.
// On the server the systemd unit loads them from /etc/birthdaygift/env.

import fs from 'node:fs';
import path from 'node:path';

// Minimal .env reader so local development needs no dependencies.
// Server deployments use systemd EnvironmentFile instead and skip this.
function loadDotEnv(file) {
  let text;
  try {
    text = fs.readFileSync(file, 'utf8');
  } catch {
    return;
  }
  for (const rawLine of text.split('\n')) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq < 1) continue;
    const key = line.slice(0, eq).trim();
    if (process.env[key] !== undefined) continue; // real env wins
    let value = line.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    process.env[key] = value;
  }
}

loadDotEnv(path.join(process.cwd(), '.env'));

const int = (value, fallback) => {
  const n = Number.parseInt(value ?? '', 10);
  return Number.isFinite(n) ? n : fallback;
};

export const config = {
  port: int(process.env.PORT, 3000),
  publicUrl: (process.env.PUBLIC_URL || 'http://localhost:3000').replace(/\/+$/, ''),
  dataDir: process.env.DATA_DIR || path.join(process.cwd(), 'data'),
  ttlDays: int(process.env.CARD_TTL_DAYS, 5),

  aiProvider: process.env.AI_PROVIDER || 'none',
  anthropicKey: process.env.ANTHROPIC_API_KEY || '',
  anthropicModel: process.env.ANTHROPIC_MODEL || 'claude-opus-5',

  telegramToken: process.env.TELEGRAM_BOT_TOKEN || '',

  ratePerUserPerDay: int(process.env.RATE_PER_USER_PER_DAY, 3),
  rateGlobalPerDay: int(process.env.RATE_GLOBAL_PER_DAY, 100),
};

export const ttlMs = config.ttlDays * 24 * 60 * 60 * 1000;
