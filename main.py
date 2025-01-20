import requests
from groq import Groq
import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

GROQ_API_KEY = "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"
TELEGRAM_BOT_TOKEN = "7730702253:AAFZPSCqCUbRSnxacHWP_UKsLsLG-bERUcA"

client = Groq(api_key=GROQ_API_KEY)

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)


QUESTION_1, QUESTION_2, QUESTION_3, QUESTION_4, QUESTION_5 = range(5)

responses = {}


# Start command handler
async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        "Welcome! This is a Telegram bot for ScholarsHub. Bot is currently under development, "
        "but you can try using bot's AI feature. Let's register you first! \n\nWhat is your name?"
    )
    return QUESTION_1

async def question_1(update: Update, context: CallbackContext) -> int:
    responses['name'] = update.message.text
    await update.message.reply_text("Thanks! What is your age?")
    return QUESTION_2


async def question_2(update: Update, context: CallbackContext) -> int:
    responses['age'] = update.message.text
    await update.message.reply_text("Great! What is your phone_number?")
    return QUESTION_3

async def question_3(update: Update, context: CallbackContext) -> int:
    responses['phone_number'] = update.message.text
    await update.message.reply_text("What are your interests?")
    return QUESTION_4

async def question_4(update: Update, context: CallbackContext) -> int:
    responses['interest'] = update.message.text
    await update.message.reply_text("What is your SAT score or approximate SAT score")
    return QUESTION_5

async def question_5(update: Update, context: CallbackContext) -> int:
    responses['sat'] = update.message.text
    await update.message.reply_text(
    f"You are registered! \n \n Press /menu to access AI Features")

    save_to_database(responses)

    return ConversationHandler.END


def save_to_database(data):
    print("Saving to database:", data)


    result = supabase.table("students").insert(
        {
            "name": responses['name'],
            "phone_number": responses['phone_number'],
            "telegram_id": 2121240,
            "age": responses['age'],
            "interest": responses['interest'],
            "sat": responses['sat'],
            "vocabulary": "stellar"
        }
    ).execute()
    print("Insertion Result:", result)

    data = supabase.table("students").select("*").execute()
    print("Retrieved Data:", data)

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Questionnaire canceled.")
    return ConversationHandler.END


async def menu(update: Update, context: CallbackContext) -> None:
    context.user_data["menu_active"] = True
    keyboard = [["Solve SAT through AI"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Choose an option from the menu below:", reply_markup=reply_markup)


async def ai_solver(update: Update, context: CallbackContext) -> None:
    if "menu_active" not in context.user_data:
        return

    if update.message.text == "Solve SAT through AI":
        await update.message.reply_text("Please send an SAT question image for analysis.")
    else:
        await update.message.reply_text("Invalid option. Please select a valid menu option.")

async def handle_image(update: Update, context: CallbackContext) -> None:
            if update.message.photo:
                photo = update.message.photo[-1]
                file = await context.bot.get_file(photo.file_id)
                image_url = file.file_path
                completion = client.chat.completions.create(
                    model="llama-3.2-90b-vision-preview",
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
                await update.message.reply_text(f"Image received. Processing image at {image_url}...")
                await update.message.reply_text(f"Answer: {answer}")
            else:
                await update.message.reply_text("Please send an image of the SAT question.")


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            QUESTION_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, question_1)],
            QUESTION_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, question_2)],
            QUESTION_3: [MessageHandler(filters.TEXT & ~filters.COMMAND, question_3)],
            QUESTION_4: [MessageHandler(filters.TEXT & ~filters.COMMAND, question_4)],
            QUESTION_5: [MessageHandler(filters.TEXT & ~filters.COMMAND, question_5)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)

    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_solver))  # Handle menu text

    application.run_polling()

if __name__ == "__main__":
    main()