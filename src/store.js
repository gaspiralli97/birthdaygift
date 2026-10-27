// Card storage and abuse limits.
//
// Deliberately file-backed rather than a database: a few dozen cards a day does
// not justify one, and this keeps the service dependency-free. Node is
// single-threaded, so read-modify-write of the counter file needs no locking;
// writes go through a temp file + rename so a crash cannot leave a half-written
// JSON behind.

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { config, ttlMs } from './config.js';

const cardsDir = path.join(config.dataDir, 'cards');
const ratePath = path.join(config.dataDir, 'rate.json');

fs.mkdirSync(cardsDir, { recursive: true });

function writeJsonAtomic(file, value) {
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(value));
  fs.renameSync(tmp, file);
}

function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return fallback;
  }
}

// Base32-ish alphabet with no vowels and no look-alike characters, so an id is
// safe to read aloud and cannot spell anything unfortunate.
const ALPHABET = '23456789bcdfghjkmnpqrstvwxyz';

export function newId(length = 8) {
  const bytes = crypto.randomBytes(length);
  let out = '';
  for (const byte of bytes) out += ALPHABET[byte % ALPHABET.length];
  return out;
}

const cardPath = id => path.join(cardsDir, `${id}.json`);

// Ids come from the URL, so never let one escape the cards directory.
const VALID_ID = /^[2-9b-z]{6,16}$/;

export function saveCard(card) {
  const id = newId();
  const now = Date.now();
  const record = { ...card, id, createdAt: now, expiresAt: now + ttlMs };
  writeJsonAtomic(cardPath(id), record);
  return record;
}

/** Returns the card, or null if it never existed / already expired. */
export function getCard(id) {
  if (!VALID_ID.test(id)) return null;
  const record = readJson(cardPath(id), null);
  if (!record) return null;
  if (record.expiresAt <= Date.now()) {
    try {
      fs.unlinkSync(cardPath(id));
    } catch {}
    return null;
  }
  return record;
}

/** Deletes every card past its expiry. Returns how many were removed. */
export function sweepExpired() {
  const now = Date.now();
  let removed = 0;
  let files;
  try {
    files = fs.readdirSync(cardsDir);
  } catch {
    return 0;
  }
  for (const file of files) {
    if (!file.endsWith('.json')) continue;
    const full = path.join(cardsDir, file);
    const record = readJson(full, null);
    if (!record || record.expiresAt <= now) {
      try {
        fs.unlinkSync(full);
        removed++;
      } catch {}
    }
  }
  return removed;
}

const today = () => new Date().toISOString().slice(0, 10);

/**
 * Counts one card against both the per-user and the global daily budget.
 * The global cap exists because text generation is billed to the operator:
 * without it, one determined user could run up the bill on their own.
 */
export function checkAndCountQuota(userKey) {
  const day = today();
  const state = readJson(ratePath, null);
  const current = state && state.day === day ? state : { day, total: 0, users: {} };

  const used = current.users[userKey] || 0;
  if (used >= config.ratePerUserPerDay) {
    return { ok: false, reason: 'user', limit: config.ratePerUserPerDay };
  }
  if (current.total >= config.rateGlobalPerDay) {
    return { ok: false, reason: 'global', limit: config.rateGlobalPerDay };
  }

  current.users[userKey] = used + 1;
  current.total += 1;
  writeJsonAtomic(ratePath, current);
  return { ok: true, remaining: config.ratePerUserPerDay - current.users[userKey] };
}
