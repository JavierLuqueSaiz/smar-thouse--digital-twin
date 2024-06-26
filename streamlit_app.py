# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import cufflinks as cf
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import StackingRegressor, GradientBoostingRegressor, RandomForestRegressor, AdaBoostRegressor
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
import xgboost as xgb
import lightgbm as lgb
import requests
import json
from datetime import datetime, timedelta, time, date
import matplotlib.pyplot as plt
import pickle
from sklearn.metrics import root_mean_squared_error
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.metrics import mean_squared_error
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.metrics import r2_score
from sklearn.metrics import explained_variance_score
from sklearn.metrics import median_absolute_error
from sklearn.metrics import max_error
from sklearn.metrics import mean_squared_log_error
from sklearn.metrics import mean_poisson_deviance
from sklearn.metrics import mean_gamma_deviance

cf.set_config_file(sharing='private',theme='white',offline=True)

estilos = """
<style>
    .stMultiSelect .st-dr {
        background-color: darkblue !important;
    }
    header {
        background-image: linear-gradient(purple, rgb(0,0,100)) !important;
        color: white !important;
    }
    img {
        padding: 2rem;
    }
    .st-emotion-cache-6awftf {
        color: purple !important;
    }
    .st-emotion-cache-b5hcvb {
        color: purple !important;
    }
</style>
"""

st.html(estilos)

code = """
<style>
    .container{
        text-align: center;
    }
    .title {
        color: red;
        font-size: 2.8vw;
    }
    .card {
        background-color: rgb(200,200,200);
        border-radius: 20px;
    }
    .card-text {
        width: 100%;
        font-size: 1.7vw;
        font-weight: bold;
    }
</style>
<div class="container">
    <h1 class="title">Energetic Consumption Prediction</h1>
    <div class="card">
        <p class="card-text">Select the dates and reveal how much you will spend</p>
    </div>
</div>
"""
st.html(code)
st.error("WARNING: If you select a period with the time change (27-03-2016 02:00 and 30-10-2016 03:00) it will give an error for the prices. It is pending.")

# Descarga datos
@st.cache_data
def load_data():
    with open('streamlit-application/features.pkl', 'rb') as f:
            X = pickle.load(f)
    with open('streamlit-application/objetivos.pkl', 'rb') as f:
            y = pickle.load(f)
    with open('streamlit-application/dates.pkl', 'rb') as f:
            dates = pickle.load(f)

    return X, y, dates
df_features, df_objetivos, dates = load_data()

st.sidebar.title("Select appliance/Room")

appl = st.sidebar.selectbox("Appliance/Room", ["Overall", "Dishwasher", "Office", "Fridge", "Wine Cellar", "Garage Door", "Barn", "Well", "Microwave", "Living Room"])

appls = dict(zip(["Overall", "Dishwasher", "Office", "Fridge", "Wine Cellar", "Garage Door", "Barn", "Well", "Microwave", "Living Room"],
                 ['House.overall..kW.', 'Dishwasher..kW.', 'Home.office..kW.',
        'Fridge..kW.', 'Wine.cellar..kW.', 'Garage.door..kW.', 'Barn..kW.',
        'Well..kW.', 'Microwave..kW.', 'Living.room..kW.']))

st.sidebar.title("Select the period")

# Usando el widget st.datetime_input para obtener la fecha y hora del usuario
initial_day = st.sidebar.date_input("Initial day", value=datetime(2016, 10, 1), min_value = datetime(2016, 1, 1), max_value = datetime(2016, 12, 15))
initial_hour = st.sidebar.time_input("Initial hour (exact hour will be considered)", value=time(12,0))

final_day = st.sidebar.date_input("Final day (max difference: 30 days)", value=initial_day + timedelta(days=20), min_value = initial_day, max_value = min(initial_day + timedelta(days=30),
                                                                                                                                     date(2016, 12, 15)))
final_hour = st.sidebar.time_input("Final hour (exact hour will be considered)", value = initial_hour)
if final_day == date(2016, 12, 15) and final_hour > time(22, 59):
    st.error("ERROR: For this day, select an hour before 23:00")

if initial_hour.minute == 0:
    initial_datetime = datetime.combine(initial_day, initial_hour)
else:
    initial_datetime = datetime.combine(initial_day, initial_hour) - timedelta(hours=1)
final_datetime = datetime.combine(final_day, final_hour)

i_m = initial_datetime.month
i_d = initial_datetime.day
i_h = initial_datetime.hour

f_m = final_datetime.month
f_d = final_datetime.day
f_h = final_datetime.hour

initial_index = dates.index[(dates['Mes'] == i_m) & (dates['Hora'] == i_h) & (dates['Dia'] == i_d)].tolist()[0]
final_index = dates.index[(dates['Mes'] == f_m) & (dates['Hora'] == f_h) & (dates['Dia'] == f_d)].tolist()[0]

dates_test = pd.to_datetime({
    'year': 2016,
    'month': dates.loc[initial_index:final_index, 'Mes'],
    'day': dates.loc[initial_index:final_index, 'Dia'],
    'hour': dates.loc[initial_index:final_index, 'Hora']
})

X = np.array(df_features)
y = np.array(df_objetivos[[appls[appl]]]).flatten()

X_test = X[initial_index:final_index+1]
y_test = y[initial_index:final_index+1]

X_train = np.concatenate([X[:initial_index], X[final_index+1:]])
y_train = np.concatenate([y[:initial_index], y[final_index+1:]])

m = AdaBoostRegressor(
    estimator = DecisionTreeRegressor(criterion='friedman_mse', max_depth=20, min_samples_split=10, splitter='random'),
    n_estimators = 25,
)
model = m.fit(X_train,y_train)

yp = model.predict(X_test)

if len(dates_test) > 125:

    df_p = pd.DataFrame({'fecha': dates_test, 'valor': yp})
    df_pr = pd.DataFrame(columns=["fecha","valor","suma_acumulada"])
    s = 0
    size = len(df_p)
    n = size // 75

    code = """
        <style>
            .ast {{
                position: relative;
                top: -0.4vw;
                font-size: 1.2vw;
                margin-right: 1px;
            }}
            .agg {{
                font-size: 0.9vw;
                font-style: italic;
                color: rgb(173, 27, 27);
                margin-bottom: -1vw;
            }}
        </style>

        <p class="agg"><span class="ast">*</span>Aggregation of {} hours</p>
    """.format(n)

    st.html(code)

    while s+n < size:
        portion = df_p.iloc[s:s+n]
        s += n
        portion['suma_acumulada'] = portion['valor'].cumsum()
        df_pr = pd.concat([df_pr, portion.iloc[[-1]]])
    portion = df_p.iloc[s:]
    s += n
    portion['suma_acumulada'] = portion['valor'].cumsum()
    df_pr = pd.concat([df_pr, portion.iloc[[-1]]])

    df_r = pd.DataFrame({'fecha': dates_test, 'valor': y_test})
    df_rr = pd.DataFrame(columns=["fecha","valor","suma_acumulada"])
    s = 0
    size = len(df_r)
    n = size // 75
    while s+n < size:
        portion = df_r.iloc[s:s+n]
        s += n
        portion['suma_acumulada'] = portion['valor'].cumsum()
        df_rr = pd.concat([df_rr, portion.iloc[[-1]]])
    portion = df_r.iloc[s:]
    s += n
    portion['suma_acumulada'] = portion['valor'].cumsum()
    df_rr = pd.concat([df_rr, portion.iloc[[-1]]])

    fig, ax = plt.subplots()

    ax.plot(df_rr["fecha"], df_rr["suma_acumulada"], label='Real', color="darkblue")
    ax.plot(df_pr["fecha"], df_pr["suma_acumulada"], label='Predicted', color="purple")
    ax.set_xlabel('Date')
    ax.set_ylabel('kW', rotation=0)
    ax.set_title(f'Prediction from {dates_test.iloc[0]} to {dates_test.iloc[-1]}')
    ax.yaxis.set_label_coords(-0.15,0.5)
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    ax.tick_params(axis="x", labelrotation=45)

    # Mostrar el gráfico en Streamlit
    st.pyplot(fig)

else:
    code = """
        <p class="agg"><span class="ast">*</span>No Aggregation</p>
    """
    st.html(code)

    fig, ax = plt.subplots()

    ax.plot(dates_test, yp, label='Predicted', color="purple")
    ax.plot(dates_test, y_test, label='Real', color="darkblue")
    ax.set_xlabel('Date')
    ax.set_ylabel('kW', rotation=0)
    ax.set_title(f"Real vs Predicted from {initial_datetime} to {final_datetime}")
    ax.yaxis.set_label_coords(-0.1,0.5)
    ax.legend()
    ax.tick_params(axis="x", labelrotation=45)

    # Mostrar el gráfico en Streamlit
    st.pyplot(fig)

mets = ["RMSE",
        "MAPE",
        "R2-Score",
        "MSE",
        "MAE",
        "Explained Variance Score",
        "Median Absolute Error",
        "Max Error",
        "Mean Squared Logarithmic Error",
        "Mean Poisson Deviance",
        "Mean Gamma Deviance"]

metrics = ["RMSE","MAPE"]
metrics = st.multiselect("Select Metrics", mets, default=metrics)
p = ""
if "RMSE" in metrics:
    p += '<p class="metric">RMSE: <span class="number">{}</span></p>'.format(np.round(root_mean_squared_error(yp,y_test),3))
if "MAPE" in metrics:
    p += '<p class="metric">MAPE: <span class="number">{}%</span></p>'.format(np.round(mean_absolute_percentage_error(yp,y_test)*100,3))
if "MSE" in metrics:
    p += '<p class="metric">MSE: <span class="number">{}</span></p>'.format(np.round(mean_squared_error(yp,y_test),3))
if "MAE" in metrics:
    p += '<p class="metric">MAE: <span class="number">{}</span></p>'.format(np.round(mean_absolute_error(yp,y_test),3))
if "R2-Score" in metrics:
    p += '<p class="metric">R2-Score: <span class="number">{}</span></p>'.format(np.round(r2_score(yp,y_test),3))
if "Explained Variance Score" in metrics:
    p += '<p class="metric">Explained Variance Score: <span class="number">{}</span></p>'.format(np.round(explained_variance_score(yp,y_test),3))
if "Median Absolute Error" in metrics:
    p += '<p class="metric">Median Absolute Error: <span class="number">{}</span></p>'.format(np.round(median_absolute_error(yp,y_test),3))
if "Max Error" in metrics:
    p += '<p class="metric">Max Error: <span>{}</span class="number"></p>'.format(np.round(max_error(yp,y_test),3))
if "Mean Squared Logarithmic Error" in metrics:
    p += '<p class="metric">Mean Squared Logarithmic Error: <span class="number">{}</span></p>'.format(np.round(mean_squared_log_error(yp,y_test),3))
if "Mean Poisson Deviance" in metrics:
    p += '<p class="metric">Mean Poisson Deviance: <span class="number">{}</span></p>'.format(np.round(mean_poisson_deviance(yp,y_test),3))
if "Mean Gamma Deviance" in metrics:
    p += '<p class="metric">Mean Gamma Deviance: <span class="number">{}</span></p>'.format(np.round(mean_gamma_deviance(yp,y_test),3))


code = """
    <style>
        .metrics-title {{
            color: darkblue;
            font-size: 2.1vw;
        }}
        .metrics {{
            background-color: lightblue;
            padding: 5px;
            border-radius: 7px;
        }}
        .number {{
            left-margin: 5px;
            font-weight: normal;
            font-size: 1.1vw;
            padding: 0;
            position: relative;
            top: 0;
            left: 15px;
        }}
        .metric {{
            font-weight: bold;
            margin: 2px 0 2px 2px;
            font-size: 1.1vw;
        }}
    </style>
    <h3 class=metrics-title>These are the evaluation metrics of your model:</h3>
    <div class="metrics">
        {}
    </div>
    """.format(p)
st.html(code)

def api(i,f):

    i = i.strftime('%Y-%m-%d %H:%M:%S')
    f = f.strftime('%Y-%m-%d %H:%M:%S')

    i = str(i).replace(" ","T")
    f = str(f).replace(" ","T")

    url = "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"
    params = {
        "start_date": i,
        "end_date": f,
        "time_trunc": "hour"
    }

    # Realizar la solicitud GET
    response = requests.get(url, params=params)

    # Verificar si la solicitud fue exitosa (código de estado 200)
    if response.status_code == 200:
        # Extraer los datos en formato JSON
        data = response.json()
        # Aquí puedes procesar los datos según tus necesidades
        #print(data)
    else:
        # En caso de error, imprimir el código de estado
        st.error(f"Error: {response.status_code}")

    data = json.loads(json.dumps(data))
    pvpc_values = data['included'][0]['attributes']['values']
    #print("Precios de mercado peninsular en tiempo real (PVPC):")
    precios = []
    for value in pvpc_values:
        precios.append(value['value'])

    return precios

precios = api(initial_datetime, final_datetime)

precios = np.array(precios)
costes = precios*yp/1000
c_ascendente = costes.cumsum()
c_total = costes.sum()

fig, (ax1,ax2) = plt.subplots(1,2)

if len(dates_test) > 125:

    df_r = pd.DataFrame({'fecha': dates_test, 'valor': costes})
    df_rr = pd.DataFrame(columns=["fecha","valor","suma_acumulada"])
    s = 0
    size = len(df_r)
    n = size // 75
    while s+n < size:
        portion = df_r.iloc[s:s+n]
        s += n
        portion['suma_acumulada'] = portion['valor'].cumsum()
        df_rr = pd.concat([df_rr, portion.iloc[[-1]]])
    portion = df_r.iloc[s:]
    s += n
    portion['suma_acumulada'] = portion['valor'].cumsum()
    df_rr = pd.concat([df_rr, portion.iloc[[-1]]])

    ax1.plot(df_rr["fecha"], df_rr["suma_acumulada"], color="darkblue")
else:
    ax1.plot(dates_test, costes, color="darkblue")
ax2.plot(dates_test, c_ascendente, color="darkblue")
ax1.set_xlabel('Date')
ax2.set_xlabel('Date')
ax1.set_ylabel('€', rotation=0)
ax2.set_ylabel('€', rotation=0)
ax1.set_title('Predicted Cost')
ax2.set_title('Accumulated Predicted Cost')
fig.subplots_adjust(wspace=0.5)
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=90)
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=90)

# Mostrar el gráfico en Streamlit
st.pyplot(fig)

code = """
    <style>
        .total-cont {{
            background-color: lightblue;
            padding: 5px;
            border-radius: 7px;
        }}
        .numb {{
            left-margin: 5px;
            font-weight: normal;
            font-size: 1.1vw;
            padding: 0;
            position: relative;
            top: 0;
            left: 15px;
        }}
        .total {{
            font-weight: bold;
            margin: 2px 0 2px 2px;
            font-size: 1.1vw;
        }}
    </style>

    <div class="total-cont">
        <p class="total">TOTAL COST: <span class="numb">{}€</span></p>
    </div>
""".format(np.round(c_total))

st.html(code)
