import pprint
import pandas as pd
from scipy.signal import find_peaks  # type: ignore
import itertools
import numpy as np

pd.set_option("display.expand_frame_repr", False)  # не переносить строки
pd.set_option("display.max_colwidth", None)
pd.set_option("display.float_format", lambda x: "%.3f" % x)
pd.set_option("display.max_rows", 30)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)
pp = pprint.PrettyPrinter(indent=4)

def pnt(
    BTC_PRICE_DIR,
    TRADE_CICLE_MIN_DAYS_MIN_MAX_STEP,
    MIN_BTC_PRICE_DIFF_PCT_MIN_MAX_STEP,
    SMA_MIN,
    MIN_BTC_PRICE_DIFF_PLATO_MIN_MAX_STEP
):  

    cicle_range = np.round(np.arange(*TRADE_CICLE_MIN_DAYS_MIN_MAX_STEP), 2)
    price_diff_pct_range = np.round(np.arange(*MIN_BTC_PRICE_DIFF_PCT_MIN_MAX_STEP), 2)
    plato_range = np.round(np.arange(*MIN_BTC_PRICE_DIFF_PLATO_MIN_MAX_STEP), 2)
    total_iterarions = def_total_iterations(TRADE_CICLE_MIN_DAYS_MIN_MAX_STEP, MIN_BTC_PRICE_DIFF_PCT_MIN_MAX_STEP, MIN_BTC_PRICE_DIFF_PLATO_MIN_MAX_STEP)
    results_df = pd.DataFrame(columns=['CICLE', 'PRICE_DIFF_PCT', 'PLATO', 'PROFIT', 'SUM_AVG'])
    btc_price_df = get_btc_prices(BTC_PRICE_DIR)

    x = 0
    results = []
    for cicle, price_diff_pct, plato in itertools.product(cicle_range, price_diff_pct_range, plato_range):
        x += 1
        print(f'Итерация {x} из {total_iterarions}, {round((x/total_iterarions)*100, 2)} %')

        btc_price_df = analyze_with_parameters(btc_price_df, cicle, price_diff_pct, plato, SMA_MIN)
        profit, sum_avg = calculate_profit(btc_price_df)
        if not profit:
            profit = 0 
        new_row = [cicle, price_diff_pct, plato, profit, sum_avg]
        results.append(new_row)

    results_df = pd.DataFrame(results, columns=['CICLE', 'PRICE_DIFF_PCT', 'PLATO', 'PROFIT', 'SUM_AVG'])
    return results_df 

def def_total_iterations(TRADE_CICLE_MIN_DAYS_MIN_MAX_STEP, MIN_BTC_PRICE_DIFF_PCT_MIN_MAX_STEP, MIN_BTC_PRICE_DIFF_PLATO_MIN_MAX_STEP):
    num_cicle_points = np.arange(*TRADE_CICLE_MIN_DAYS_MIN_MAX_STEP).size
    num_price_diff_points = np.arange(*MIN_BTC_PRICE_DIFF_PCT_MIN_MAX_STEP).size
    num_plato_points = np.arange(*MIN_BTC_PRICE_DIFF_PLATO_MIN_MAX_STEP).size
    total_iterations = num_cicle_points * num_price_diff_points * num_plato_points
    return total_iterations

def get_btc_prices(BTC_PRICE_DIR):
    btc_price_df = pd.read_csv(BTC_PRICE_DIR) 
    btc_price_df.dropna(inplace=True)  # type: ignore
    btc_price_df = btc_price_df.reset_index(drop=True)
    btc_price_df["Human_time"] = pd.to_datetime(btc_price_df["Timestamp"], unit="s")  # type: ignore
    btc_price_df.rename(columns={"SMA_MINUTES_180": "BTC_Price_SMA_180"}, inplace=True)
    btc_price_df["Buy"], btc_price_df["Sell"] = 0, 0
    return btc_price_df

def analyze_with_parameters(btc_price_df, cicle, price_diff_pct, plato, SMA_MIN):
    prices = btc_price_df["Price"].values  # type: ignore
    peaks, _ = find_peaks(prices, distance=cicle * 24 * 60 / SMA_MIN, width=1)

    for index, peak in enumerate(peaks): 
        btc_price_df.loc[peak, "Sell"] = 1

    for i in range(1, len(peaks)):
    # Получаем интервал между двумя пиками
        start_peak = peaks[i - 1]
        end_peak = peaks[i]
        interval = btc_price_df.iloc[start_peak+1:end_peak]
        # Находим минимальную цену в интервале
        min_price_row = interval.loc[interval['Price'].idxmin()]
        min_price = min_price_row['Price']

        # Проверяем разницу в цене только со вторым пиком
        if abs(btc_price_df.iloc[end_peak]['Price'] - min_price) / min_price * 100 >= price_diff_pct:
            # Если условие выполняется, то точка с минимальной ценой - потенциальная точка для покупки
            potential_buy_points = interval[(interval['Price'] >= min_price) &
                                            (interval['Price'] <= min_price * (1 + plato / 100))]
            # Устанавливаем метку Buy для этих точек
            btc_price_df.loc[potential_buy_points.index, 'Buy'] = 1

    btc_price_df = identify_trade_intervals(btc_price_df)
    return btc_price_df

def identify_trade_intervals(btc_price_df):
    # Объединяем столбцы Buy и Sell
    btc_price_df['Trade'] = btc_price_df['Buy'] - btc_price_df['Sell']
    btc_price_df['Start_interval'] = 0
    btc_price_df['End_interval'] = 0
    trade_points = btc_price_df.copy()
    trade_points = trade_points.loc[btc_price_df['Trade'] != 0]

    # Находим индексы начала и конца торговых интервалов
    in_interval = False
    last_sell_index = None
    sell_indexes = {}

    for index, trade in trade_points['Trade'].items():
        if trade == 1:  # Если есть покупка
            if in_interval and last_sell_index:
                highest_index = max(sell_indexes, key=sell_indexes.get)
                btc_price_df.loc[highest_index, 'End_interval'] = 1
                in_interval = False
                last_sell_index = None
                sell_indexes = {}

            if not in_interval:  # Если ещё не в интервале
                btc_price_df.loc[index, 'Start_interval'] = 1  # Начало нового интервала
                in_interval = True
                last_sell_index = None  # Сброс последней продажи

        elif trade == -1 and in_interval:  # Если есть продажа и мы в интервале
            last_sell_index = index  # Обновляем индекс последней продажи
            sell_indexes[index] = btc_price_df.loc[index, 'SMA_10_MINUTES']

    # Если остались незакрытые интервалы
    if in_interval and last_sell_index is not None:
        if sell_indexes:
            highest_index = max(sell_indexes, key=sell_indexes.get)
            btc_price_df.loc[highest_index, 'End_interval'] = 1
        in_interval = False
        last_sell_index = None

    btc_price_df.to_parquet(r'btc_price_df_with_intervals.parquet')
    del trade_points
    return btc_price_df

def calculate_profit(btc_price_df):
    trade_points = btc_price_df.copy()
    trade_points = trade_points.loc[(trade_points['End_interval']!=0) | (trade_points['Start_interval']!=0)]
    index_pairs = [(trade_points.index[i], trade_points.index[i+1]) for i in range(0, len(trade_points.index) - 1, 2)]
    dollars = 1000
    btc = 0 
    sum_avg = 0
    commision_proc = 0.001
    for i, k in index_pairs:
        interval = btc_price_df.iloc[i:k+1]
        buy_prices = pd.Series([interval['Price'].iloc[i] for i in range(len(interval)) if interval['Buy'].iloc[i] == 1])
        avg_buy_price = buy_prices.mean()
        sell_prices = pd.Series([interval['Price'].iloc[i] for i in range(len(interval)) if interval['Sell'].iloc[i] == 1])
        avg_sell_price = sell_prices.mean()
        sum_avg += avg_sell_price - avg_buy_price
        
        btc = dollars/avg_buy_price
        btc = btc-btc*commision_proc
        dollars = 0
        dollars = btc*avg_sell_price
        dollars = dollars-dollars*commision_proc
        btc = 0

    if btc != 0:
        dollars += btc*sell_prices
        btc = 0
    return dollars, sum_avg
