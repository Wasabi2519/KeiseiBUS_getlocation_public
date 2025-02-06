import json
import os
import time
import discord
import asyncio
from discord.ext import tasks
from dotenv import load_dotenv

# .env ファイルの読み込み
load_dotenv()

# 設定
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # .env からトークンを取得
CHANNEL_NAME = "通知チャンネル"  # 送信したいチャンネル名
JSON_FILE_PATH = KeiseiBus\bus_location.json　 # 監視するJSONファイルのパス

# Discordクライアントの設定
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# 送信メッセージのフォーマット
MESSAGE_TEMPLATE = "{系統} のバスがもうそろそろ到着するよ！！"
TARGET_BUS_STOP = "あいうえお高校"  # 通過したときに通知
last_checked_time = 0  # 最後に確認したファイルの更新時刻（数値型）

async def check_json_and_send_message():
    global last_checked_time
    try:
        # ファイルの最終更新時刻を取得
        file_mod_time = os.path.getmtime(JSON_FILE_PATH)

        # ファイルが更新されていたら処理を実行
        if last_checked_time < file_mod_time:
            last_checked_time = file_mod_time  # 最新の更新時刻を記録

            with open(JSON_FILE_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)

            for bus in data.get("運行中のバス", []):
                if bus.get("バス停名") == TARGET_BUS_STOP:
                    message = MESSAGE_TEMPLATE.format(系統=bus["系統"])
                    await send_discord_message(message)
                    break  # 送信したらループを抜ける

    except Exception as e:
        print(f"エラーが発生しました: {e}")

@client.event
async def on_ready():
    print(f"Botがログインしました: {client.user}")
    # 監視タスクを開始
    check_json_loop.start()

@tasks.loop(seconds=1)  # 1秒ごとに実行
async def check_json_loop():
    await check_json_and_send_message()

async def send_discord_message(message):
    for guild in client.guilds:
        channel = discord.utils.get(guild.text_channels, name=CHANNEL_NAME)
        if channel:
            await channel.send(message)
            print(f"メッセージをチャンネル '{CHANNEL_NAME}' に送信しました。")
            return
    print(f"チャンネル '{CHANNEL_NAME}' が見つかりませんでした。")

if __name__ == "__main__":
    if TOKEN is None:
        print("エラー: .env ファイルに DISCORD_BOT_TOKEN が設定されていません。")
        exit(1)
    
    client.run(TOKEN)
