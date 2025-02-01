import os
import re
from dotenv import load_dotenv

load_dotenv()

import requests
from groq import Groq
from supabase import create_client

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext, ConversationHandler

# --- Configuration Variables ---
GROQ_API_KEY = "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"
TELEGRAM_BOT_TOKEN = "7730702253:AAFZPSCqCUbRSnxacHWP_UKsLsLG-bERUcA"

client = Groq(api_key=GROQ_API_KEY)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

QUESTION_1, QUESTION_2, QUESTION_3, QUESTION_4, QUESTION_5 = range(5)

responses = {}


async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        "Welcome! This is a Telegram bot for ScholarsHub. Bot is currently under development, "
        "but you can try using the bot's AI feature. Let's register you first!\n\nWhat is your name?"
    )
    return QUESTION_1


async def question_1(update: Update, context: CallbackContext) -> int:
    responses['name'] = update.message.text
    await update.message.reply_text("Thanks! What is your age?")
    return QUESTION_2


async def question_2(update: Update, context: CallbackContext) -> int:
    responses['age'] = update.message.text
    await update.message.reply_text("Great! What is your phone number?")
    return QUESTION_3


async def question_3(update: Update, context: CallbackContext) -> int:
    responses['phone_number'] = update.message.text
    await update.message.reply_text("What are your interests?")
    return QUESTION_4


async def question_4(update: Update, context: CallbackContext) -> int:
    responses['interest'] = update.message.text
    await update.message.reply_text("What is your SAT score or approximate SAT score?")
    return QUESTION_5


async def question_5(update: Update, context: CallbackContext) -> int:
    responses['sat'] = update.message.text
    await update.message.reply_text(
        "You are registered!\n\nPress /menu to access AI Features."
    )
    save_to_database(responses, update.effective_user.id)
    return ConversationHandler.END


def save_to_database(data, telegram_id):
    print("Saving to database:", data)
    result = supabase.table("students").insert({
        "name": data['name'],
        "phone_number": data['phone_number'],
        "telegram_id": telegram_id,
        "age": data['age'],
        "interest": data['interest'],
        "sat": data['sat'],
        "vocabulary": ""
    }).execute()
    print("Insertion Result:", result)
    retrieved = supabase.table("students").select("*").execute()
    print("Retrieved Data:", retrieved)


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



def extract_unique_words(text: str):

    words = re.findall(r'\b\w+\b', text)
    unique_words = list(set(words))
    unique_words = [word for word in unique_words if len(word) > 3]
    return unique_words


async def handle_image(update: Update, context: CallbackContext) -> None:
    if update.message.photo:
        # Get the highest-resolution photo
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
                            "text": (
                                "Act like a Scholastic Aptitude Test tutor. You will be given the image of the SAT question that you should analyze. Analyze the question NEATLY. Look if it is DIGITAL SAT QUESTION. If the image does not match the SAT question, give a response that the user should send an SAT question. After analyzing the question, DO NOT give an answer directly. Give a HINT to the solution! You may have questions with both options like A, B, C, D or open-ended Math questions. Give a HINT before giving an ANSWER!"
                            )
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

        unique_words = extract_unique_words(answer)
        if unique_words:
            context.chat_data["word_list"] = unique_words

            # Create an inline keyboard with the extracted unique words
            keyboard = [[InlineKeyboardButton(word, callback_data=word) for word in unique_words]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Choose a word to add to your vocabulary list:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("No vocabulary words found in the answer.")
    else:
        await update.message.reply_text("Please send an image of the SAT question.")


async def button_click(update: Update, context: CallbackContext) -> None:

    query = update.callback_query
    await query.answer()
    selected_word = query.data

    if "word_list" in context.chat_data and selected_word in context.chat_data["word_list"]:
        context.chat_data["word_list"].remove(selected_word)

    try:
        student_response = supabase.table("students") \
            .select("*") \
            .eq("telegram_id", update.effective_user.id) \
            .execute()

        if student_response.data:
            student_record = student_response.data[0]
            current_vocab = student_record.get("vocabulary", "")
            if current_vocab.strip():
                vocab_list = [word.strip() for word in current_vocab.split(",")]
            else:
                vocab_list = []

            if selected_word not in vocab_list:
                vocab_list.append(selected_word)

            new_vocab = ", ".join(vocab_list)

            update_result = supabase.table("students") \
                .update({"vocabulary": new_vocab}) \
                .eq("telegram_id", update.effective_user.id) \
                .execute()
            print("Updated vocabulary:", update_result)
        else:
            print("Student record not found for", update.effective_user.id)
            await query.edit_message_text("Could not find your student record.")
            return

    except Exception as e:
        print("Error updating vocabulary:", e)
        await query.edit_message_text("An error occurred while saving your selection.")
        return

    updated_list = context.chat_data.get("word_list", [])
    if updated_list:
        keyboard = [[InlineKeyboardButton(word, callback_data=word) for word in updated_list]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Choose another word:", reply_markup=reply_markup)
    else:
        await query.edit_message_text("All words have been selected!")



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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_solver))

    application.add_handler(CallbackQueryHandler(button_click))

    application.run_polling()


if __name__ == "__main__":
    main()
