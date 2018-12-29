import logging
import time
import traceback
import pandas as pd

from pymongo import MongoClient
import requests

from .xAPIConnector import *

logger = logging.getLogger()
logger.setLevel(logging.ERROR)

#connection to MongoDB
client = MongoClient('localhost')

db = client.Bot

FxData = db.FxData


HEADER ={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36'}

def get_info_about_trades():
    '''
    returns profitable trades and unprofitable
    '''
    return FxData.aggregate([{'$facet':{'loss':[{ '$match': { 'order': { '$exists': True }, 'profit' :{'$lt':12} }},{'$count': "No"}], 'profitable':[{ '$match': { 'order': { '$exists': True }, 'profit' :{'$gt':12} }},{'$count': "No"}], 'PL':[{ '$match': { 'order': { '$exists': True } }},{ '$group': { '_id' : None, 'sum' : { '$sum': "$profit" }}}]}}]).next()

def get_trades():
    '''
    returns trades
    '''
    return [item for item in FxData.aggregate([{ '$match': { 'order': { '$exists': True }}}])]

def get_3600(time):
    '''
    for opening time of trade will return price data from 3600 before to the time of trade
    '''
    return [element.get('Price') for element in FxData.aggregate([{'$match': { 'Time':{ '$gt': time - 3600, '$lt': time }}}])]


def exporting():
    '''
    save excel file filled with data about executed trades
    '''
    data = list(FxData.find({ 'order': { '$exists': True }},{'_id':0}))
    df =  pd.DataFrame(data)
    df.to_csv('eurusddata.csv', sep = ',')
    writer = pd.ExcelWriter('eurusddata.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Sheet1')
    writer.save()


    
def get_json():
    '''
    return list of orders info dictionaries
    '''
    return list(FxData.find({ 'order': { '$exists': True }},{'_id':0}))

class Trader():

    def __init__(self, userid= 11111, password='password', demo=True, setbet=0 , stop_loss = 0.0010, take_profit = 0.0065):
        server = 'xapia.x-station.eu'
        port = 5124
        streaming_port = 5125
        logging.basicConfig(level=logging.INFO, format = '%(asctime)s %(levelname)s %(message)s')
        self.logger = logging.getLogger(__name__)
        self.server = server
        self.port = port
        self.streaming_port = streaming_port
        if demo == False:
            self.port = 5112
            self.streaming_port = 5113
        self.userid = userid  
        self.password = password
        self.prices = []
        self.demo = demo
        self.setbet = setbet
        self.stop_loss = stop_loss
        self.take_profit = take_profit

    def get_day(self):
        '''
        returns  day as Mon, ... Sun, Fri ... UTC ZONE
        '''
        return time.strftime( "%a" , time.gmtime() )

    def get_hour(self):
        '''
        returnshour + minutes for 13 15 returns 1315 as integer UTC ZONE
        '''
        return int(time.strftime("%H%M", time.gmtime()))

    def get_price(self):
        '''
        returns price for EURUSD
        '''
        url = "http://webrates.truefx.com/rates/connect.html?f=html&c=EUR/USD"
        data  = requests.get(url, headers = HEADER).text.replace('<table>','').replace('<tr>','').replace('<td>','').replace('</td>','')
        return float( data [ data.index('.') - 1 : data.index('.') + 6 ] )

    def trade(self, value = 0, volume = 1, customComment = ''):
        '''
        opens trade if value = 0 buy if 1 sell, also returns response from XTB api
        '''
        apiClient = APIClient(address = self.server, port = self.port, encrypt = True)
        loginCmd = loginCommand(self.userid, self.password)
        # execute login command
        loginResponse = apiClient.execute(loginCmd)
        symbol = baseCommand('getSymbol',{"symbol": "EURUSD"})
        tick = apiClient.execute(symbol)
        # get price for opening trade
        price = tick['returnData']['ask']
        # set take profit and stop loss
        tp, sl = 0,0
        tp = tick['returnData']['bid']- self.take_profit if value == 1 else tick['returnData']['ask'] + self.take_profit
        sl = tick['returnData']['bid'] + self.stop_loss if value == 1 else tick['returnData']['ask'] - self.stop_loss
        trade = baseCommand('tradeTransaction',{"tradeTransInfo": {"cmd": value,"customComment": customComment,"expiration": 0,"order": 0,"price": price,"sl": sl,"tp": tp,"symbol": "EURUSD","type": 0,"volume": volume}})
        tradeResponse = apiClient.execute(trade)
        del self.prices[:]
        apiClient.disconnect()
        return tradeResponse

    def buy(self, volume = 1, customComment = ''):
        '''
        opens trade if value = 0 buy if 1 sell, also returns response from XTB api
        '''
        apiClient = APIClient(address = self.server, port = self.port, encrypt = True)
        loginCmd = loginCommand(self.userid, self.password)
        # execute login command
        loginResponse = apiClient.execute(loginCmd)
        symbol = baseCommand('getSymbol',{"symbol": "EURUSD"})
        tick = apiClient.execute(symbol)
        # get price for opening trade
        price = tick['returnData']['ask']
        # set take profit and stop loss
        trade = baseCommand('tradeTransaction',{"tradeTransInfo": {"cmd": 0,"customComment": customComment,"expiration": 0,"order": 0,"price": price,"sl": price - self.stop_loss,
                                                                   "tp": price + self.take_profit,"symbol": "EURUSD","type": 0,"volume": volume}})
        tradeResponse = apiClient.execute(trade)
        del self.prices[:]
        apiClient.disconnect()
        return tradeResponse

    def sell(self, volume = 1, customComment = ''):
        '''
        opens trade if value = 0 buy if 1 sell, also returns response from XTB api
        '''
        apiClient = APIClient(address = self.server, port = self.port, encrypt = True)
        loginCmd = loginCommand(self.userid, self.password)
        # execute login command
        loginResponse = apiClient.execute(loginCmd)
        symbol = baseCommand('getSymbol',{"symbol": "EURUSD"})
        tick = apiClient.execute(symbol)
        # get price for opening trade
        price = tick['returnData']['bid']
        # set take profit and stop loss
        trade = baseCommand('tradeTransaction',{"tradeTransInfo": {"cmd": 1,"customComment": customComment,"expiration": 0,"order": 0,"price": price,"sl": price + self.stop_loss,
                                                                   "tp": price - self.take_profit,"symbol": "EURUSD","type": 0,"volume": volume}})
        tradeResponse = apiClient.execute(trade)
        del self.prices[:]
        apiClient.disconnect()
        return tradeResponse

    def delete_trades(self, residue=0):
        '''
        returns opened trades also you can set up that numbers of last trades which will stay
        '''
        apiClient = APIClient(address=self.server, port=self.port, encrypt=True)
        loginCmd = loginCommand(self.userid, self.password)
        # execute login command
        loginResponse = apiClient.execute(loginCmd)
        openTrades = apiClient.execute(baseCommand('getTrades',{"openedOnly": True}))['returnData']
        if openTrades:
            for i in range(len(openTrades)-1,residue - 1,-1):
                trade = baseCommand('tradeTransaction',{"tradeTransInfo": {"cmd": list_open[i]['cmd'],"customComment": openTrades[i]["customComment"],"expiration":0,"order": openTrades[i]['order'],"price": openTrades[i]['close_price'],"sl": openTrades[i]['sl'],"tp": openTrades[i]['tp'],"symbol": "EURUSD","type": 2,"volume": openTrades[i]['volume']}})
                traderesponse = apiClient.execute(trade)
        apiClient.disconnect()

    def get_trades(self):
        '''
        returns historical trades
        '''
        apiClient = APIClient(address=self.server, port=self.port, encrypt=True)
        loginCmd = loginCommand(self.userid, self.password)
        # execute login command
        loginResponse = apiClient.execute(loginCmd)
        trades = apiClient.execute(baseCommand('getTradesHistory',{"end": 0,"start":0}))
        return trades

    def update_info_trades(self):
        '''
        add info about orders to mongodb by using customComment
        '''
        trades = self.get_trades()['returnData']
        for item in trades:
            try:
                Time = int(item['customComment'])
                result = {}
                for element in ['order','cmd','profit','close_time']:
                    result[element] = item[element]
                FxData.update({'Time':Time},{'$set':result})
            except:
                logger.error('Order not found ...')

    def set_bet(self):
        '''
        returns volume which will be used to open trade
        '''
        apiClient = APIClient(address=self.server, port=self.port, encrypt=True)
        loginCmd = loginCommand(self.userid, self.password)
        # execute login command
        loginResponse = apiClient.execute(loginCmd)
        balanceResponse = apiClient.execute(baseCommand('getMarginLevel',dict()))
        balance = balanceResponse["returnData"]['balance']
        volume = balance//1000
        volume = 1 if volume == 0 else volume
        volume = round(volume*0.01,2)
        volume = 50 if volume > 50 else volume
        apiClient.disconnect()
        return volume

    def check(self):
        '''
        checks data if there is a signal
        '''
        if len(self.prices) > 3600:
            delta = self.prices[-1]-self.prices[-1200]
            '''
            here will be good to implement control by linear regression
            hmm it will be interesting if it is really possible to get 40 percent of profitable trades
            '''
            response = {1:'buy',-2:'sell'}
            result = response.get(delta//0.0010)
            if result:
                return result
            else:
                return None

    def scan_fx(self):
        '''
        scans every second if there is signal to trade
        '''
        while True:
            hourmin = self.get_hour()
            day =  self.get_day()
            if day == 'Fri' and 1944 < hourmin <2000:
                self.update_info_trades()
                time.sleep(172750)
            try:
                price = self.get_price()
                self.prices.append(price)
                response = self.check()
                result = {}
                result['Time'] = int(time.time())
                result['Price'] = price
                if response:
                    logger.error(response)
                    bet = self.set_bet()
                    if response == 'buy':
                        tradeResponse = self.buy(volume = bet, customComment =  str(result['Time']))
                    if response == 'sell':
                        tradeResponse = self.sell(volume = bet, customComment =  str(result['Time']))
                    if tradeResponse['status']:
                        result['Order'] = tradeResponse['returnData']['order']
                        self.logger.error(result)
                FxData.insert(result)
                self.logger.error('One loop done')
                time.sleep(0.8)
                if len(self.prices)>7200:
                    del self.prices[:3600]
            except Exception as e:
                self.logger.error('Error : {} Traceback : {}'.format(e, traceback.print_exc()))
                time.sleep(0.75)
                
def run():
    #change to your account, if real account add demo = False
    tr = Trader(userid = 11111111, password = 'blablabla')
    tr.scan_fx()

if __name__ == "__main__":
    tr = Trader(userid = 11111111)
    tr.scan_fx()
