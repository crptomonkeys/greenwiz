import time
from bot import Bot


if __name__ == "__main__":
    bot = Bot()
    try:
        bot.run()
    except ConnectionResetError:
        print("Initially failed to connect. Retrying in five seconds.")
        time.sleep(5000)
        bot.run()
