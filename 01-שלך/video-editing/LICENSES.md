# רישיונות וקרדיטים

הסקיל עצמו (הסקריפטים וההוראות) מיועד לשימוש אישי של משתתפי הסדנה.
הרכיבים המצורפים והכלים שמותקנים בהרצה ראשונה הם קוד פתוח, לפי הפירוט:

## מודלים מצורפים (בתיקיית `models/`)

| קובץ                                           | מקור                                                             | רישיון       |
| ---------------------------------------------- | ---------------------------------------------------------------- | ------------ |
| `yunet.onnx`                                   | YuNet face detection, OpenCV Zoo (Shiqi Yu)                      | MIT          |
| `MobileNetSSD_deploy.caffemodel` + `.prototxt` | chuanqi305/MobileNet-SSD                                         | MIT          |
| `bd.rnnn`                                      | מודל הפחתת רעש מפרויקט rnnoise-models, מבוסס RNNoise של Xiph.Org | BSD-3-Clause |

## כלים שמותקנים ב-`setup.sh` (לא מופצים בחבילה)

| כלי                                          | רישיון     |
| -------------------------------------------- | ---------- |
| ffmpeg / ffprobe (דרך ffmpeg-static ב-npm)   | LGPL/GPL   |
| mlx-whisper (Apple) + מודלי Whisper (OpenAI) | MIT        |
| opencv-python                                | Apache 2.0 |
| Pillow                                       | MIT-CMU    |

## פונט

הפונט `Arial Bold` **אינו מופץ עם החבילה** (פונט מסחרי של Monotype).
בהרצת `setup.sh` הוא מועתק מספריית הפונטים של המק שלך
(`/System/Library/Fonts/Supplemental/`) אל `fonts/` - עותק מקומי בלבד,
במסגרת רישיון macOS שכבר יש לך. הוא לא עוזב את המחשב שלך.
