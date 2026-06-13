#!/usr/bin/env node
// Green API ↔ Claude WhatsApp Bot
// המוח של הבוט (Claude) זהה — רק הצינור (Green API) מחליף את Baileys.

import { spawn } from "child_process";
import path from "path";
import fs from "fs";
import http from "http";
import os from "os";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ---------- env ----------
// Priority: 1) process.env (cloud — Railway/Heroku) 2) local .env file (Mac/Windows)
function loadEnv() {
  // First — use process.env directly (cloud deployments set these as env vars)
  if (process.env.GREEN_API_INSTANCE_ID && process.env.GREEN_API_TOKEN) {
    return process.env;
  }

  // Fallback — read from local .env file (same directory as the bot)
  const envPath = path.join(__dirname, ".env");
  if (!fs.existsSync(envPath)) {
    console.error("❌ .env not found at", envPath);
    console.error(
      "   Either set GREEN_API_* env vars (cloud) or create a .env file (local).",
    );
    process.exit(1);
  }
  const text = fs.readFileSync(envPath, "utf8");
  const env = { ...process.env };
  for (const line of text.split("\n")) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m) env[m[1]] = m[2].trim();
  }
  return env;
}
const env = loadEnv();
const INSTANCE_ID = env.GREEN_API_INSTANCE_ID;
const TOKEN = env.GREEN_API_TOKEN;
if (!INSTANCE_ID || !TOKEN) {
  console.error("❌ missing GREEN_API_INSTANCE_ID or GREEN_API_TOKEN");
  process.exit(1);
}
const API_BASE = `https://api.green-api.com/waInstance${INSTANCE_ID}`;

// ---------- paths ----------
const CONFIG_PATH = path.join(__dirname, "config.json");
const SESSIONS_PATH = path.join(__dirname, "sessions-greenapi.json");
const FEED_PATH = path.join(__dirname, "feed-greenapi.json");
const LOG_FILE = path.join(__dirname, "green-api-bot.log");
const DASHBOARD_PORT = parseInt(process.env.PORT || "7654", 10);

// ---------- config ----------
function loadConfig() {
  return JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
}
let config = loadConfig();
const CLAUDE_BIN = config.claudeBin || "claude";

// ---------- logging ----------
const logStream = fs.createWriteStream(LOG_FILE, { flags: "a" });
function log(...args) {
  const ts = new Date().toLocaleTimeString("he-IL", { hour12: false });
  const msg = `[${ts}] ${args
    .map((a) => (typeof a === "string" ? a : JSON.stringify(a)))
    .join(" ")}`;
  console.log(msg);
  logStream.write(msg + "\n");
}

// ---------- sessions persistence (per user, for Claude --resume) ----------
let userSessions = {};
try {
  userSessions = JSON.parse(fs.readFileSync(SESSIONS_PATH, "utf8"));
} catch {}
function saveSessions() {
  fs.writeFileSync(SESSIONS_PATH, JSON.stringify(userSessions, null, 2));
}

// ---------- feed (recent in/out for dashboard) ----------
let feed = [];
try {
  feed = JSON.parse(fs.readFileSync(FEED_PATH, "utf8"));
} catch {}
function addFeed(dir, from, text) {
  feed.push({ t: Date.now(), dir, from, text });
  if (feed.length > 200) feed = feed.slice(-200);
  fs.writeFile(FEED_PATH, JSON.stringify(feed, null, 2), () => {});
}

// ---------- Green API helpers ----------
async function apiGET(endpoint) {
  const url = `${API_BASE}/${endpoint}/${TOKEN}`;
  const r = await fetch(url, { signal: AbortSignal.timeout(35000) });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`${endpoint} → ${r.status}`);
  const text = await r.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

async function sendMessage(chatId, text) {
  const url = `${API_BASE}/sendMessage/${TOKEN}`;
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chatId, message: text }),
    signal: AbortSignal.timeout(30000),
  });
  if (!r.ok) throw new Error(`sendMessage → ${r.status}`);
  return await r.json();
}

async function deleteNotification(receiptId) {
  const url = `${API_BASE}/deleteNotification/${TOKEN}/${receiptId}`;
  await fetch(url, { method: "DELETE", signal: AbortSignal.timeout(10000) });
}

// ---------- whitelist check ----------
function isWhitelisted(senderPhone) {
  const wl = config.whitelist || [];
  return wl.some((n) => {
    const clean = String(n).replace(/^\+/, "").replace(/\D/g, "");
    return clean === senderPhone;
  });
}

// ---------- Claude invocation ----------
function getSystemAppend() {
  const custom = (config.systemPromptAppend || "").trim();
  if (custom) return custom;
  return `אתה "${config.agentName || "הסוכן"}" — בוט WhatsApp של טל. ענה בעברית, קצר וישיר.`;
}

function askClaude(prompt, userKey) {
  return new Promise((resolve, reject) => {
    const resumeId = userSessions[userKey];
    const args = [
      "-p",
      prompt,
      "--append-system-prompt",
      getSystemAppend(),
      "--output-format",
      "json",
      "--model",
      config.model || "sonnet",
      "--permission-mode",
      config.permissionMode || "bypassPermissions",
    ];
    if (resumeId) args.push("--resume", resumeId);

    const cwd = config.workdir || os.homedir();
    const cp = spawn(CLAUDE_BIN, args, { cwd, env: process.env });
    let out = "";
    let err = "";
    const timer = setTimeout(() => {
      cp.kill("SIGTERM");
      reject(new Error("Claude timeout (3m)"));
    }, 180_000);
    cp.stdout.on("data", (d) => (out += d.toString()));
    cp.stderr.on("data", (d) => (err += d.toString()));
    cp.on("error", (e) => {
      clearTimeout(timer);
      reject(e);
    });
    cp.on("exit", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        reject(new Error((err.slice(-200) || `exit ${code}`).trim()));
        return;
      }
      try {
        const json = JSON.parse(out);
        const reply = (json.result || json.response || "").trim() || "(ריק)";
        if (json.session_id) {
          userSessions[userKey] = json.session_id;
          saveSessions();
        }
        resolve(reply);
      } catch {
        resolve(out.trim() || "(ריק)");
      }
    });
  });
}

// ---------- extract text from various message types ----------
function extractText(messageData) {
  if (!messageData) return "";
  const t = messageData.typeMessage;
  if (t === "textMessage")
    return messageData.textMessageData?.textMessage || "";
  if (t === "extendedTextMessage")
    return messageData.extendedTextMessageData?.text || "";
  if (t === "quotedMessage")
    return messageData.extendedTextMessageData?.text || "";
  return "";
}

// ---------- main message handler ----------
async function handleNotification(notif) {
  const body = notif.body;
  if (!body) return;
  const type = body.typeWebhook;

  // accept either incoming (from contacts) or outgoing-from-other-device (Self-Chat from her phone)
  const isIncoming = type === "incomingMessageReceived";
  const isSelfFromPhone = type === "outgoingMessageReceived";
  if (!isIncoming && !isSelfFromPhone) {
    return;
  }

  const sender = body.senderData?.sender || ""; // e.g. "972501234567@c.us"
  const chatId = body.senderData?.chatId || sender;
  const senderName = body.senderData?.senderName || "";
  const messageData = body.messageData || {};

  const text = extractText(messageData).trim();
  if (!text) {
    log(`📎 ${type} non-text (${messageData.typeMessage}) — ignored`);
    return;
  }

  const senderPhone = sender.split("@")[0];
  const chatPhone = chatId.split("@")[0];
  const isGroup = chatId.endsWith("@g.us");

  // for Self-Chat detection: outgoingMessageReceived where sender == chatId == her own number
  let isSelfChat = false;
  if (isSelfFromPhone) {
    if (senderPhone === chatPhone && isWhitelisted(senderPhone)) {
      isSelfChat = true;
    } else {
      // outgoing to someone else (her sending TO contact from her phone) — ignore
      return;
    }
  }

  log(
    `📨 ${type} from=${senderPhone} chat=${chatPhone} group=${isGroup} self=${isSelfChat} text="${text.slice(0, 50)}"`,
  );

  // group filter (uses same setting as old bot)
  if (isGroup) {
    const gm = config.groupMode || "off";
    if (gm === "off") {
      log("⛔ group ignored (groupMode=off)");
      return;
    }
  }

  // whitelist check (self-chat bypasses)
  if (!isSelfChat && !isWhitelisted(senderPhone)) {
    log("⛔ blocked (not in whitelist):", senderPhone);
    return;
  }

  addFeed("in", senderPhone, text);

  // ask Claude
  try {
    const userKey = senderPhone;
    log("🧠 sending to Claude...");
    const reply = await askClaude(text, userKey);
    log(`🤖 reply (${reply.length} chars): ${reply.slice(0, 80)}...`);
    await sendMessage(chatId, reply);
    addFeed("out", senderPhone, reply);
    log("✅ sent");
  } catch (e) {
    log("❌ error:", e.message);
    try {
      await sendMessage(chatId, `(שגיאה פנימית: ${e.message.slice(0, 100)})`);
    } catch {}
  }
}

// ---------- polling loop ----------
let stopped = false;
let lastPollOk = Date.now();

async function pollLoop() {
  log(`🟢 starting poll loop (instance ${INSTANCE_ID})`);
  let consecutiveErrors = 0;
  while (!stopped) {
    try {
      const notif = await apiGET("receiveNotification");
      lastPollOk = Date.now();
      consecutiveErrors = 0;
      if (notif) {
        const receiptId = notif.receiptId;
        try {
          await handleNotification(notif);
        } catch (e) {
          log("handler crashed:", e.message);
        }
        try {
          await deleteNotification(receiptId);
        } catch (e) {
          log("delete failed:", e.message);
        }
      }
      // small jitter to avoid hammering
      await new Promise((r) => setTimeout(r, 100));
    } catch (e) {
      consecutiveErrors++;
      const wait = Math.min(30000, 2000 * consecutiveErrors);
      log(
        `⚠️ poll error (#${consecutiveErrors}): ${e.message} — retry in ${wait / 1000}s`,
      );
      await new Promise((r) => setTimeout(r, wait));
    }
  }
}

// ---------- mini dashboard ----------
http
  .createServer((req, res) => {
    if (req.url === "/" || req.url === "/index.html") {
      const since = Math.round((Date.now() - lastPollOk) / 1000);
      const status =
        since < 60
          ? `<span style="color:#25d366">🟢 פעיל (polling אחרון לפני ${since}ש)</span>`
          : `<span style="color:#e74c3c">🔴 לא תקין (אחרון לפני ${since}ש)</span>`;
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      res.end(`<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="utf-8"><title>Green API Bot — ${config.agentName || "Bot"}</title>
<meta http-equiv="refresh" content="10">
<style>
body{font-family:-apple-system,system-ui,sans-serif;background:#f0ede5;padding:20px;max-width:900px;margin:auto;color:#333}
.card{background:white;border-radius:10px;padding:18px;margin:12px 0;box-shadow:0 2px 6px rgba(0,0,0,0.06)}
h1{color:#25d366;margin:0 0 8px}
h3{margin:0 0 12px;color:#444;font-size:15px}
.kv{margin:6px 0;font-size:14px}
.kv b{color:#666}
.feed-entry{padding:8px 0;border-bottom:1px solid #eee;font-size:13px;line-height:1.5}
.feed-entry:last-child{border:none}
.in{color:#1e88e5}.out{color:#25d366}
.t{color:#999;font-size:11px}
</style></head>
<body>
<h1>🤖 ${config.agentName || "Bot"} <small style="font-size:14px;color:#888">(Green API)</small></h1>
<div class="card">
<div class="kv"><b>סטטוס:</b> ${status}</div>
<div class="kv"><b>Instance:</b> ${INSTANCE_ID}</div>
<div class="kv"><b>Whitelist:</b> ${(config.whitelist || []).join(", ") || "(ריק)"}</div>
<div class="kv"><b>סה"כ הודעות בפיד:</b> ${feed.length}</div>
</div>
<div class="card">
<h3>הודעות אחרונות (20)</h3>
${
  feed.length === 0
    ? '<p style="color:#999">עוד לא נכנסו הודעות. שלחי הודעה לעצמך ב-WhatsApp לבדיקה.</p>'
    : feed
        .slice(-20)
        .reverse()
        .map(
          (f) =>
            `<div class="feed-entry"><span class="t">[${new Date(f.t).toLocaleTimeString("he-IL")}]</span> <span class="${f.dir}">${f.dir === "in" ? "⬅️ נכנס" : "➡️ יוצא"}</span> מ/אל <b>${f.from}</b>: ${(f.text || "").slice(0, 200).replace(/[<>]/g, "")}</div>`,
        )
        .join("")
}
</div>
<p style="text-align:center;color:#aaa;font-size:12px">מתרענן אוטומטית כל 10 שניות</p>
</body></html>`);
      return;
    }
    if (req.url === "/state") {
      res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
      res.end(
        JSON.stringify({
          instance: INSTANCE_ID,
          agentName: config.agentName,
          whitelist: config.whitelist || [],
          feedSize: feed.length,
          lastPollAgoSec: Math.round((Date.now() - lastPollOk) / 1000),
          feed: feed.slice(-50),
        }),
      );
      return;
    }
    // /group/send — Baileys-compatible endpoint so existing automations (morning-agenda, etc.) keep working.
    // accepts {jid, text} where jid is "972501234567@s.whatsapp.net" or "...@g.us" or "...@c.us".
    if (req.url === "/group/send" && req.method === "POST") {
      let body = "";
      req.on("data", (c) => (body += c));
      req.on("end", async () => {
        try {
          const { jid, text } = JSON.parse(body);
          if (!jid || !text) throw new Error("missing jid or text");
          // translate JID: Green API uses @c.us for individuals and @g.us for groups
          let chatId = jid;
          if (jid.endsWith("@s.whatsapp.net")) {
            chatId = jid.replace("@s.whatsapp.net", "@c.us");
          }
          await sendMessage(chatId, text);
          log(`📤 /group/send → ${chatId}: ${text.slice(0, 60)}...`);
          addFeed("out", chatId.split("@")[0], text);
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ ok: true }));
        } catch (e) {
          log("❌ /group/send error:", e.message);
          res.writeHead(500, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ ok: false, error: e.message }));
        }
      });
      return;
    }
    res.writeHead(404).end("not found");
  })
  .listen(DASHBOARD_PORT, "127.0.0.1", () => {
    log(`🌐 dashboard: http://127.0.0.1:${DASHBOARD_PORT}`);
  });

// ---------- shutdown ----------
function shutdown() {
  log("👋 shutting down");
  stopped = true;
  setTimeout(() => process.exit(0), 1500);
}
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

// ---------- start ----------
log(`🚀 Green API bot starting (port ${DASHBOARD_PORT})`);
pollLoop().catch((e) => {
  log("💥 poll loop crashed:", e.message);
  process.exit(1);
});
