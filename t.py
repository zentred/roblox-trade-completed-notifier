import requests, threading, re, json, time, colorama
from colorama import init, Fore
init()

totalValues = None
lock = threading.Lock()

with open('config.json','r') as config:
    config = json.load(config)

bigProfitWebhook = config['bigProfitWebhook']
smallProfitWebhook = config['smallProfitWebhook']
lossWebhook = config['lossProfitWebhook']
discordid = config['discordId']
cookies = config['cookies']

def rolimons():
    global totalValues
    while True:
        items, data = [], []
        try:
            itemDetails = json.loads(
                re.findall('item_details = (.*?);', requests.get('https://www.rolimons.com/deals').text)[0]
            )
            for item in itemDetails:
                if itemDetails[item][5] == None:
                    items.append(item)
                    data.append(f'{itemDetails[item][2]}/{itemDetails[item][0]}/{itemDetails[item][4]}')
                elif itemDetails[item][5] != None:
                    items.append(item)
                    data.append(f'{itemDetails[item][5]}/{itemDetails[item][0]}/{itemDetails[item][4]}')
            totalValues = dict(zip(items, data))
            time.sleep(600)
        except:
            continue

threading.Thread(target=rolimons).start()
time.sleep(2)

class Player:
    def __init__(self, cookie):
        self.cookie = cookie
        self.alreadyChecked = []
        self.req = requests.Session()
        self.req.cookies['.ROBLOSECURITY'] = cookie

    def oldCompleteds(self):
        oldAccepts = self.req.get('https://trades.roblox.com/v1/trades/completed?cursor=&limit=25&sortOrder=Desc').json()
        oldAccepts = oldAccepts['data']
        self.alreadyChecked = [accept['id'] for accept in oldAccepts]
        with lock: print(f'{Fore.WHITE}[{Fore.MAGENTA}Collection{Fore.WHITE}] {Fore.MAGENTA}Trades were collected')

    def newCompleteds(self):
        while True:
            toSend = []
            try:
                newAccepts = self.req.get('https://trades.roblox.com/v1/trades/completed?cursor=&limit=25&sortOrder=Desc').json()
                if 'data' in newAccepts:
                    for item in newAccepts['data']:
                        if not item['id'] in self.alreadyChecked:
                            toSend.append(item['id'])
                    if len(toSend) > 0:
                        self.checkValuation(toSend)
                    else:
                        with lock: print(f'{Fore.WHITE}[{Fore.MAGENTA}Checked{Fore.WHITE}] {Fore.MAGENTA}No new completeds found')
                    break
            except Exception as err:
                with lock: print(err)
                continue

    def checkValuation(self, toSend):
        for tradeId in toSend:
            try:
                r = self.req.get(f'https://trades.roblox.com/v1/trades/{tradeId}').json()

                myValue, theirValue, myOffer,theirOffer = 0, 0, [f'\u200b\n**Robux**: {r["offers"][0]["robux"]}\n'], [f'\u200b\n**Robux**: {r["offers"][1]["robux"]}\n']

                for item in r['offers'][0]['userAssets']:
                    itemValue, itemName, itemProjection = totalValues[str(item['assetId'])].split('/',3)
                    myOffer.append(f'**Item**: {itemName}\n**Value**: {"{:,}".format(int(itemValue))}\n')
                    myValue += int(itemValue)

                for item in r['offers'][1]['userAssets']:
                    itemValue, itemName, itemProjection = totalValues[str(item['assetId'])].split('/',3)
                    theirOffer.append(f'**Item**: {itemName}\n**Value**: {"{:,}".format(int(itemValue))}\n')
                    theirValue += int(itemValue)

                myOffer, theirOffer = '\n'.join(myOffer), '\n'.join(theirOffer)
                profitAmount, profitPercentage = int(theirValue) - int(myValue), (1 - int(myValue) / int(theirValue)) * 100

                if '.' in str(profitPercentage):
                    if len(str(profitPercentage).split('.')[1]) >= 3:
                        profitPercentage = round(profitPercentage, 2)

                theirUsername = r['offers'][1]['user']['name']
                theirUserId = r['offers'][1]['user']['id']
                myUsername = r['offers'][0]['user']['name']
                myUserId = r['offers'][0]['user']['id']

                data = {
                    'content': f'<@{discordid}>',
                    'embeds':[{
                        'author': {
                            'name': f'Trade accepted by {theirUsername}\n\u200b',
                            'url': f'https://www.roblox.com/users/{str(theirUserId)}/profile'
                            },
                        'color': int('00FF00',16),
                        'fields': [
                            {'name': f'📤 Gave [{myValue}]','value': f'{myOffer}','inline':True},
                            {'name': f'\u200b','value': f'\u200b','inline':True},
                            {'name': f'📥 Received: [{theirValue}]','value': f'{theirOffer}','inline':True},
                            {'name': '💸 Profit','value': f'{profitAmount} ({profitPercentage}%)','inline':False},
                                ],
                            'thumbnail': {
                                'url': f'http://www.roblox.com/Thumbs/Avatar.ashx?x=200&y=200&Format=Png&username={theirUsername}',
                            },
                            'footer': {
                                'text': f'Account: {myUsername}'
                            }
                        }]
                    }
                if int(profitAmount) < 1000 and int(profitAmount) > 0:
                    requests.post(smallProfitWebhook, json=data)
                    with lock: print(f'{Fore.WHITE}[{Fore.GREEN}Found{Fore.WHITE}] {Fore.GREEN}New completed trade was found for {myUsername}')
                elif int(profitAmount) > 1000:
                    requests.post(bigProfitWebhook, json=data)
                    with lock: print(f'{Fore.WHITE}[{Fore.GREEN}Found{Fore.WHITE}] {Fore.GREEN}New completed trade was found for {myUsername}')
                else:
                    requests.post(lossWebhook, json=data)
                    with lock: print(f'{Fore.WHITE}[{Fore.GREEN}Found{Fore.WHITE}] {Fore.GREEN}New completed trade was found for {myUsername}')
                self.alreadyChecked.append(tradeId)
            except Exception as err:
                pass

    def looping(self):
        self.oldCompleteds()
        while True:
            self.newCompleteds()
            time.sleep(300)


for cookie in cookies:
    c = Player(cookie)
    threading.Thread(target=c.looping).start()
