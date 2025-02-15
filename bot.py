import logging
import random
import copy
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

GRID_SIZE = 4
XO_SIZE = 3


def new_game():
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    add_new_number(grid)
    add_new_number(grid)
    return grid


def add_new_number(grid):
    empty_cells = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if grid[r][c] == 0]
    if empty_cells:
        r, c = random.choice(empty_cells)
        grid[r][c] = 2 if random.random() < 0.9 else 4


def render_grid(grid):
    emoji_dict = {0: "⬜", 2: "🟩", 4: "🟦", 8: "🟧", 16: "🟥",
                  32: "🟨", 64: "🟪", 128: "🔶", 256: "🔷",
                  512: "💠", 1024: "🔥", 2048: "🏆"}
    return "\n".join(" ".join(emoji_dict.get(cell, "⬛") for cell in row) for row in grid)


def move_row_left(row):
    new_row = [num for num in row if num != 0]
    for i in range(len(new_row) - 1):
        if new_row[i] == new_row[i + 1]:
            new_row[i] *= 2
            new_row[i + 1] = 0
    new_row = [num for num in new_row if num != 0]
    return new_row + [0] * (GRID_SIZE - len(new_row))


def move_grid(grid, direction):
    old_grid = copy.deepcopy(grid)
    if direction == "left":
        grid = [move_row_left(row) for row in grid]
    elif direction == "right":
        grid = [move_row_left(row[::-1])[::-1] for row in grid]
    elif direction == "up":
        grid = list(map(list, zip(*grid)))
        grid = [move_row_left(row) for row in grid]
        grid = list(map(list, zip(*grid)))
    elif direction == "down":
        grid = list(map(list, zip(*grid)))
        grid = [move_row_left(row[::-1])[::-1] for row in grid]
        grid = list(map(list, zip(*grid)))
    if old_grid != grid:
        add_new_number(grid)
    return grid


def is_game_over(grid):
    for row in grid:
        if 0 in row:
            return False
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE - 1):
            if grid[r][c] == grid[r][c + 1]:
                return False
    for r in range(GRID_SIZE - 1):
        for c in range(GRID_SIZE):
            if grid[r][c] == grid[r + 1][c]:
                return False
    return True


def new_xo_game():
    return [["⬜"] * XO_SIZE for _ in range(XO_SIZE)]


def render_xo_board(board):
    return "\n".join(" ".join(row) for row in board)


def check_winner(board):
    for row in board:
        if row.count("❌") == XO_SIZE:
            return "❌ Победил!"
        if row.count("⭕") == XO_SIZE:
            return "⭕ Победил!"

    for col in range(XO_SIZE):
        if all(board[row][col] == "❌" for row in range(XO_SIZE)):
            return "❌ Победил!"
        if all(board[row][col] == "⭕" for row in range(XO_SIZE)):
            return "⭕ Победил!"

    if all(board[i][i] == "❌" for i in range(XO_SIZE)) or all(board[i][XO_SIZE - i - 1] == "❌" for i in range(XO_SIZE)):
        return "❌ Победил!"
    if all(board[i][i] == "⭕" for i in range(XO_SIZE)) or all(board[i][XO_SIZE - i - 1] == "⭕" for i in range(XO_SIZE)):
        return "⭕ Победил!"

    if all(cell != "⬜" for row in board for cell in row):
        return "🤝 Ничья!"

    return None


async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("🎮 Играть в 2048", callback_data="start_2048")],
        [InlineKeyboardButton("❌⭕ Играть в Крестики-Нолики", callback_data="start_xo")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Выбери игру:", reply_markup=reply_markup)


async def start_2048(update: Update, context):
    query = update.callback_query
    await query.answer()

    grid = new_game()
    context.user_data["2048_grid"] = grid
    await update_grid(update, context, grid)


async def start_xo(update: Update, context):
    query = update.callback_query
    await query.answer()

    board = new_xo_game()
    context.user_data["xo_board"] = board
    await update_xo_board(update, context, board)


async def update_grid(update, context, grid):
    keyboard = [
        [InlineKeyboardButton("⬅️", callback_data="left"), InlineKeyboardButton("⬆️", callback_data="up"),
         InlineKeyboardButton("➡️", callback_data="right")],
        [InlineKeyboardButton("⬇️", callback_data="down")],
        [InlineKeyboardButton("🔄 Начать заново", callback_data="start_2048")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    grid_text = render_grid(grid)

    if is_game_over(grid):
        await update.callback_query.message.edit_text(f"😵 Игра окончена!\n{grid_text}\n\nНажми '🔄 Начать заново'!",
                                                      reply_markup=reply_markup)
    else:
        await update.callback_query.message.edit_text(f"{grid_text}\n\nВыбери направление:", reply_markup=reply_markup)


async def update_xo_board(update, context, board):
    keyboard = [[InlineKeyboardButton(board[r][c], callback_data=f"move_{r}_{c}") for c in range(XO_SIZE)] for r in
                range(XO_SIZE)]
    reply_markup = InlineKeyboardMarkup(keyboard)
    winner = check_winner(board)

    if winner:
        await update.callback_query.message.edit_text(
            f"{winner}\n{render_xo_board(board)}\n\nНажми /start, чтобы сыграть снова.")
    else:
        await update.callback_query.message.edit_text(f"{render_xo_board(board)}\n\nВыбери клетку:",
                                                      reply_markup=reply_markup)


async def xo_move(update: Update, context):
    query = update.callback_query
    await query.answer()
    r, c = map(int, query.data.split("_")[1:])
    board = context.user_data.get("xo_board")

    if board[r][c] == "⬜":
        board[r][c] = "❌"
        if not check_winner(board):
            bot_move = random.choice([(x, y) for x in range(XO_SIZE) for y in range(XO_SIZE) if board[x][y] == "⬜"])
            board[bot_move[0]][bot_move[1]] = "⭕"

        await update_xo_board(update, context, board)


def main():
    TOKEN = "8122182713:AAEvg-cUkioErT571I_UotqfrDE9cvuzfT0"
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start_2048, pattern="start_2048"))
    app.add_handler(CallbackQueryHandler(start_xo, pattern="start_xo"))
    app.add_handler(CallbackQueryHandler(xo_move, pattern="move_.*"))
    app.run_polling()


if __name__ == "__main__":
    main()
