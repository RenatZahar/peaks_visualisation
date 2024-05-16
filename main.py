import plotly.graph_objs as go
from plotly.offline import plot
from flask import Flask, render_template
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import peaksntroughs as pnt
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

BTC_PRICE_DIR = r'I:\my_python\Traider_bot\bot, scripts, data\цены биткоина\чистка цен BTC и их сглаживание\smoothed_BTCUSDT_10min.csv'
SMA_MIN = 10

app = Flask(__name__)

cicle, price_diff_pct, plato = 16, 8, 1.5
btc_price_df = pnt.get_btc_prices(BTC_PRICE_DIR)
btc_price_data = pnt.analyze_with_parameters(btc_price_df, cicle, price_diff_pct, plato, SMA_MIN)
print(pnt.calculate_profit(btc_price_data))
sell_signals = btc_price_data[btc_price_data['Sell'] > 0]
buy_signals = btc_price_data[btc_price_data['Buy'] > 0]
start_interval_signals = btc_price_data[btc_price_data['Start_interval'] > 0]
end_interval_signals = btc_price_data[btc_price_data['End_interval'] > 0]

hover_text = ['Дата: {}<br>Индекс: {}<br>Цена: {}<br>tmsp: {}'.format(date, idx, price, timestamp) for idx, (date, price, timestamp) in enumerate(zip(btc_price_data['Human_time'], btc_price_data['SMA_10_MINUTES'], btc_price_data['Timestamp']))]
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=btc_price_data['Human_time'], y=btc_price_data['SMA_10_MINUTES'], mode='lines', name='BTC Price', text=hover_text, hoverinfo='text+name'), secondary_y=False)

# Создаем текст для отображения при наведении для сигналов покупки, Добавляем сигналы покупки на график
hover_text_sell = ['Дата: {}<br>Индекс: {}<br>Цена продажи: {}<br>tmsp: {}'.format(date, idx, price, timestamp) 
                  for idx, (date, price, timestamp) in enumerate(zip(sell_signals['Human_time'], sell_signals['SMA_10_MINUTES'], sell_signals['Timestamp']))]
fig.add_trace(go.Scatter(x=sell_signals['Human_time'], y=sell_signals['SMA_10_MINUTES'], mode='markers', name='Sell Signal',
                         marker=dict(color='red'), text=hover_text_sell, hoverinfo='text+name'), secondary_y=False)

# Создаем текст для отображения при наведении для сигналов покупки, Добавляем сигналы покупки на график
hover_text_buy = ['Дата: {}<br>Индекс: {}<br>Цена продажи: {}<br>tmsp: {}'.format(date, idx, price, timestamp) 
                 for idx, (date, price, timestamp) in enumerate(zip(buy_signals['Human_time'], buy_signals['SMA_10_MINUTES'], buy_signals['Timestamp']))]
fig.add_trace(go.Scatter(x=buy_signals['Human_time'], y=buy_signals['SMA_10_MINUTES'], mode='markers', name='Buy Signal',
                         marker=dict(color='blue'), text=hover_text_buy, hoverinfo='text+name'), secondary_y=False)

shapes = []
for idx, row in start_interval_signals.iterrows():
    if row['Start_interval'] == 1:
        shapes.append(dict(type='line', x0=row['Human_time'], y0=0, x1=row['Human_time'], y1=1, xref='x', yref='paper', line=dict(color='blue', width=1)))
 
for idx, row in end_interval_signals.iterrows():
    if row['End_interval'] == 1:
        shapes.append(dict(type='line', x0=row['Human_time'], y0=0, x1=row['Human_time'], y1=1, xref='x', yref='paper', line=dict(color='red', width=1)))

# Добавляем вертикальные линии на график
for shape in shapes:
    fig.add_shape(shape)

fig.update_yaxes(title_text="BTC Price", secondary_y=False)
fig.update_yaxes(title_text="Signals", secondary_y=True)
 
@app.route('/')
def index():
    div = plot(fig, output_type='div', include_plotlyjs=False)
    return render_template('plotly_graph.html', plot_div=div)

if __name__ == '__main__':
    app.run(debug=True)