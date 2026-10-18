#!/usr/bin/env node
// ─────────────────────────────────────────────────────────────
// התקנת קול לבוט הוואטסאפ — Mac, Windows ו-Linux
//
// מתקין את מנוע התמלול, מחבר אותו לבוט, ומריץ בדיקה אמיתית.
// לא מדווח על הצלחה לפני שתמלול אמיתי עבר.
// ─────────────────────────────────────────────────────────────

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BOT_DIR = process.argv[2] || process.cwd();
const WIN = process.platform === "win32";

const PKGS = ["@huggingface/transformers", "ffmpeg-static", "onnxruntime-node"];

function step(n, msg) {
  console.log(`\n[${n}/5] ${msg}`);
}
function die(msg) {
  console.error(`\n❌ ${msg}\n`);
  process.exit(1);
}

// ── 1. איפה הבוט ──────────────────────────────────────────────
step(1, "מאתר את תיקיית הבוט");

const BOT_FILES = ["green-api-bot.js", "bot.js", "index.js"];
const botFile = BOT_FILES.map((f) => path.join(BOT_DIR, f)).find((p) =>
  fs.existsSync(p),
);
if (!botFile)
  die(
    `לא מצאתי קובץ בוט בתיקייה:\n   ${BOT_DIR}\n` +
      `   חיפשתי: ${BOT_FILES.join(", ")}\n` +
      `   הרץ את הפקודה מתוך תיקיית הבוט.`,
  );
console.log(`   ✅ ${path.basename(botFile)}`);

// ── 2. מקום בדיסק ─────────────────────────────────────────────
step(2, "בודק מקום בדיסק");
try {
  const { bavail, bsize } = fs.statfsSync(BOT_DIR);
  const freeGb = (bavail * bsize) / 1024 ** 3;
  console.log(`   ${freeGb.toFixed(1)} ג'יגה פנויים`);
  if (freeGb < 3)
    die(
      `צריך לפחות 3 ג'יגה פנויים והמודל לא ייכנס.\n` +
        `   פנה מקום בדיסק ונסה שוב.`,
    );
  console.log("   ✅ יש מספיק מקום");
} catch {
  console.log("   ⏭️  לא הצלחתי לבדוק — ממשיך");
}

// ── 3. התקנת החבילות ──────────────────────────────────────────
step(3, "מתקין את מנוע התמלול (הורדה גדולה, כמה דקות)");
try {
  execFileSync(WIN ? "npm.cmd" : "npm", ["install", ...PKGS], {
    cwd: BOT_DIR,
    stdio: "inherit",
    shell: WIN,
  });
} catch {
  die("ההתקנה נכשלה. בדוק חיבור אינטרנט ונסה שוב.");
}
for (const p of PKGS) {
  if (!fs.existsSync(path.join(BOT_DIR, "node_modules", ...p.split("/"))))
    die(`החבילה ${p} לא הותקנה.`);
}
console.log("   ✅ שלוש החבילות מותקנות");

// ── 4. חיבור המודול ───────────────────────────────────────────
step(4, "מחבר את מודול הקול לבוט");
fs.copyFileSync(path.join(HERE, "voice.js"), path.join(BOT_DIR, "voice.js"));
console.log("   ✅ voice.js הועתק לתיקיית הבוט");

// ── 5. בדיקה אמיתית ───────────────────────────────────────────
step(5, "מתמלל הקלטה אמיתית בעברית (הפעם הראשונה אטית)");
const sample = path.join(HERE, "assets", "sample-he.ogg");
let transcript = "";
try {
  const { transcribeFile } = await import(
    "file://" + path.join(BOT_DIR, "voice.js").replace(/\\/g, "/")
  );
  transcript = await transcribeFile(sample);
} catch (e) {
  die(`התמלול נכשל: ${e.message}`);
}
if (!transcript || transcript.length < 4)
  die(`התמלול חזר ריק — המנוע לא עובד.`);

console.log(`\n   📝 התמליל: "${transcript}"`);
console.log(`
═══════════════════════════════════════════
✅ הקול מותקן ועובד.

שלח לבוט הקלטה בוואטסאפ והוא יתמלל אותה.
ההקלטה הראשונה לוקחת כ-20 שניות, הבאות מהירות.
═══════════════════════════════════════════
`);
