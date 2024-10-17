import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from shapely import wkt
import branca.colormap as cm

# Шаг 1: Загрузка данных
sales_data = pd.read_excel('ПродажиИюньДляКарт_Абс.xlsx')
mapping_df = pd.read_csv('ТаблСоотвНаименованийРайонов1СиGADM.csv', sep=';')
districts_data = pd.read_csv('districts_data.csv')

# Преобразование геометрий из WKT в объекты shapely
districts_data['geometry'] = districts_data['geometry'].apply(wkt.loads)

# Функция для форматирования выручки
def format_revenue(value):
    return f"{value:,.0f}".replace(',', ' ').replace('.', ',')

# Функция для фильтрации данных
def filter_data(group1, subgroup2, department1, department2):
    filtered_data = sales_data.copy()

    # Применение фильтров с учетом множественного выбора
    if group1:
        filtered_data = filtered_data[filtered_data['Группа (вид1)'].isin(group1)]
    if subgroup2:
        filtered_data = filtered_data[filtered_data['Подгруппа (вид2)'].isin(subgroup2)]
    if department1:
        filtered_data = filtered_data[filtered_data['Подразделение1'].isin(department1)]
    if department2:
        filtered_data = filtered_data[filtered_data['Подразделение2'].isin(department2)]

    return filtered_data.groupby('Район', as_index=False)['Выручка'].sum()

# Интерфейс фильтров с множественным выбором
st.sidebar.header('Фильтры')

# Группа (вид1)
group1_options = sales_data['Группа (вид1)'].unique().tolist()
group1_selected = st.sidebar.multiselect('Группа (вид1)', options=['Все'] + group1_options, default=['Все'], key='group1')

# Подгруппа (вид2)
subgroup2_options = sales_data['Подгруппа (вид2)'].unique().tolist()
subgroup2_selected = st.sidebar.multiselect('Подгруппа (вид2)', options=['Все'] + subgroup2_options, default=['Все'], key='subgroup2')

# Подразделение1
department1_options = sales_data['Подразделение1'].unique().tolist()
department1_selected = st.sidebar.multiselect('Подразделение1', options=['Все'] + department1_options, default=['Все'], key='department1')

# Подразделение2
department2_options = sales_data['Подразделение2'].unique().tolist()
department2_selected = st.sidebar.multiselect('Подразделение2', options=['Все'] + department2_options, default=['Все'], key='department2')

# Убираем "Все" из выбранных, если выпадающий список был раскрыт
if st.session_state.get('group1_expanded', False):
    group1_selected = [item for item in group1_selected if item != 'Все']
if st.session_state.get('subgroup2_expanded', False):
    subgroup2_selected = [item for item in subgroup2_selected if item != 'Все']
if st.session_state.get('department1_expanded', False):
    department1_selected = [item for item in department1_selected if item != 'Все']
if st.session_state.get('department2_expanded', False):
    department2_selected = [item for item in department2_selected if item != 'Все']

# Триггеры для отслеживания раскрытия списков
def on_expand(group):
    st.session_state[f'{group}_expanded'] = True

st.sidebar.markdown("### Список элементов фильтра")

# Создание триггеров для отслеживания раскрытия списков
if st.sidebar.button('Развернуть группу (вид1)'):
    on_expand('group1')
if st.sidebar.button('Развернуть подгруппу (вид2)'):
    on_expand('subgroup2')
if st.sidebar.button('Развернуть подразделение1'):
    on_expand('department1')
if st.sidebar.button('Развернуть подразделение2'):
    on_expand('department2')

# Кнопка для запуска формирования карты
if st.sidebar.button("Сформировать карту"):
    try:
        # Фильтрация данных
        filtered_data = filter_data(group1_selected, subgroup2_selected, department1_selected, department2_selected)
        filtered_data = filtered_data.merge(mapping_df, left_on='Район', right_on='Район RU', how='outer')
        filtered_data = filtered_data.merge(districts_data, left_on='Район BY', right_on='NL_NAME_2', how='outer')

        # Заполнение NaN значениями
        filtered_data['Выручка'] = filtered_data['Выручка'].fillna(0)

        # Создание цветовой шкалы
        max_value = filtered_data['Выручка'].max()
        min_value = filtered_data['Выручка'].min()
        colormap = cm.LinearColormap(colors=['green', 'yellow', 'orange', 'red'], vmin=min_value, vmax=max_value)
        colormap.caption = 'Выручка по районам (USD)'

        # Создание карты
        m = folium.Map(location=[53.9, 27.5], zoom_start=7)

        # Добавление геообъектов на карту с цветовой заливкой
        for _, row in filtered_data.iterrows():
            geojson_data = row['geometry']
            folium.GeoJson(
                geojson_data,
                style_function=lambda x, revenue=row['Выручка']: {
                    'fillColor': colormap(revenue) if revenue > 0 else 'none',
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': 0.6 if revenue > 0 else 0.3,
                }
            ).add_to(m)

            centroid = geojson_data.centroid
            district_name = row["Район RU"]
            offset = -len(district_name) * 0.002
            revenue_text = format_revenue(row["Выручка"])
            folium.map.Marker(
                location=[centroid.y, centroid.x + offset],
                icon=folium.DivIcon(html=f'<div style="font-size: 12pt; font-weight: bold; white-space: nowrap;">{district_name}: {revenue_text} USD</div>')
            ).add_to(m)

        # Добавление цветовой шкалы
        colormap.add_to(m)

        # Отображение карты
        st.components.v1.html(m._repr_html_(), height=600)

    except Exception as e:
        st.error(f"Произошла ошибка: {e}")
