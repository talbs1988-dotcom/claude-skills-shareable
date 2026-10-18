// ─────────────────────────────────────────────────────────────
// voice.js · תמלול הקלטות וואטסאפ
//
// רץ על המחשב שלך. אין מפתח API, אין עלות, וההקלטות לא יוצאות לאינטרנט.
// המודל יורד פעם אחת בשימוש הראשון (כ-250 מגה) ואז נשמר.
// ─────────────────────────────────────────────────────────────

import { pipeline, env as hfEnv } from "@huggingface/transformers";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import ffmpegBin from "ffmpeg-static";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const execFileAsync = promisify(execFile);

// whisper-large-v3-turbo בגרסה מכווצת (q8): הדיוק של המודל הגדול
// במהירות של הקטן. נבדק על עברית — 4 שניות להקלטה של 3 שניות.
const MODEL = process.env.VOICE_MODEL || "onnx-community/whisper-large-v3-turbo";
const DTYPE = process.env.VOICE_DTYPE || "q8";

hfEnv.allowLocalModels = false;

// המודל נשמר בתיקיית הבוט ולא בתוך node_modules, כדי שהתקנה מחדש
// של חבילות לא תמחק אותו ותגרום להורדה מיותרת של מאות מגה.
hfEnv.cacheDir = path.join(path.dirname(fileURLToPath(import.meta.url)), ".voice-models");

let enginePromise = null;

// המודל נטען פעם אחת ונשאר בזיכרון — לכן ההקלטה הראשונה אטית והבאות מהירות
function getEngine() {
  if (!enginePromise) {
    enginePromise = pipeline("automatic-speech-recognition", MODEL, {
      dtype: DTYPE,
    }).catch((e) => {
      enginePromise = null; // כדי שניסיון הבא לא ייתקע על שגיאה שנשמרה
      throw e;
    });
  }
  return enginePromise;
}

// ogg/opus של וואטסאפ → Float32 של 16 קילוהרץ, מה ש-whisper צריך
async function toAudio(oggPath) {
  const wav = path.join(
    os.tmpdir(),
    `voice-${crypto.randomBytes(6).toString("hex")}.wav`,
  );
  try {
    await execFileAsync(ffmpegBin, [
      "-y", "-i", oggPath,
      "-ar", "16000", "-ac", "1", "-f", "wav",
      wav,
    ]);
    const buf = await fs.readFile(wav);
    // 44 הבתים הראשונים בקובץ wav הם כותרת, אחריהם הקול עצמו
    const pcm = new Int16Array(
      buf.buffer,
      buf.byteOffset + 44,
      Math.floor((buf.length - 44) / 2),
    );
    return Float32Array.from(pcm, (v) => v / 32768);
  } finally {
    await fs.rm(wav, { force: true });
  }
}

/**
 * מתמלל קובץ הקלטה ומחזיר את הטקסט.
 * @param {string} oggPath נתיב לקובץ ההקלטה שהורד מוואטסאפ
 * @returns {Promise<string>} התמליל בעברית
 */
export async function transcribeFile(oggPath) {
  const audio = await toAudio(oggPath);
  const seconds = audio.length / 16000;
  if (seconds < 0.3) throw new Error("ההקלטה קצרה מדי");

  const asr = await getEngine();
  const out = await asr(audio, {
    language: "hebrew",
    task: "transcribe",
    // הקלטות ארוכות מ-30 שניות מתומללות במקטעים
    chunk_length_s: seconds > 30 ? 30 : undefined,
    stride_length_s: seconds > 30 ? 5 : undefined,
  });

  const text = (out?.text || "").trim();
  if (!text) throw new Error("לא זוהה דיבור בהקלטה");
  return text;
}

/**
 * מתמלל הקלטה שהורדה לזיכרון (Buffer).
 */
export async function transcribeBuffer(buffer) {
  const ogg = path.join(
    os.tmpdir(),
    `voice-${crypto.randomBytes(6).toString("hex")}.ogg`,
  );
  await fs.writeFile(ogg, buffer);
  try {
    return await transcribeFile(ogg);
  } finally {
    await fs.rm(ogg, { force: true });
  }
}
