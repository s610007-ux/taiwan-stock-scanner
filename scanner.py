"""
台股掃描器 - 雙策略版
策略一：UT Bot Alerts 買入訊號 + Squeeze Momentum 今日 > 昨日
策略二：當日漲幅 ≥ 8% + Squeeze Momentum 反轉向上（今>昨>前天反轉）且數值為正

每天收盤後執行，結果存為 results.json，供 dashboard.html 顯示
"""

import json
import time
from datetime import datetime, date
import warnings
warnings.filterwarnings("ignore")

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("正在安裝必要套件...")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "yfinance", "pandas", "numpy", "requests"])
    import yfinance as yf
    import pandas as pd
    import numpy as np
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ──────────────────────────────────────────────
# 參數設定
# ──────────────────────────────────────────────
UT_BOT_ATR_PERIOD  = 10      # UT Bot ATR 週期
UT_BOT_SENSITIVITY = 1       # UT Bot 靈敏度（Key Value）
SQUEEZE_LENGTH     = 20      # Squeeze Momentum 週期
SQUEEZE_MULT_BB    = 2.0     # Squeeze BB 乘數
SQUEEZE_MULT_KC    = 1.5     # Squeeze KC 乘數
SURGE_THRESHOLD    = 0.08    # 策略二漲幅門檻（8%）
FETCH_PERIOD       = "200d"  # 抓取資料長度
MAX_STOCKS         = 500     # 取成交量前 N 名
DELAY_BETWEEN      = 0.3     # 每檔之間延遲秒數

# ──────────────────────────────────────────────
# 內建台股代碼清單（備援用）
# ──────────────────────────────────────────────
BUILTIN_CODES = [
    "1101","1102","1103","1104","1108","1109","1110","1201","1203","1210",
    "1213","1215","1216","1217","1218","1219","1220","1225","1227","1229",
    "1231","1232","1233","1234","1235","1236","1256","1262","1264","1268",
    "1269","1271","1274","1275","1277","1301","1303","1304","1305","1307",
    "1308","1309","1310","1312","1313","1314","1315","1316","1319","1321",
    "1323","1324","1325","1326","1327","1328","1329","1330","1337","1338",
    "1339","1340","1341","1342","1402","1403","1404","1405","1406","1407",
    "1409","1410","1413","1414","1415","1416","1417","1418","1419","1423",
    "1424","1425","1426","1427","1428","1429","1430","1431","1432","1433",
    "1434","1435","1436","1437","1438","1439","1440","1441","1442","1443",
    "1444","1445","1446","1447","1448","1449","1451","1452","1453","1454",
    "1455","1456","1457","1459","1460","1461","1462","1463","1464","1465",
    "1466","1467","1468","1469","1470","1471","1472","1473","1474","1475",
    "1476","1477","1503","1504","1506","1507","1512","1513","1514","1515",
    "1516","1517","1519","1521","1522","1524","1525","1526","1527","1528",
    "1529","1530","1531","1532","1533","1535","1536","1537","1538","1539",
    "1540","1541","1542","1543","1544","1545","1546","1547","1548","1549",
    "1550","1551","1552","1553","1554","1555","1556","1558","1560","1561",
    "1562","1563","1564","1565","1566","1568","1569","1570","1571","1573",
    "1574","1575","1576","1577","1578","1579","1580","1581","1582","1583",
    "1584","1585","1586","1587","1590","1591","1592","1593","1594","1595",
    "1597","1598","1599","1600","1601","1603","1604","1605","1608","1609",
    "1611","1612","1613","1614","1615","1616","1617","1618","1619","1621",
    "2002","2003","2006","2007","2008","2009","2010","2011","2012","2013",
    "2014","2015","2016","2017","2018","2019","2020","2021","2022","2023",
    "2024","2025","2026","2027","2028","2029","2030","2031","2032","2033",
    "2034","2035","2036","2038","2039","2049","2050","2059","2062","2065",
    "2066","2067","2068","2069","2101","2102","2103","2104","2105","2106",
    "2107","2108","2109","2110","2111","2114","2115","2116","2117","2118",
    "2119","2120","2121","2122","2123","2124","2125","2126","2127","2128",
    "2201","2204","2205","2206","2207","2208","2209","2211","2212","2213",
    "2214","2215","2216","2217","2219","2221","2227","2228","2230","2231",
    "2232","2233","2235","2236","2237","2238","2239","2240","2241","2243",
    "2244","2301","2302","2303","2305","2306","2308","2309","2312","2313",
    "2314","2315","2316","2317","2318","2319","2320","2321","2323","2324",
    "2325","2326","2327","2328","2329","2330","2331","2332","2334","2335",
    "2336","2337","2338","2340","2341","2342","2344","2345","2347","2348",
    "2349","2350","2351","2352","2353","2354","2355","2356","2357","2358",
    "2359","2360","2362","2363","2364","2365","2366","2367","2368","2369",
    "2371","2372","2373","2374","2375","2376","2377","2379","2380","2381",
    "2382","2383","2384","2385","2386","2387","2388","2389","2390","2392",
    "2393","2394","2395","2396","2397","2399","2401","2402","2404","2405",
    "2406","2408","2409","2410","2412","2413","2414","2415","2416","2417",
    "2419","2420","2421","2422","2423","2424","2425","2426","2427","2428",
    "2429","2430","2431","2432","2433","2434","2435","2436","2437","2438",
    "2439","2440","2441","2442","2443","2444","2448","2449","2450","2451",
    "2452","2453","2454","2455","2456","2457","2458","2459","2460","2461",
    "2462","2463","2464","2465","2466","2467","2468","2469","2470","2471",
    "2472","2474","2475","2476","2477","2478","2480","2481","2482","2483",
    "2484","2485","2486","2488","2489","2491","2492","2493","2494","2495",
    "2496","2497","2498","2499","2501","2504","2505","2506","2507","2511",
    "2515","2516","2520","2521","2524","2527","2528","2530","2531","2532",
    "2534","2535","2536","2537","2538","2539","2540","2542","2543","2545",
    "2546","2547","2548","2549","2550","2551","2552","2553","2601","2603",
    "2605","2606","2607","2608","2609","2610","2612","2613","2614","2615",
    "2616","2617","2618","2630","2633","2634","2636","2637","2641","2642",
    "2645","2701","2702","2703","2704","2705","2706","2707","2708","2712",
    "2714","2715","2718","2719","2722","2723","2724","2726","2727","2729",
    "2731","2732","2736","2739","2740","2743","2745","2748","2749","2752",
    "2753","2754","2755","2761","2762","2763","2764","2801","2809","2812",
    "2820","2823","2832","2834","2836","2838","2839","2840","2841","2842",
    "2845","2847","2849","2850","2851","2855","2856","2867","2868","2876",
    "2880","2881","2882","2883","2884","2885","2886","2887","2888","2889",
    "2890","2891","2892","2897","2903","2904","2905","2906","2907","2908",
    "2910","2911","2912","2913","2915","2917","2918","2919","2920","2921",
    "3008","3010","3012","3014","3015","3016","3017","3018","3019","3020",
    "3021","3022","3023","3024","3025","3026","3027","3028","3029","3030",
    "3031","3032","3033","3034","3035","3036","3037","3038","3039","3040",
    "3041","3042","3044","3045","3046","3047","3048","3049","3050","3051",
    "3052","3053","3054","3055","3056","3057","3058","3059","3060","3062",
    "3064","3065","3066","3068","3069","3070","3071","3072","3073","3074",
    "3075","3076","3077","3078","3079","3080","3081","3082","3083","3084",
    "3085","3086","3087","3088","3089","3090","3091","3092","3093","3094",
    "3095","3096","3097","3098","3099","3100","3101","3102","3103","3105",
    "3106","3108","3109","3110","3111","3112","3113","3114","3115","3116",
    "3117","3118","3119","3120","3121","3122","3123","3124","3125","3126",
    "3127","3128","3129","3130","3131","3132","3402","3406","3407","3408",
    "3702","3703","3704","3706","3707","3708","3709","3711","3712","3714",
    "3715","3716","3717","3718","3719","3720","3721","3722","3723","3724",
    "3725","3726","3727","3728","3729","3730","3731","3732","3733","3735",
    "3736","3737","3738","3741","3742","3743","3744","3745","3746","3747",
    "4102","4104","4105","4106","4107","4108","4109","4110","4111","4112",
    "4113","4114","4115","4116","4117","4118","4119","4120","4121","4122",
    "4123","4124","4125","4126","4127","4128","4129","4130","4131","4132",
    "4133","4134","4135","4136","4137","4138","4139","4140","4141","4142",
    "4143","4144","4145","4146","4147","4148","4149","4150","4151","4152",
    "4153","4154","4155","4156","4157","4158","4159","4160","4161","4162",
    "4163","4164","4165","4166","4167","4168","4169","4170","4171","4172",
    "4173","4174","4175","4176","4177","4178","4179","4180","4181","4182",
    "4904","4906","4907","4908","4909","4910","4911","4912","4914","4915",
    "4916","4917","4918","4919","4920","4921","4922","4923","4924","4925",
    "4926","4927","4928","4929","4930","4931","4932","4933","4934","4935",
    "4936","4937","4938","4939","4940","4941","4942","4943","4944","4945",
    "4946","4947","4948","4949","4950","4951","4952","4953","4954","4955",
    "4956","4957","4958","4959","4960","4961","4962","4963","4964","4965",
    "4966","4967","4968","4969","4970","4971","4972","4973","4974","4975",
    "5007","5009","5011","5014","5015","5016","5017","5018","5019","5020",
    "5534","5536","5538","5539","5540","5541","5543","5546","5547","5548",
    "5550","5551","5552","5553","5554","5555","5556","5557","5559","5560",
    "5562","5563","5564","5565","5567","5568","5569","5570","5571","5572",
    "5871","5876","5878","5879","5880","5881","5882","5883","5884","5885",
    "5886","5887","5888","5889","5890","5891","5892","5893","5894","5895",
    "6005","6006","6007","6008","6009","6010","6011","6012","6013","6014",
    "6015","6016","6017","6018","6019","6020","6021","6022","6023","6024",
    "6025","6026","6027","6028","6029","6030","6031","6032","6033","6034",
    "6035","6036","6037","6038","6039","6040","6041","6042","6043","6044",
    "6045","6046","6047","6048","6049","6050","6051","6052","6053","6054",
    "6055","6056","6057","6058","6059","6060","6061","6062","6063","6064",
    "6065","6066","6067","6068","6069","6070","6071","6072","6073","6074",
    "6075","6076","6077","6078","6079","6080","6081","6082","6083","6084",
    "6085","6086","6087","6088","6089","6090","6091","6092","6093","6094",
    "6095","6096","6097","6098","6099","6100","6101","6102","6103","6104",
    "6105","6106","6107","6108","6109","6110","6111","6112","6113","6114",
    "6115","6116","6117","6118","6119","6120","6121","6122","6123","6124",
    "6125","6126","6127","6128","6129","6130","6131","6132","6133","6134",
    "6135","6136","6137","6138","6139","6140","6141","6142","6143","6144",
    "6145","6146","6147","6148","6149","6150","6151","6152","6153","6154",
    "6155","6156","6157","6158","6159","6160","6161","6162","6163","6164",
    "6165","6166","6167","6168","6169","6170","6171","6172","6173","6174",
    "6175","6176","6177","6178","6179","6180","6181","6182","6183","6184",
    "6185","6186","6187","6188","6189","6190","6191","6192","6193","6194",
    "6195","6196","6197","6198","6199","6200","6201","6202","6203","6204",
    "6205","6206","6207","6208","6209","6210","6211","6212","6213","6214",
    "6215","6216","6217","6218","6219","6220","6221","6222","6223","6224",
    "6225","6226","6227","6228","6229","6230","6231","6232","6233","6234",
    "6235","6236","6237","6238","6239","6240","6241","6242","6243","6244",
    "6245","6246","6247","6248","6249","6250","6251","6252","6253","6254",
    "6255","6256","6257","6258","6259","6260","6261","6262","6263","6264",
    "6265","6266","6267","6268","6269","6270","6271","6272","6273","6274",
    "6275","6276","6277","6278","6279","6280","6281","6282","6283","6284",
    "6285","6286","6287","6288","6289","6290","6291","6292","6293","6294",
    "6295","6296","6297","6298","6299","6300","6301","6302","6303","6304",
    "6305","6306","6307","6308","6309","6310","6311","6312","6313","6314",
    "6315","6316","6317","6318","6319","6320","6321","6322","6323","6324",
    "6325","6326","6327","6328","6329","6330","6331","6332","6333","6334",
    "6335","6336","6337","6338","6339","6340","6341","6342","6343","6344",
    "6345","6346","6347","6348","6349","6350","6351","6352","6353","6354",
    "6355","6356","6357","6358","6359","6360","6361","6362","6363","6364",
    "6365","6366","6367","6368","6369","6370","6371","6372","6373","6374",
    "6375","6376","6377","6378","6379","6380","6381","6382","6383","6384",
    "6385","6386","6387","6388","6389","6390","6391","6392","6393","6394",
    "6395","6396","6397","6398","6399","6401","6402","6403","6404","6405",
    "6406","6407","6408","6409","6410","6411","6412","6413","6414","6415",
    "6416","6417","6418","6419","6420","6421","6422","6423","6424","6425",
    "6426","6427","6428","6429","6430","6431","6432","6433","6434","6435",
    "6436","6437","6438","6439","6440","6441","6442","6443","6444","6445",
    "6446","6447","6448","6449","6450","6451","6452","6453","6454","6455",
    "6456","6457","6458","6459","6460","6461","6462","6463","6464","6465",
    "6466","6467","6468","6469","6470","6471","6472","6473","6474","6475",
    "6476","6477","6478","6479","6480","6481","6482","6483","6484","6485",
    "6486","6487","6488","6489","6490","6491","6492","6493","6494","6495",
    "6496","6497","6498","6499","6500","6501","6502","6503","6504","6505",
    "6506","6507","6508","6509","6510","6511","6512","6513","6514","6515",
    "6516","6517","6518","6519","6520","6521","6522","6523","6524","6525",
    "6526","6527","6528","6529","6530","6531","6532","6533","6534","6535",
    "6536","6537","6538","6539","6540","6541","6542","6543","6544","6545",
    "6546","6547","6548","6549","6550","6551","6552","6553","6554","6555",
    "6556","6557","6558","6559","6560","6561","6562","6563","6564","6565",
    "6566","6567","6568","6569","6570","6571","6572","6573","6574","6575",
    "8001","8002","8003","8004","8005","8006","8007","8008","8009","8010",
    "8011","8012","8013","8014","8015","8016","8017","8018","8019","8020",
    "8021","8022","8023","8024","8025","8026","8027","8028","8029","8030",
    "8031","8032","8033","8034","8035","8036","8037","8038","8039","8040",
    "8041","8042","8043","8044","8045","8046","8047","8048","8049","8050",
    "8051","8052","8053","8054","8055","8056","8057","8058","8059","8060",
    "8061","8062","8063","8064","8065","8066","8067","8068","8069","8070",
    "8071","8072","8073","8074","8075","8076","8077","8078","8079","8080",
    "8081","8082","8083","8084","8085","8086","8087","8088","8089","8090",
    "8091","8092","8093","8094","8095","8096","8097","8098","8099","8100",
    "9101","9103","9104","9105","9106","9107","9108","9109","9110","9111",
    "9112","9113","9114","9115","9116","9117","9118","9119","9120","9121",
    "9125","9126","9127","9128","9129","9130","9131","9132","9133","9134",
    "9910","9911","9912","9913","9914","9915","9916","9917","9918","9919",
    "9920","9921","9922","9923","9924","9925","9926","9927","9928","9929",
    "9930","9931","9932","9933","9934","9935","9936","9937","9938","9939",
    "9940","9941","9942","9943","9944","9945","9946","9947","9948","9949",
    "9950","9951","9952","9953","9954","9955","9956","9957","9958","9959",
]


# ──────────────────────────────────────────────
# 抓取股票清單（上市 + 上櫃合併，即時成交量排行）
# ──────────────────────────────────────────────
def fetch_twse():
    """抓取上市個股清單（含昨日成交量，用來確認股票存在）"""
    url  = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    resp = requests.get(url, timeout=20, verify=False)
    resp.raise_for_status()
    data = resp.json()
    tickers = []
    for item in data:
        code = item.get("Code", "")
        name = item.get("Name", "")
        if not (code.isdigit() and len(code) == 4):
            continue
        vol_str = item.get("TradeVolume", "0").replace(",", "")
        try:    volume = int(vol_str)
        except: volume = 0
        tickers.append({"code": code, "name": name, "volume": volume, "market": "上市"})
    return tickers

def fetch_tpex():
    """抓取上櫃個股清單（含昨日成交量，用來確認股票存在）"""
    url  = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"
    resp = requests.get(url, timeout=20, verify=False)
    resp.raise_for_status()
    data = resp.json()
    tickers = []
    for item in data:
        code = item.get("SecuritiesCompanyCode", "")
        name = item.get("CompanyName", "")
        if not (code.isdigit() and len(code) == 4):
            continue
        vol_str = item.get("TradingShares", "0").replace(",", "")
        try:    volume = int(vol_str)
        except: volume = 0
        tickers.append({"code": code, "name": name, "volume": volume, "market": "上櫃"})
    return tickers

def get_realtime_volume_twse(candidates):
    """
    方法一：用 TWSE 盤中即時 API 抓今日成交量
    速度最快，約5~10秒，官方資料
    """
    print(f"   ⚡ 嘗試 TWSE 盤中即時 API...")
    try:
        # 建立上市股票對照表
        twse_map = {s["code"]: s for s in candidates if s["market"] == "上市"}
        tpex_map = {s["code"]: s for s in candidates if s["market"] == "上櫃"}

        updated = []

        # 上市：TWSE 盤中成交量排行
        url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=" + "|".join(
            [f"tse_{code}.tw" for code in list(twse_map.keys())[:500]]
        )
        resp = requests.get(url, timeout=15, verify=False,
                           headers={"User-Agent": "Mozilla/5.0",
                                    "Referer": "https://mis.twse.com.tw"})
        data = resp.json()
        for item in data.get("msgArray", []):
            code = item.get("c", "")
            vol_str = item.get("v", "0").replace(",", "")
            try:    volume = int(float(vol_str))
            except: volume = 0
            if code in twse_map:
                updated.append({**twse_map[code], "volume": volume})

        # 上櫃：OTC 盤中成交量
        url2 = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=" + "|".join(
            [f"otc_{code}.tw" for code in list(tpex_map.keys())[:500]]
        )
        resp2 = requests.get(url2, timeout=15, verify=False,
                            headers={"User-Agent": "Mozilla/5.0",
                                     "Referer": "https://mis.twse.com.tw"})
        data2 = resp2.json()
        for item in data2.get("msgArray", []):
            code = item.get("c", "")
            vol_str = item.get("v", "0").replace(",", "")
            try:    volume = int(float(vol_str))
            except: volume = 0
            if code in tpex_map:
                updated.append({**tpex_map[code], "volume": volume})

        if len(updated) > 100:
            updated.sort(key=lambda x: x["volume"], reverse=True)
            print(f"   ✅ TWSE 即時 API 成功！最高: {updated[0]['code']} {updated[0]['name']} ({updated[0]['volume']:,} 張)")
            return updated

    except Exception as e:
        print(f"   ⚠️  TWSE 即時 API 失敗: {e}")

    return None


def get_realtime_volume_yf(candidates):
    """
    方法二：yfinance 批次下載（備援）
    """
    print(f"   ⚡ 備援：yfinance 批次下載即時成交量...")
    code_map = {}
    all_symbols = []
    for s in candidates:
        suffix = "TWO" if s["market"] == "上櫃" else "TW"
        sym = f"{s['code']}.{suffix}"
        all_symbols.append(sym)
        code_map[sym] = s

    BATCH = 200
    vol_today = {}
    for i in range(0, len(all_symbols), BATCH):
        batch = all_symbols[i:i+BATCH]
        try:
            df = yf.download(batch, period="2d", interval="1d",
                             progress=False, auto_adjust=True, group_by="ticker")
            for sym in batch:
                try:
                    if len(batch) == 1:
                        v = int(df["Volume"].iloc[-1])
                    else:
                        v = int(df[sym]["Volume"].iloc[-1])
                    vol_today[sym] = v
                except Exception:
                    vol_today[sym] = code_map[sym]["volume"]
        except Exception as e:
            for sym in batch:
                vol_today[sym] = code_map[sym]["volume"]

    updated = []
    for sym, s in code_map.items():
        updated.append({**s, "volume": vol_today.get(sym, s["volume"])})
    updated.sort(key=lambda x: x["volume"], reverse=True)
    return updated


def get_realtime_volume(candidates):
    """先試 TWSE 即時 API，失敗才用 yfinance 備援"""
    result = get_realtime_volume_twse(candidates)
    if result:
        return result
    print(f"   ⚡ 改用 yfinance 備援...")
    return get_realtime_volume_yf(candidates)

def get_tw_stock_list():
    print(f"📋 正在抓取上市+上櫃即時成交量排行（前 {MAX_STOCKS} 名）...")
    all_tickers = []

    # 上市
    for attempt in range(2):
        try:
            tickers = fetch_twse()
            if len(tickers) > 100:
                all_tickers.extend(tickers)
                print(f"   ✅ 上市清單成功！共 {len(tickers)} 檔")
                break
        except Exception as e:
            if attempt == 0:
                print(f"   ⚠️  上市第1次失敗，重試... ({e})")
                time.sleep(2)
            else:
                print(f"   ⚠️  上市 API 失敗，略過")

    # 上櫃
    for attempt in range(2):
        try:
            tickers = fetch_tpex()
            if len(tickers) > 100:
                all_tickers.extend(tickers)
                print(f"   ✅ 上櫃清單成功！共 {len(tickers)} 檔")
                break
        except Exception as e:
            if attempt == 0:
                print(f"   ⚠️  上櫃第1次失敗，重試... ({e})")
                time.sleep(2)
            else:
                print(f"   ⚠️  上櫃 API 失敗，略過")

    if len(all_tickers) > 100:
        # 先用昨日成交量取前800名候選，再抓即時成交量重新排序
        all_tickers.sort(key=lambda x: x["volume"], reverse=True)
        candidates = all_tickers[:800]
        print(f"   📋 候選清單：昨日成交量前 {len(candidates)} 名")

        # 抓即時成交量重新排序
        updated = get_realtime_volume(candidates)
        top = updated[:MAX_STOCKS]
        print(f"   📊 即時成交量前 {len(top)} 名，最高: {top[0]['code']} {top[0]['name']} ({top[0]['volume']:,} 張)")
        return top

    # 備援
    seen, unique = set(), []
    for c in BUILTIN_CODES:
        if c not in seen:
            seen.add(c)
            unique.append({"code": c, "name": c, "volume": 0, "market": "上市"})
    top = unique[:MAX_STOCKS]
    print(f"   ℹ️  使用內建清單，共 {len(top)} 檔")
    return top


# ──────────────────────────────────────────────
# UT Bot Alerts（復刻 QuantNomad）
# ──────────────────────────────────────────────
def rma(series, period):
    """Wilder's Moving Average（RMA），與 TradingView Pine Script 的 ta.rma() 一致"""
    alpha = 1 / period
    result = np.zeros(len(series))
    result[:] = np.nan
    # 找第一個非 NaN 的位置
    values = series.values
    start = 0
    while start < len(values) and np.isnan(values[start]):
        start += 1
    if start >= len(values):
        return pd.Series(result, index=series.index)
    result[start] = values[start]
    for i in range(start + 1, len(values)):
        if np.isnan(values[i]):
            result[i] = result[i-1]
        else:
            result[i] = alpha * values[i] + (1 - alpha) * result[i-1]
    return pd.Series(result, index=series.index)

def compute_ut_bot(df, key_value=1, atr_period=1):
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    tr    = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    # 用 RMA（Wilder's MA）與 TradingView 一致
    atr    = rma(tr, atr_period)
    n_loss = key_value * atr
    src, nl = close.values, n_loss.values
    ts = np.zeros(len(src))
    ts[0] = src[0]
    for i in range(1, len(src)):
        prev = ts[i-1]
        if   src[i] > prev and src[i-1] > prev: ts[i] = max(prev, src[i] - nl[i])
        elif src[i] < prev and src[i-1] < prev: ts[i] = min(prev, src[i] + nl[i])
        elif src[i] > prev:                      ts[i] = src[i] - nl[i]
        else:                                    ts[i] = src[i] + nl[i]
    trailing_stop = pd.Series(ts, index=df.index)

    # 基本穿越訊號
    cross_up   = (close > trailing_stop) & (close.shift(1) <= trailing_stop.shift(1))
    cross_down = (close < trailing_stop) & (close.shift(1) >= trailing_stop.shift(1))

    # 加入交替邏輯：Buy 前面必須有 Sell，Sell 前面必須有 Buy
    # 用 position 追蹤：1=多頭（上穿後）, -1=空頭（下穿後）
    pos = np.zeros(len(close))
    for i in range(1, len(close)):
        if cross_up.iloc[i]:
            pos[i] = 1
        elif cross_down.iloc[i]:
            pos[i] = -1
        else:
            pos[i] = pos[i-1]

    position   = pd.Series(pos, index=df.index)
    prev_pos   = position.shift(1).fillna(0)

    # Buy：向上穿越 且 前一個狀態是空頭（-1）
    buy_signal = cross_up & (prev_pos <= 0)

    return buy_signal, trailing_stop


# ──────────────────────────────────────────────
# Squeeze Momentum（復刻 LazyBear）
# ──────────────────────────────────────────────
def linreg_value(series, length):
    """
    完全復刻 TradingView Pine Script 的 linreg(source, length, 0)
    取線性迴歸在最後一個點的預測值（不是斜率）
    """
    def _linreg(x):
        n = len(x)
        if n < length:
            return np.nan
        t = np.arange(n)
        # 線性迴歸：y = a*t + b，取 t=n-1 的預測值
        a, b = np.polyfit(t, x, 1)
        return a * (n - 1) + b
    return series.rolling(length).apply(_linreg, raw=True)

def compute_squeeze_momentum(df, length=20, mult_bb=2.0, mult_kc=1.5):
    """
    完全復刻 LazyBear Squeeze Momentum Indicator
    使用 linreg 預測值，與 TradingView 結果一致
    """
    close, high, low = df["Close"], df["High"], df["Low"]
    basis    = close.rolling(length).mean()
    dev      = close.rolling(length).std()
    tr       = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr_kc   = tr.rolling(length).mean()
    upper_kc = basis + mult_kc * atr_kc
    lower_kc = basis - mult_kc * atr_kc
    highest_high = high.rolling(length).max()
    lowest_low   = low.rolling(length).min()
    mid_hl       = (highest_high + lowest_low) / 2
    delta        = close - (mid_hl + basis) / 2
    # 用 linreg 預測值，與 TradingView 一致
    momentum = linreg_value(delta, length)
    return momentum


# ──────────────────────────────────────────────
# 分析單一股票，同時跑兩個策略
# ──────────────────────────────────────────────
def analyze_stock(code, name, market=''):
    try:
        suffix = "TWO" if market == "上櫃" else "TW"
        df = yf.download(f"{code}.{suffix}", period=FETCH_PERIOD, interval="1d",
                         progress=False, auto_adjust=False)
        if df is None or len(df) < 50:
            return None, None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        if len(df) < 50:
            return None, None

        close    = df["Close"]
        volume   = int(df["Volume"].iloc[-1]) if "Volume" in df.columns else 0
        price    = round(float(close.iloc[-1]), 2)
        date_str = str(df.index[-1].date())

        # 計算指標
        buy_signal, trailing_stop = compute_ut_bot(df, UT_BOT_SENSITIVITY, UT_BOT_ATR_PERIOD)
        momentum = compute_squeeze_momentum(df, SQUEEZE_LENGTH, SQUEEZE_MULT_BB, SQUEEZE_MULT_KC)

        # 去除 NaN 後再取最近三根，確保索引對應正確的交易日
        mom_clean = momentum.dropna()
        if len(mom_clean) < 3:
            return None, None
        mom_t0 = float(mom_clean.iloc[-1])  # 今日
        mom_t1 = float(mom_clean.iloc[-2])  # 昨日
        mom_t2 = float(mom_clean.iloc[-3])  # 前天

        result_s1 = None
        result_s2 = None

        # ── 策略一：UT Bot 買入 + Squeeze 今 > 昨 + 今日為負值 ──
        if (mom_t0 is not None and mom_t1 is not None
                and bool(buy_signal.iloc[-1])
                and mom_t0 > mom_t1
                and mom_t0 < 0):
            result_s1 = {
                "code":     code, "name": name,
                "price":    price, "volume": volume,
                "momentum": round(mom_t0, 4),
                "prev_mom": round(mom_t1, 4),
                "ts":       round(float(trailing_stop.iloc[-1]), 2),
                "date":     date_str,
                "market":   market,
                "strategy": 1,
            }

        # ── 策略二：漲幅 ≥ 8% + Squeeze 今 > 昨 + 今日昨日都是正值 ──
        if (mom_t0 is not None and mom_t1 is not None
                and mom_t0 > 0 and mom_t1 > 0          # 今、昨都是正值
                and mom_t0 > mom_t1):                   # 今 > 昨（上升）
            prev_close = float(close.iloc[-2])
            change_pct = (price - prev_close) / prev_close if prev_close > 0 else 0
            if change_pct >= SURGE_THRESHOLD:
                result_s2 = {
                    "code":       code, "name": name,
                    "price":      price, "volume": volume,
                    "momentum":   round(mom_t0, 4),
                    "prev_mom":   round(mom_t1, 4),
                    "prev2_mom":  round(mom_t2, 4),
                    "change_pct": round(change_pct * 100, 2),
                    "ts":         round(float(trailing_stop.iloc[-1]), 2),
                    "date":       date_str,
                    "strategy":   2,
                }

        return result_s1, result_s2

    except Exception:
        return None, None


# ──────────────────────────────────────────────
# 主程式
# ──────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  台股掃描器｜雙策略版")
    print("  策略一：UT Bot + Squeeze Momentum 上升")
    print("  策略二：漲幅≥8% + Squeeze 正值反轉向上")
    print("=" * 55)

    stocks  = get_tw_stock_list()
    total   = len(stocks)
    res_s1, res_s2 = [], []

    print(f"\n🔍 開始掃描 {total} 檔股票...\n")

    for i, s in enumerate(stocks, 1):
        code, name = s["code"], s["name"]
        print(f"  [{i:4d}/{total}] {i/total*100:5.1f}%  {code} {name:<12}", end="\r")

        r1, r2 = analyze_stock(code, name, s.get('market', ''))
        if r1:
            res_s1.append(r1)
            print(f"\n  ✅ [策略一] {code} {name}  價格={r1['price']}  動量={r1['momentum']:.4f}")
        if r2:
            res_s2.append(r2)
            print(f"\n  🚀 [策略二] {code} {name}  漲幅={r2['change_pct']}%  動量={r2['momentum']:.4f}")

        time.sleep(DELAY_BETWEEN)

    print(f"\n\n{'='*55}")
    print(f"  掃描完成！策略一：{len(res_s1)} 檔  策略二：{len(res_s2)} 檔")
    print(f"{'='*55}\n")

    output = {
        "scan_time":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scan_date":        str(date.today()),
        "total_scanned":    total,
        "matched_strategy1": len(res_s1),
        "matched_strategy2": len(res_s2),
        "strategy1":        res_s1,
        "strategy2":        res_s2,
    }

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("📄 結果已儲存至 results.json")
    print("🌐 請開啟 dashboard.html 查看結果\n")


if __name__ == "__main__":
    main()
