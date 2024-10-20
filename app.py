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
    if group1 and 'Все' not in group1:
        filtered_data = filtered_data[filtered_data['Группа (вид1)'].isin(group1)]
    if subgroup2 and 'Все' not in subgroup2:
        filtered_data = filtered_data[filtered_data['Подгруппа (вид2)'].isin(subgroup2)]
    if department1 and 'Все' not in department1:
        filtered_data = filtered_data[filtered_data['Подразделение1'].isin(department1)]
    if department2 and 'Все' not in department2:
        filtered_data = filtered_data[filtered_data['Подразделение2'].isin(department2)]

    return filtered_data.groupby('Район', as_index=False)['Выручка'].sum()

# Интерфейс фильтров с множественным выбором
st.sidebar.header('Фильтры')

# Группа (вид1)
group1_options = ['Все'] + sales_data['Группа (вид1)'].unique().tolist()
group1_selected = st.sidebar.multiselect('Группа (вид1)', options=group1_options, default=[], key='group1')

# Подгруппа (вид2)
subgroup2_options = ['Все'] + sales_data['Подгруппа (вид2)'].unique().tolist()
subgroup2_selected = st.sidebar.multiselect('Подгруппа (вид2)', options=subgroup2_options, default=[], key='subgroup2')

# Подразделение1
department1_options = ['Все'] + sales_data['Подразделение1'].unique().tolist()
department1_selected = st.sidebar.multiselect('Подразделение1', options=department1_options, default=[], key='department1')

# Подразделение2
department2_options = ['Все'] + sales_data['Подразделение2'].unique().tolist()
department2_selected = st.sidebar.multiselect('Подразделение2', options=department2_options, default=[], key='department2')

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
                icon=folium.DivIcon(html=f'<div style="font-size: 6pt; font-weight: bold; white-space: nowrap;">{district_name}: {revenue_text} USD</div>')
            ).add_to(m)

        # Добавление цветовой шкалы
        colormap.add_to(m)

        # Отображение фильтров над картой
        filter_info = f"Примененные фильтры: Группа (вид1): {', '.join(group1_selected) if group1_selected else 'Все'}, Подгруппа (вид2): {', '.join(subgroup2_selected) if subgroup2_selected else 'Все'}, Подразделение1: {', '.join(department1_selected) if department1_selected else 'Все'}, Подразделение2: {', '.join(department2_selected) if department2_selected else 'Все'}"
        st.markdown(f"<div style='font-size: 10pt; color: black;'>{filter_info}</div>", unsafe_allow_html=True)

        # Отображение карты
        st.components.v1.html(m._repr_html_(), height=1400)  # Увеличен размер карты

    except Exception as e:
        st.error(f"Произошла ошибка: {e}")
