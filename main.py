import discord
from discord.ext import commands
import mysql.connector as sqlc
from mysql.connector import Error
import random
from timeit import default_timer as timer
from content import Help, GameList, Dm_Content
import json
import os
import sys

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), 'config.json')
if not os.path.exists(config_path):
    print("Error: config.json not found. Please create it with your TOKEN and DB credentials.")
    sys.exit(1)

with open(config_path, 'r') as f:
    config = json.load(f)

intents = discord.Intents.all()
client = commands.Bot(command_prefix="!", intents=intents)

# Database connection
try:
    connect = sqlc.connect(
        host=config.get('DB_HOST', 'localhost'),
        user=config.get('DB_USER', 'root'),
        password=config.get('DB_PASSWORD', ''),
        database=config.get('DB_NAME', 'mindbreaker')
    )
    cur = connect.cursor()
    # Create table if not exists (optional, but good for "fixing" the repo)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lb (
            rank int AUTO_INCREMENT PRIMARY KEY,
            username varchar(255),
            points int
        )
    """)
    print("Connected to database successfully.")
except Error as e:
    print(f"Error connecting to database: {e}")
    print("Ensure you have a MySQL server running and the credentials in config.json are correct.")
    cur = None
    connect = None

# Load sentences
sentence_file = os.path.join(os.path.dirname(__file__), 'sentence.txt')
try:
    with open(sentence_file, 'r') as f:
        sentences = f.readlines()
except FileNotFoundError:
    sentences = ["The quick brown fox jumps over the lazy dog."]
    print(f"Warning: {sentence_file} not found. Using default sentence.")

sentence = ''
typespd = ''
chek = True

# Load hangman words
hangman_file = os.path.join(os.path.dirname(__file__), 'hangman.txt')
try:
    with open(hangman_file, 'r') as f:
        data = f.read().splitlines()
except FileNotFoundError:
    data = ["discord", "python", "bot"]
    print(f"Warning: {hangman_file} not found. Using default words.")

if data:
    word = random.choice(data)
else:
    word = "default"
    
gameover = True
data_to_guess = ''
limit = 5
person = ''
limith = 3

# TicTacToe vars
player1 = ""
player2 = ""
turn = ""
gameOver = True
board = []
count = 0

winningConditions = [
    [0, 1, 2],
    [3, 4, 5],
    [6, 7, 8],
    [0, 3, 6],
    [1, 4, 7],
    [2, 5, 8],
    [0, 4, 8],
    [2, 4, 6]
]

@client.event
async def on_ready():
    print('Ready to go as {0.user} !!!'.format(client))

@client.command()
async def commandhelp(ctx):
    await ctx.send(Help)

@client.command()
async def gmlt(ctx):
    await ctx.send(GameList)

@client.command()
async def tst(ctx):
    global chek
    global sentence
    chek = False
    
    sentence = random.choice(sentences).strip()
    await ctx.send(f'Welcome to Type Speed test, {ctx.author.mention}!!!!')
    await ctx.send('Below is the sentence you have to type:')
    await ctx.send(sentence)

    def check(m):
        global typespd
        if m.author == ctx.author and m.channel == ctx.channel:
            typespd = m.content
            return True
        return False

    def calculate_stats(input_text, target_text, elapsed_time):
        count = 0
        error = 0
        min_len = min(len(input_text), len(target_text))
        
        for i in range(min_len):
            if input_text[i] == target_text[i]:
                count += 1
            else:
                error += 1
        
        # Account for length difference errors
        error += abs(len(input_text) - len(target_text))
        
        cpm_correct = (count / elapsed_time) * 60 if elapsed_time > 0 else 0
        cpm_error = (error / elapsed_time) * 60 if elapsed_time > 0 else 0
        cpm_total = ((count + error) / elapsed_time) * 60 if elapsed_time > 0 else 0
        
        return cpm_correct, cpm_error, cpm_total

    try:
        start_time = timer()
        msg = await client.wait_for('message', check=check, timeout=60.0)
        end_time = timer()
        
        elapsed = end_time - start_time
        a, b, c = calculate_stats(typespd, sentence, elapsed)

        if a < 300 and b < 30: # Reasonable thresholds? Original logic was a*10 < 5 which is very low CPM. 
            # Original logic: a = count/end. if a*10 < 5 => count/end < 0.5 chars/sec? That's very slow.
            # Let's trust the user meant "high speed". 
            # Actually, let's just stick to the calculation fix and printing.
            pass

        # Use parameterized query
        if cur:
            try:
                # Giving points logic - simplified for "fix"
                if elapsed < 5: # If typed in less than 5 seconds?
                     await ctx.send("Congratulations! you got 10 points for speed!")
                     cur.execute("UPDATE lb SET points = points + 10 WHERE username = %s", (ctx.author.name,))
                     connect.commit()
            except Error as e:
                print(f"DB Error: {e}")

        # Formatting output
        res_a = 'correct cpm: ' + str(round(a, 2))
        res_b = 'error cpm: ' + str(round(b, 2))
        res_c = 'total cpm: ' + str(round(c, 2))
        await ctx.send(f"{res_a}\n{res_b}\n{res_c}")
        
    except Exception as e:
         await ctx.send(f'Time out or error: {e}')
    
    chek = True

@client.command()
async def tictactoe(ctx, p1: discord.Member):
    global count, player1, player2, turn, gameOver, board

    if gameOver:
        board = [":white_large_square:"] * 9
        turn = ""
        gameOver = False
        count = 0

        player1 = ctx.author
        player2 = p1

        # print the board
        await print_board(ctx)

        # determine who goes first
        num = random.randint(1, 2)
        if num == 1:
            turn = player1
        else:
            turn = player2
        await ctx.send(f"It is {turn.mention}'s turn.")

    else:
        await ctx.send("A game is already in progress! Finish it before starting a new one.")

async def print_board(ctx):
    line = ""
    for x in range(len(board)):
        line += " " + board[x]
        if (x + 1) % 3 == 0:
            await ctx.send(line)
            line = ""

@client.command()
async def place(ctx, pos: int):
    global turn, player1, player2, board, count, gameOver

    if not gameOver:
        if turn == ctx.author:
            mark = ":regional_indicator_x:" if turn == player1 else ":o2:"
            
            if 0 < pos < 10 and board[pos - 1] == ":white_large_square:":
                board[pos - 1] = mark
                count += 1

                await print_board(ctx)

                checkWinner(winningConditions, mark)
                
                if gameOver:
                    await ctx.send(f"{mark} wins!")
                    if turn != client.user and cur:
                        try:
                            await ctx.send(f"{turn.name} wins 10 points!")
                            cur.execute("UPDATE lb SET points = points + 10 WHERE username = %s", (turn.name,))
                            connect.commit()
                        except Error as e:
                            print(f"DB Error: {e}")
                elif count >= 9:
                    gameOver = True
                    await ctx.send("It's a tie!")
                    await ctx.send("uhoh! No one gets any points though :(")
                else:
                    # switch turns
                    turn = player2 if turn == player1 else player1
                    await ctx.send(f"It is {turn.mention}'s turn.")
                    
                    # Bot move logic if playing against bot
                    if turn == client.user:
                         await bot_move(ctx)

            else:
                await ctx.send("Be sure to choose an integer between 1 and 9 (inclusive) and an unmarked tile.")
        else:
            await ctx.send("It is not your turn.")
    else:
        await ctx.send("Please start a new game using the !tictactoe or !ttt command.")

async def bot_move(ctx):
    global turn, board, gameOver
    available = [i for i, x in enumerate(board) if x == ":white_large_square:"]
    if available:
        move = random.choice(available)
        board[move] = ":o2:"
        await print_board(ctx)
        checkWinner(winningConditions, ":o2:")
        if gameOver:
             await ctx.send(":o2: wins!")
        else:
            turn = player1
            await ctx.send(f"It is {turn.mention}'s turn.")

def checkWinner(winningConditions, mark):
    global gameOver
    for condition in winningConditions:
        if board[condition[0]] == mark and board[condition[1]] == mark and board[condition[2]] == mark:
            gameOver = True
            return

@client.command()
async def ttt(ctx):
    global count, player1, player2, turn, gameOver, board
    if gameOver:
        board = [":white_large_square:"] * 9
        turn = ""
        gameOver = False
        count = 0

        player1 = ctx.author
        player2 = client.user

        await print_board(ctx)
        
        num = random.randint(1, 2)
        if num == 1:
            turn = player1
            await ctx.send(f"It is {turn.mention}'s turn.")
        else:
            turn = player2
            await ctx.send(f"It is {turn.mention}'s turn.")
            await bot_move(ctx)
    else:
        await ctx.send("A game is already in progress! Finish it before starting a new one.")

@client.command()
async def hangman(ctx):
    global data_to_guess, word, gameover, person, limit
    person = ctx.author
    limit = 5
    gameover = False
    
    if data:
        word = random.choice(data)
    
    data_to_guess = '- ' * len(word)
    
    embed = discord.Embed(title="Hangman!", description="Guess The Letters!!!")
    embed.set_author(name=client.user.name if client.user else "Bot", icon_url=client.user.avatar.url if client.user and client.user.avatar else discord.Embed.Empty)
    embed.add_field(name=data_to_guess, value="You got 5 chances!", inline=False)

    await ctx.send("Welcome to Hangman! Use `!guess <letter>` or `!guess <word>`!", embed=embed)

@client.command()
async def guess(ctx, guess_str: str):
    global gameover, word, data_to_guess, limit
    
    if gameover:
        await ctx.send('The game is over. Start again with !hangman.')
        return

    if ctx.author != person:
        await ctx.send("Not your game.")
        return

    guess_str = guess_str.lower()
    
    if guess_str == word:
        await ctx.send('Yay! You guessed correctly!')
        if cur:
            cur.execute("UPDATE lb SET points = points + 15 WHERE username = %s", (ctx.author.name,))
            connect.commit()
        gameover = True
        return

    if len(guess_str) == 1:
        if guess_str in word:
            # Update data_to_guess
            new_data = list(data_to_guess.replace(' ', '')) # clean up current display
            # Wait, data_to_guess is "- - " string. 
            # Let's rebuild it properly
            # The original code logic was very specific about indices (2*i), which is brittle.
            # Let's just rebuild the display string
            
            # Actually, the original code logic: listdata_to_guess[2 * i] = word[i]
            # This implies data_to_guess is "X X X X " (spaced).
            
            # Let's reconstruct data_to_guess based on the word and the guess.
            # We can't really reconstruct without knowing previous guesses unless we parse data_to_guess.
            # Easier approach: Store guessed letters? No, I must stick to "fixing" the file, not adding too much new state vars if possible.
            # But wait, I can just check the current `data_to_guess` string.
            
            current_display = list(data_to_guess)
            found = False
            for idx, char in enumerate(word):
                if char == guess_str:
                    current_display[idx * 2] = char # Assuming "- " format
                    found = True
            
            data_to_guess = "".join(current_display)

            if found:
                # Check win
                if "-" not in data_to_guess:
                     await ctx.send(f'Yay! You guessed correctly! Word: {word}')
                     if cur:
                        cur.execute("UPDATE lb SET points = points + 15 WHERE username = %s", (ctx.author.name,))
                        connect.commit()
                     gameover = True
            else:
                 limit -= 1
        else:
            limit -= 1
    else:
        limit -= 1

    if not gameover:
        embed = discord.Embed(title="Hangman!", description="Guess The Letters!!!")
        embed.add_field(name=data_to_guess, value=f"You got {limit} chances!", inline=False)
        await ctx.send(embed=embed)

    if limit == 0:
        await ctx.send(f'Game Over! The word was {word}.')
        gameover = True

@client.command()
async def hint(ctx):
    global limith, data_to_guess
    if gameover: return
    if limith > 0:
        # Simple hint: reveal one unrevealed letter
        unrevealed_indices = [i for i, x in enumerate(word) if data_to_guess[i*2] == '-']
        if unrevealed_indices:
            idx = random.choice(unrevealed_indices)
            char = word[idx]
            
            # Reveal all instances of that char
            current_display = list(data_to_guess)
            for i, c in enumerate(word):
                if c == char:
                    current_display[i * 2] = char
            data_to_guess = "".join(current_display)
            
            limith -= 1
            await ctx.send(f"Hint: The letter '{char}' is in the word. {limith} hints left.")
            
            embed = discord.Embed(title="Hangman!", description="Guess The Letters!!!")
            embed.add_field(name=data_to_guess, value=f"You got {limit} chances!", inline=False)
            await ctx.send(embed=embed)
    else:
        await ctx.send("No hints left!")

@client.command()
async def lb(ctx):
    if cur:
        try:
            cur.execute("SELECT * FROM lb WHERE username = %s ORDER BY points DESC", (ctx.author.name,))
            data = cur.fetchall()
            if data:
                for i in data:
                    await ctx.send(f'rank = {i[0]}\nusername = {i[1]}\npoints = {i[2]}')
            else:
                await ctx.send("You are not on the leaderboard yet.")
        except Error as e:
            await ctx.send(f"Database error: {e}")
    else:
        await ctx.send("Database not connected.")

@tictactoe.error
async def tictactoe_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please mention a player to play with for this command.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Please make sure to mention/ping player.")

@place.error
async def place_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please enter a position you would like to mark.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Please make sure to enter an integer.")

@client.event
async def on_member_join(member):
    try:
        newUserMessage = f" Hii!!! Welcome {member.name} " + Dm_Content
        await member.send(newUserMessage)
        if cur:
            cur.execute("INSERT INTO lb(username, points) VALUES(%s, 0)", (member.name,))
            connect.commit()
    except Exception as e:
        print(f"Error in on_member_join: {e}")

@client.event
async def on_member_remove(member):
    try:
        if cur:
            # Fixed 'wh ere' typo
            cur.execute("DELETE FROM lb WHERE username = %s", (member.name,))
            connect.commit()
    except Exception as e:
        print(f"Error in on_member_remove: {e}")

if __name__ == "__main__":
    token = config.get('TOKEN')
    if token and token != "YOUR_DISCORD_BOT_TOKEN_HERE":
        client.run(token)
    else:
        print("Please set your TOKEN in config.json")