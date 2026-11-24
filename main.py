
import os
import asyncio
import subprocess
import tempfile
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
import edge_tts

TOKEN = os.environ.get("BOT_TOKEN")

def run_ffmpeg(args):
    subprocess.run(
        ["ffmpeg", "-y"] + args,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE
    )

def process_video(video_path, output_path, folder):
    audio_path = os.path.join(folder, "audio.wav")
    hindi_path = os.path.join(folder, "hindi.mp3")

    # Extract original audio
    run_ffmpeg([
        "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000",
        audio_path
    ])

    # Recognize all languages
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path, vad_filter=True)

    original_text = " ".join(
        segment.text.strip() for segment in segments
    )

    if not original_text.strip():
        raise Exception("Video mein speech nahi mili.")

    # Translate into Hindi
    hindi_text = GoogleTranslator(
        source="auto", target="hi"
    ).translate(original_text)

    # Generate Hindi voice
    async def make_voice():
        communicate = edge_tts.Communicate(
            hindi_text,
            "hi-IN-SwaraNeural"
        )
        await communicate.save(hindi_path)

    asyncio.run(make_voice())

    # Replace original audio with Hindi voice
    run_ffmpeg([
        "-i", video_path,
        "-i", hindi_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-af", "apad",
        "-shortest",
        output_path
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Namaste! Mujhe English, German ya kisi bhi supported language ka video bhejiye. Main Hindi voice banane ki koshish karunga."
    )

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    media = message.video or message.document

    if not media:
        return

    if message.document and not (
        media.mime_type or ""
    ).startswith("video/"):
        await message.reply_text("Kripya MP4 video bhejiye.")
        return

    await message.reply_text(
        "Video mil gaya! Hindi voice ban rahi hai. Kripya intezar karein."
    )

    try:
        with tempfile.TemporaryDirectory() as folder:
            input_path = os.path.join(folder, "input.mp4")
            output_path = os.path.join(folder, "output.mp4")

            file = await context.bot.get_file(media.file_id)
            await file.download_to_drive(input_path)

            await asyncio.to_thread(
                process_video,
                input_path,
                output_path,
                folder
            )

            with open(output_path, "rb") as video:
                await message.reply_video(
                    video=video,
                    caption="Hindi Voice Dubbing Complete!"
                )

    except Exception as e:
        print("ERROR:", str(e))
        await message.reply_text(
            "Video process nahi ho paya. Chhota MP4 video dobara bhejiye."
        )

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN set nahi hai.")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(
            filters.VIDEO | filters.Document.VIDEO,
            video_handler
        )
    )

    print("Hindi Video Dubbing Bot Started!")
    app.run_polling()

if __name__ == "__main__":
    main()
  
