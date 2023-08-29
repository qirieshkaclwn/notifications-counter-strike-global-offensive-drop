from bs4 import BeautifulSoup
import requests
from unidecode import unidecode
import asyncio
import time
from steam import webauth as wa
import os, json
from steampy.guard import generate_one_time_code
from discord_webhook import DiscordWebhook, DiscordEmbed


discord_webhook_url = 'замените этот текст на ссылку на дискорд вебхук'
steamLoginSecure_list = []
item2 = {}
login_for_steam_login_secure = {}

async def parse_and_notify():
    global accaunts
    ABSmaFilePath = os.path.abspath('maFiles')
    accaunts = 0

    for maFileName in os.listdir(ABSmaFilePath):
        if maFileName != 'manifest.json':
            try:
                maFile = ABSmaFilePath + '\\' + maFileName
                file = open(maFile, encoding='utf-8')
                info = json.loads(file.read())
                file.close()

                maFileNameNew = ABSmaFilePath + '\\' + info["account_name"] + '.maFile'
                os.rename(maFile, maFileNameNew)
                print(f'{maFileName} успешно переименован в {info["account_name"]}.maFile!')
            except:
                print(f'\nОткрыть {maFileName} не удалось, возможно они зашифрованы в SDA.\n'
                      'Удалите пароль в SDA и попробуйте снова.\n')

    with open('logpass.txt', 'r') as file:
        lines = file.readlines()



    login_passwords = {}


    for line in lines:
        accaunts = int(accaunts) + 1
        line = line.strip()
        if ':' in line:
            login, password = line.split(':')
            login_passwords[login] = password


    for login, password in login_passwords.items():
        print(f'загрузился: {login}')
        file = open(f"maFiles/{login}.maFile", encoding='utf-8')
        info = json.loads(file.read())
        file.close()
        shared_secret = info["shared_secret"]
        a = generate_one_time_code(shared_secret)
        domain = 'store.steampowered.com'
        user = wa.WebAuth(username=login, password=password)
        s = user.login(twofactor_code=a)
        steamLoginSecure = s.cookies.get('steamLoginSecure', domain=domain)
        steamLoginSecure_list.append(steamLoginSecure)
        login_for_steam_login_secure[steamLoginSecure] = login
        time.sleep(30)

    global item2
    n = 1
    while True:
        for steamLoginSecure in steamLoginSecure_list:
            r = requests.get(url="https://steamcommunity.com/profiles/76561199001315036/inventoryhistory", headers={'User-Agent': "Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS 7.5; Trident/5.0; IEMobile/9.0)"},
                            cookies={'steamLoginSecure': steamLoginSecure}, timeout=50)

            try:
                soup = BeautifulSoup(r.text, "html.parser")
                print(f"Parsing data...логин: {login_for_steam_login_secure[steamLoginSecure]}")

                trade_history_rows = soup.find_all("div", class_="tradehistoryrow")

                current_data = []

                for row in trade_history_rows:
                    img_element = row.find("img", class_="tradehistory_received_item_img")
                    img_src = ""
                    if img_element and 'src' in img_element.attrs:
                        img_src = img_element['src']
                        img_src = img_src.replace("120x40", "256x198")

                    timestamp_element = row.find("div", class_="tradehistory_timestamp")
                    timestamp = timestamp_element.get_text(strip=True)
                    timestamp_element.decompose()

                    date = row.find("div", class_="tradehistory_date").get_text(strip=True)
                    date = date.replace(",", ".")

                    event_description = row.find("div", class_="tradehistory_event_description").get_text(strip=True)
                    event_description = unidecode(event_description)

                    items_plusminus_elem = row.find("div", class_="tradehistory_items_plusminus")
                    items_plusminus = items_plusminus_elem.get_text(strip=True) if items_plusminus_elem else ""

                    # ITEM NAME ENTRY
                    item_name = row.find("span", class_="history_item_name").get_text(strip=True)
                    item_name = unidecode(item_name)

                    if event_description == "Got an item drop":
                        item_info = (
                            login_for_steam_login_secure[steamLoginSecure],
                            item_name,
                            img_src
                        )
                        current_data.append(item_info)
                if list(set(current_data)) != []:
                    new_items = list(set(current_data) - set(item2.get(steamLoginSecure, [])))
                    item2[steamLoginSecure] = current_data.copy()

                    if n >= int(accaunts):
                        print(item2[steamLoginSecure])
                        items_to_notify = []

                        for item_info in new_items:
                            items_to_notify.append(item_info)
                            await send_discord_notification(items_to_notify)

                    else:
                        print(item2[steamLoginSecure])
                        n = n + 1
            except Exception as e:
                print(e)
            await asyncio.sleep(30)


async def send_discord_notification(item_data):
    webhook = DiscordWebhook(url=discord_webhook_url)

    for item_info in item_data:
        account, item_name, img_src = item_info

        market_item_name = item_name.replace(' ', '%20').replace('&', '%26')
        market_url = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=5&market_hash_name={market_item_name}"
        market_response = requests.get(market_url, headers={
            'User-Agent': "Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS 7.5; Trident/5.0; IEMobile/9.0)"}, timeout=50)
        market_data = market_response.json()
        item_price = market_data.get("lowest_price", "Не удалось получить цену")
        print(f"{market_item_name} - {item_price}")

        embed = DiscordEmbed(title="Уведомление о новом предмете",
                             description=f"аккаунт: {account}\nпредмет: {item_name}\nцена: {item_price}", color=242424)

        if img_src:
            embed.set_thumbnail(url=img_src)

        webhook.add_embed(embed)

    response = webhook.execute()
    print(f"Уведомление отправлено на Discord: {response}")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(parse_and_notify())
    loop.run_forever()