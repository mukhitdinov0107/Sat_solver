import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

GROQ_API_KEY = "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"
TELEGRAM_BOT_TOKEN = "7520385659:AAGQlf03kEMMayTWlwhuD8ZKF-Aq-Ls-zUY"

client = Groq(api_key=GROQ_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("Hello! Send me an SAT question image, and I'll analyze it for you.")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    image_url = file.file_path  
    
    completion = client.chat.completions.create(
        model="llama-3.2-11b-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "You will be given SAT question images. Analyze each image and give the solution! While giving the solution, look at the option and give your answer in a format: A, B, C, or D"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url  
                        }
                    }
                ]
            }
        ],
        temperature=1,
        max_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )
    
    answer = completion.choices[0].message.content
    
    await update.message.reply_text(f"Answer: {answer}")

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    
    application.run_polling()

if __name__ == '__main__':
    main()
