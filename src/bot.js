// Telegram bot: collects the card details in a short chat, then hands back a
// link. Long polling, so the server needs no inbound port for Telegram and no
// webhook certificate — only the card page is reachable from outside.

import { config } from './config.js';
import { saveCard, checkAndCountQuota, refundQuota } from './store.js';
import { writeLetter, normalizeInput, LANGUAGES } from './ai.js';

const API = token => `https://api.telegram.org/bot${token}`;

async function call(method, payload) {
  const response = await fetch(`${API(config.telegramToken)}/${method}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!data.ok) throw new Error(`${method}: ${data.description}`);
  return data.result;
}

const send = (chatId, text, extra = {}) =>
  call('sendMessage', { chat_id: chatId, text, parse_mode: 'HTML', ...extra });

// ---------------------------------------------------------------------------
// Conversation copy
// ---------------------------------------------------------------------------

const BOT = {
  uz: {
    start:
      '🎂 <b>Tug‘ilgan kun tabrigi</b>\n\nBir necha savolga javob bering — men sizga havola qaytaraman. Havolani tug‘ilgan kun egasiga yuborasiz.\n\nHavola <b>5 kun</b> yashaydi.',
    askLang: 'Tabrik qaysi tilda bo‘lsin?',
    askName: 'Kimni tabriklaymiz? <i>Ismini yozing.</i>',
    askAge: 'Necha yosh to‘ldi? <i>Faqat raqam. Bilmasangiz — /skip</i>',
    askRel: 'U sizga kim bo‘ladi?',
    askDetails:
      'U haqida bir-ikki narsa yozing — nimani yaxshi ko‘radi, qanday odam, qayerda tanishgansiz. <i>Kerak bo‘lmasa — /skip</i>',
    askFrom: 'Tabrik kimdan? <i>Ismingizni yozing yoki /skip</i>',
    working: '✍️ Tabrik yozilmoqda…',
    done: '✅ Tayyor! Havolani yuboring:',
    expiry: d => `Havola ${d} kundan keyin o‘chadi.`,
    badName: 'Ismni yozing (kamida 2 harf).',
    badAge: 'Raqam yozing, masalan <code>30</code>. Yoki /skip',
    limitUser: n => `Kunlik chegara tugadi — kuniga ${n} karta. Ertaga qayta urinib ko‘ring.`,
    limitGlobal: 'Bugun tizim bandligi chegarasiga yetdi. Ertaga qayta urinib ko‘ring.',
    failed: 'Xatolik yuz berdi, karta saqlanmadi. Birozdan keyin qayta urinib ko‘ring: /start',
    cancelled: 'Bekor qilindi. Qaytadan boshlash: /start',
    unknown: 'Boshlash uchun /start yuboring.',
    rels: { friend: 'Do‘stim', classmate: 'Sinfdoshim', colleague: 'Hamkasbim', family: 'Qarindoshim', other: 'Boshqa' },
  },
  en: {
    start:
      '🎂 <b>Birthday card</b>\n\nAnswer a few questions and I will hand you a link. Send the link to the birthday person.\n\nThe link lives for <b>5 days</b>.',
    askLang: 'Which language should the card be in?',
    askName: 'Who are we celebrating? <i>Type their name.</i>',
    askAge: 'How old are they turning? <i>Numbers only, or /skip</i>',
    askRel: 'Who are they to you?',
    askDetails:
      'Tell me a thing or two about them — what they love, what they are like, how you met. <i>Or /skip</i>',
    askFrom: 'Who is it from? <i>Type your name or /skip</i>',
    working: '✍️ Writing the card…',
    done: '✅ Done. Here is the link:',
    expiry: d => `The link disappears in ${d} days.`,
    badName: 'Please type a name (at least 2 letters).',
    badAge: 'Type a number, e.g. <code>30</code>. Or /skip',
    limitUser: n => `Daily limit reached — ${n} cards a day. Try again tomorrow.`,
    limitGlobal: 'The service hit its daily cap. Try again tomorrow.',
    failed: 'Something went wrong and the card was not saved. Try again in a moment: /start',
    cancelled: 'Cancelled. Start again with /start',
    unknown: 'Send /start to begin.',
    rels: { friend: 'Friend', classmate: 'Classmate', colleague: 'Colleague', family: 'Family', other: 'Other' },
  },
  ko: {
    start:
      '🎂 <b>생일 카드</b>\n\n몇 가지만 답해 주시면 링크를 드립니다. 그 링크를 생일 주인공에게 보내세요.\n\n링크는 <b>5일</b> 동안 유효합니다.',
    askLang: '카드를 어떤 언어로 만들까요?',
    askName: '누구의 생일인가요? <i>이름을 입력해 주세요.</i>',
    askAge: '몇 살이 되셨나요? <i>숫자만, 또는 /skip</i>',
    askRel: '그분은 어떤 관계인가요?',
    askDetails:
      '그분에 대해 한두 가지 알려 주세요 — 좋아하는 것, 성격, 어떻게 만났는지. <i>또는 /skip</i>',
    askFrom: '보내는 사람은 누구인가요? <i>이름 또는 /skip</i>',
    working: '✍️ 카드를 쓰고 있어요…',
    done: '✅ 완성했어요. 링크입니다:',
    expiry: d => `링크는 ${d}일 후에 사라집니다.`,
    badName: '이름을 입력해 주세요 (2자 이상).',
    badAge: '숫자를 입력해 주세요. 예: <code>30</code>. 또는 /skip',
    limitUser: n => `일일 한도에 도달했습니다 — 하루 ${n}장. 내일 다시 시도해 주세요.`,
    limitGlobal: '오늘 서비스 한도에 도달했습니다. 내일 다시 시도해 주세요.',
    failed: '문제가 발생해 카드가 저장되지 않았습니다. 잠시 후 다시 시도해 주세요: /start',
    cancelled: '취소되었습니다. /start 로 다시 시작하세요.',
    unknown: '/start 를 보내 시작하세요.',
    rels: { friend: '친구', classmate: '동창', colleague: '동료', family: '가족', other: '기타' },
  },
  ru: {
    start:
      '🎂 <b>Открытка на день рождения</b>\n\nОтветь на пару вопросов — я верну ссылку. Отправь её имениннику.\n\nСсылка живёт <b>5 дней</b>.',
    askLang: 'На каком языке сделать открытку?',
    askName: 'Кого поздравляем? <i>Напиши имя.</i>',
    askAge: 'Сколько исполняется? <i>Только число, или /skip</i>',
    askRel: 'Кто он тебе?',
    askDetails:
      'Расскажи пару вещей о нём — что любит, какой он, где познакомились. <i>Или /skip</i>',
    askFrom: 'От кого открытка? <i>Напиши своё имя или /skip</i>',
    working: '✍️ Пишу открытку…',
    done: '✅ Готово. Вот ссылка:',
    expiry: d => `Ссылка исчезнет через ${d} дней.`,
    badName: 'Напиши имя (минимум 2 буквы).',
    badAge: 'Напиши число, например <code>30</code>. Или /skip',
    limitUser: n => `Дневной лимит исчерпан — ${n} открыток в день. Попробуй завтра.`,
    limitGlobal: 'Сервис достиг дневного лимита. Попробуй завтра.',
    failed: 'Что-то пошло не так, открытка не сохранилась. Попробуй чуть позже: /start',
    cancelled: 'Отменено. Начать заново: /start',
    unknown: 'Отправь /start, чтобы начать.',
    rels: { friend: 'Друг', classmate: 'Одноклассник', colleague: 'Коллега', family: 'Родственник', other: 'Другое' },
  },
};

const copy = lang => BOT[lang] || BOT.uz;

const LANG_KEYBOARD = {
  inline_keyboard: [
    [
      { text: '🇺🇿 O‘zbekcha', callback_data: 'lang:uz' },
      { text: '🇬🇧 English', callback_data: 'lang:en' },
    ],
    [
      { text: '🇰🇷 한국어', callback_data: 'lang:ko' },
      { text: '🇷🇺 Русский', callback_data: 'lang:ru' },
    ],
  ],
};

const relKeyboard = lang => {
  const { rels } = copy(lang);
  return {
    inline_keyboard: [
      [
        { text: rels.friend, callback_data: 'rel:friend' },
        { text: rels.classmate, callback_data: 'rel:classmate' },
      ],
      [
        { text: rels.colleague, callback_data: 'rel:colleague' },
        { text: rels.family, callback_data: 'rel:family' },
      ],
      [{ text: rels.other, callback_data: 'rel:other' }],
    ],
  };
};

// ---------------------------------------------------------------------------
// Conversation state
// ---------------------------------------------------------------------------

// In memory on purpose: a half-finished conversation is worth nothing after a
// restart, and this keeps the bot free of a second storage concern.
const sessions = new Map();
const SESSION_TTL = 30 * 60 * 1000;

const touch = chatId => {
  const session = sessions.get(chatId);
  if (session) session.at = Date.now();
  return session;
};

setInterval(() => {
  const cutoff = Date.now() - SESSION_TTL;
  for (const [chatId, session] of sessions) {
    if (session.at < cutoff) sessions.delete(chatId);
  }
}, 5 * 60 * 1000).unref();

async function finish(chatId, userId, session) {
  const s = copy(session.data.lang);
  const quota = checkAndCountQuota(`tg:${userId}`);
  if (!quota.ok) {
    sessions.delete(chatId);
    await send(chatId, quota.reason === 'user' ? s.limitUser(quota.limit) : s.limitGlobal);
    return;
  }

  await send(chatId, s.working);

  let url;
  try {
    const card = normalizeInput(session.data);
    const { paragraphs, source } = await writeLetter(card);
    const saved = saveCard({ ...card, paragraphs, source });
    url = `${config.publicUrl}/c/${saved.id}`;
  } catch (error) {
    // Storage is the only thing left that can fail here - writeLetter already
    // falls back to the template. Refund the attempt so a disk problem does not
    // also eat the user's daily allowance.
    refundQuota(`tg:${userId}`);
    sessions.delete(chatId);
    console.error('[bot] card creation failed:', error?.message || error);
    await send(chatId, s.failed);
    return;
  }

  sessions.delete(chatId);
  await send(chatId, `${s.done}\n\n${url}\n\n<i>${s.expiry(config.ttlDays)}</i>`, {
    link_preview_options: { is_disabled: false },
  });
}

async function onText(message) {
  const chatId = message.chat.id;
  const userId = message.from?.id ?? chatId;
  const text = (message.text || '').trim();

  if (text === '/start') {
    sessions.set(chatId, { step: 'lang', data: {}, at: Date.now() });
    await send(chatId, BOT.uz.start);
    await send(chatId, BOT.uz.askLang, { reply_markup: LANG_KEYBOARD });
    return;
  }

  if (text === '/cancel') {
    const session = sessions.get(chatId);
    sessions.delete(chatId);
    await send(chatId, copy(session?.data?.lang).cancelled);
    return;
  }

  const session = touch(chatId);
  if (!session) {
    await send(chatId, BOT.uz.unknown);
    return;
  }

  const s = copy(session.data.lang);
  const skipped = text === '/skip';

  switch (session.step) {
    case 'name':
      // No /skip here: a card has to be addressed to somebody.
      if (skipped || text.replace(/\s/g, '').length < 2) return void send(chatId, s.badName);
      session.data.name = text;
      session.step = 'age';
      return void send(chatId, s.askAge);

    case 'age': {
      if (!skipped) {
        const age = Number.parseInt(text, 10);
        if (!Number.isFinite(age) || age < 1 || age > 129) return void send(chatId, s.badAge);
        session.data.age = age;
      }
      session.step = 'rel';
      return void send(chatId, s.askRel, { reply_markup: relKeyboard(session.data.lang) });
    }

    case 'details':
      if (!skipped) session.data.details = text;
      session.step = 'from';
      return void send(chatId, s.askFrom);

    case 'from':
      if (!skipped) session.data.from = text;
      return void finish(chatId, userId, session);

    default:
      return void send(chatId, s.unknown);
  }
}

async function onCallback(query) {
  const chatId = query.message?.chat?.id;
  if (!chatId) return;
  await call('answerCallbackQuery', { callback_query_id: query.id }).catch(() => {});

  const session = touch(chatId);
  if (!session) return void send(chatId, BOT.uz.unknown);

  const [kind, value] = String(query.data || '').split(':');

  if (kind === 'lang' && session.step === 'lang' && LANGUAGES.includes(value)) {
    session.data.lang = value;
    session.step = 'name';
    return void send(chatId, copy(value).askName);
  }

  if (kind === 'rel' && session.step === 'rel') {
    session.data.relationship = value;
    session.step = 'details';
    return void send(chatId, copy(session.data.lang).askDetails);
  }
}

// ---------------------------------------------------------------------------
// Long polling
// ---------------------------------------------------------------------------

export function startBot() {
  if (!config.telegramToken) {
    console.log('[bot] TELEGRAM_BOT_TOKEN not set — bot disabled, card pages still served');
    return;
  }

  let offset = 0;
  let backoff = 1000;

  const loop = async () => {
    for (;;) {
      try {
        const updates = await call('getUpdates', { offset, timeout: 30, allowed_updates: ['message', 'callback_query'] });
        backoff = 1000;
        for (const update of updates) {
          offset = update.update_id + 1;
          try {
            if (update.message?.text) await onText(update.message);
            else if (update.callback_query) await onCallback(update.callback_query);
          } catch (error) {
            console.error('[bot] update failed:', error?.message || error);
          }
        }
      } catch (error) {
        console.error('[bot] poll failed:', error?.message || error);
        await new Promise(resolve => setTimeout(resolve, backoff));
        backoff = Math.min(backoff * 2, 60000);
      }
    }
  };

  call('getMe')
    .then(me => {
      console.log(`[bot] polling as @${me.username}`);
      if (!process.env.BOT_USERNAME) process.env.BOT_USERNAME = me.username;
      loop();
    })
    .catch(error => console.error('[bot] getMe failed, bot not started:', error?.message || error));
}
