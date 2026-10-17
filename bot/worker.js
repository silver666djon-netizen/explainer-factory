// CoinSense Telegram inbox bot (Cloudflare Worker).
// Receives files and messages from the owner and stores them in the GitHub repo; buttons start workflows.
// Env (set by .github/workflows/deploy-bot.yml): TG_TOKEN, OWNER_CHAT_ID, GH_TOKEN, GH_REPO, WEBHOOK_SECRET

const GH = "https://api.github.com";

export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("CoinSense bot is running");
    if (request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET) {
      return new Response("forbidden", { status: 403 });
    }
    const update = await request.json();
    try {
      if (update.callback_query) await onButton(update.callback_query, env);
      else if (update.message) await onMessage(update.message, env);
    } catch (e) {
      const chat = update.message?.chat?.id || update.callback_query?.message?.chat?.id;
      if (chat) await tg(env, "sendMessage", { chat_id: chat, text: "⚠️ Ошибка бота: " + String(e).slice(0, 300) });
    }
    return new Response("ok");
  },
};

// ------------------------------------------------------------------ helpers

async function tg(env, method, body) {
  const r = await fetch(`https://api.telegram.org/bot${env.TG_TOKEN}/${method}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  return r.json();
}

async function gh(env, path, init = {}) {
  const r = await fetch(`${GH}/repos/${env.GH_REPO}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`, Accept: "application/vnd.github+json",
      "User-Agent": "coinsense-bot", "Content-Type": "application/json", ...(init.headers || {}),
    },
  });
  if (r.status === 204) return {};
  const data = await r.json().catch(() => ({}));
  if (r.status >= 300 && r.status !== 404) throw new Error(`GitHub ${r.status}: ${JSON.stringify(data).slice(0, 200)}`);
  return r.status === 404 ? null : data;
}

function b64(bytes) {
  let s = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) s += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  return btoa(s);
}

function utf8b64(text) {
  return b64(new TextEncoder().encode(text));
}

async function putFile(env, path, contentB64, message) {
  const existing = await gh(env, `/contents/${path}`);
  const body = { message, content: contentB64, branch: "main" };
  if (existing && existing.sha) body.sha = existing.sha;
  return gh(env, `/contents/${path}`, { method: "PUT", body: JSON.stringify(body) });
}

async function readJson(env, path, fallback) {
  const f = await gh(env, `/contents/${path}`);
  if (!f || !f.content) return fallback;
  return JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(f.content.replace(/\n/g, "")), (c) => c.charCodeAt(0))));
}

async function state(env) {
  return readJson(env, "inbox/state.json", { episode: "" });
}

async function dispatch(env, workflow, inputs) {
  return gh(env, `/actions/workflows/${workflow}/dispatches`, { method: "POST", body: JSON.stringify({ ref: "main", inputs }) });
}

// ------------------------------------------------------------------ handlers

async function onButton(cb, env) {
  const chat = cb.message.chat.id;
  if (String(chat) !== String(env.OWNER_CHAT_ID)) return;
  const [action, slug] = (cb.data || "").split("|");
  if (action === "approve") {
    await dispatch(env, "render.yml", { episode: slug });
    await tg(env, "answerCallbackQuery", { callback_query_id: cb.id, text: "Монтаж запущен" });
    await tg(env, "sendMessage", { chat_id: chat, text: `🎬 Монтаж ${slug} запущен. Готовое видео придёт сюда.` });
  } else if (action === "redo") {
    await tg(env, "answerCallbackQuery", { callback_query_id: cb.id });
    await tg(env, "sendMessage", { chat_id: chat, text: `Напиши номера кадров через пробел, например:\n/redo b17 c03\n(эпизод ${slug})` });
  }
}

async function onMessage(msg, env) {
  const chat = msg.chat.id;
  if (String(chat) !== String(env.OWNER_CHAT_ID)) {
    await tg(env, "sendMessage", { chat_id: chat, text: "Это личный бот канала." });
    return;
  }
  const st = await state(env);
  const text = (msg.text || msg.caption || "").trim();

  // ---- files: images -> episodes/<slug>/images/<key>.<ext>, videos -> episodes/<slug>/clips/<key>.mp4
  const doc = msg.document, video = msg.video, photo = msg.photo ? msg.photo[msg.photo.length - 1] : null;
  if (doc || video || photo) {
    const m = text.match(/^(?:(\d{4}-[\w-]+)\s+)?([a-z]\d+(?:\.\d+)?|thumbnail)\b/i);
    if (!m) {
      await tg(env, "sendMessage", { chat_id: chat, text: "Подпиши файл номером кадра, например: b17 (или: 0003-credit-cards b17)" });
      return;
    }
    const slug = m[1] || st.episode;
    const key = m[2].toLowerCase();
    if (!slug) {
      await tg(env, "sendMessage", { chat_id: chat, text: "Не знаю, к какому выпуску это. Напиши: /episode 0002-casino-chips" });
      return;
    }
    const file = doc || video || photo;
    if (file.file_size && file.file_size > 20 * 1024 * 1024) {
      await tg(env, "sendMessage", { chat_id: chat, text: "Файл больше 20 МБ — Telegram не даёт ботам скачивать такие. Сожми или укороти ролик." });
      return;
    }
    const mime = (doc && doc.mime_type) || (video ? "video/mp4" : "image/jpeg");
    const isVideo = mime.startsWith("video/");
    const info = await tg(env, "getFile", { file_id: file.file_id });
    const bytes = new Uint8Array(await (await fetch(`https://api.telegram.org/file/bot${env.TG_TOKEN}/${info.result.file_path}`)).arrayBuffer());
    const ext = isVideo ? "mp4" : (mime.includes("png") ? "png" : mime.includes("webp") ? "webp" : "jpg");
    const path = isVideo ? `episodes/${slug}/clips/${key}.${ext}` : `episodes/${slug}/images/${key}.${ext}`;
    await putFile(env, path, b64(bytes), `Bot: ${isVideo ? "clip" : "frame"} ${key} for ${slug}`);
    const note = photo ? "\n(пришло как фото — Telegram его сжал; лучше отправлять как файл)" : "";
    await tg(env, "sendMessage", { chat_id: chat, text: `✅ Сохранил ${isVideo ? "вставку" : "кадр"} ${key} для ${slug}.${note}` });
    return;
  }

  // ---- commands
  if (text.startsWith("/episode")) {
    const slug = text.split(/\s+/)[1] || "";
    await putFile(env, "inbox/state.json", utf8b64(JSON.stringify({ ...st, episode: slug }, null, 2)), `Bot: current episode ${slug}`);
    await tg(env, "sendMessage", { chat_id: chat, text: `Текущий выпуск: ${slug}` });
    return;
  }
  if (text.startsWith("/redo")) {
    const parts = text.split(/\s+/).slice(1);
    let slug = st.episode;
    if (parts[0] && /^\d{4}-/.test(parts[0])) slug = parts.shift();
    if (!parts.length || !slug) {
      await tg(env, "sendMessage", { chat_id: chat, text: "Формат: /redo b17 c03" });
      return;
    }
    await dispatch(env, "storyboard.yml", { episode: slug, redo: parts.join(",") });
    await tg(env, "sendMessage", { chat_id: chat, text: `🔁 Переделываю ${parts.join(", ")} в ${slug}. Новая раскадровка придёт сюда.` });
    return;
  }
  if (text.startsWith("/approve")) {
    const slug = text.split(/\s+/)[1] || st.episode;
    await dispatch(env, "render.yml", { episode: slug });
    await tg(env, "sendMessage", { chat_id: chat, text: `🎬 Монтаж ${slug} запущен.` });
    return;
  }
  if (text === "/start" || text === "/help") {
    await tg(env, "sendMessage", { chat_id: chat, text:
      "Я принимаю файлы и отзывы для CoinSense.\n" +
      "• Картинку или видео присылай КАК ФАЙЛ с подписью-номером кадра: b17\n" +
      "• /episode 0003-credit-cards — выбрать текущий выпуск\n" +
      "• /redo b17 c03 — переделать кадры\n" +
      "• /approve — запустить монтаж\n" +
      "• Любой другой текст — отзыв для Claude, я его сохраню." });
    return;
  }

  // ---- anything else: feedback for Claude
  if (text) {
    const f = await gh(env, "/contents/inbox/feedback.md");
    const old = f && f.content ? new TextDecoder().decode(Uint8Array.from(atob(f.content.replace(/\n/g, "")), (c) => c.charCodeAt(0))) : "# Отзывы из Telegram\n";
    const stamp = new Date(msg.date * 1000).toISOString().replace("T", " ").slice(0, 16);
    const reply = msg.reply_to_message ? ` (в ответ на: «${(msg.reply_to_message.text || msg.reply_to_message.caption || "файл").slice(0, 80)}»)` : "";
    const entry = `\n- ${stamp} UTC [${st.episode || "—"}]${reply}: ${text}\n`;
    await putFile(env, "inbox/feedback.md", utf8b64(old + entry), "Bot: feedback");
    await tg(env, "sendMessage", { chat_id: chat, text: "📝 Записал. Claude прочитает, когда вы в следующий раз будете на связи (или напиши ему «глянь телеграм»)." });
  }
}
