import pandas as pd
import geopandas as gpd
import folium
from shapely import wkt
import branca.colormap as cm
import streamlit as st

# Шаг 1: Загрузка данных
sales_data = pd.read_excel('ПродажиИюньДляКарт_Абс.xlsx')
mapping_df = pd.read_csv('ТаблСоотвНаименованийРайонов1СиGADM.csv', sep=';')
districts_data = pd.read_csv('districts_data.csv')

# Шаг 2: Преобразование геометрий из WKT в объекты shapely
districts_data['geometry'] = districts_data['geometry'].apply(wkt.loads)

# Функция для форматирования выручки
def format_revenue(value):
    return f"{value:,.0f}".replace(',', ' ').replace('.', ',')

# Шаг 3: Агрегация данных о продажах по районам
aggregated_sales_data = sales_data.groupby('Район', as_index=False)['Выручка'].sum()

# Шаг 4: Объединение агрегированных данных с таблицей соответствия
aggregated_sales_data = aggregated_sales_data.merge(mapping_df, left_on='Район', right_on='Район RU', how='outer')

# Шаг 5: Объединение с данными о полигонах
aggregated_sales_data = aggregated_sales_data.merge(districts_data, left_on='Район BY', right_on='NL_NAME_2', how='outer')

# Функция для фильтрации данных
def filter_data(group1, subgroup2, department1, department2):
    filtered_data = sales_data.copy()

    # Применение фильтров
    if group1 != 'Все':
        filtered_data = filtered_data[filtered_data['Группа (вид1)'] == group1]
    if subgroup2 != 'Все':
        filtered_data = filtered_data[filtered_data['Подгруппа (вид2)'] == subgroup2]
    if department1 != 'Все':
        filtered_data = filtered_data[filtered_data['Подразделение1'] == department1]
    if department2 != 'Все':
        filtered_data = filtered_data[filtered_data['Подразделение2'] == department2]

    return filtered_data.groupby('Район', as_index=False)['Выручка'].sum()

# Создаем виджеты для фильтрации
st.title("Фильтры для продажи")
group1_widget = st.selectbox("Группа (вид1):", ['Все'] + sales_data['Группа (вид1)'].unique().tolist())
subgroup2_widget = st.selectbox("Подгруппа (вид2):", ['Все'] + sales_data['Подгруппа (вид2)'].unique().tolist())
department1_widget = st.selectbox("Подразделение1:", ['Все'] + sales_data['Подразделение1'].unique().tolist())
department2_widget = st.selectbox("Подразделение2:", ['Все'] + sales_data['Подразделение2'].unique().tolist())

# Создаем кнопку для запуска формирования карты
if st.button("Сформировать карту"):
    with st.spinner("Создание карты..."):
        # Попробуем отфильтровать данные
        try:
            filtered_data = filter_data(group1_widget, subgroup2_widget, department1_widget, department2_widget)
            filtered_data = filtered_data.merge(mapping_df, left_on='Район', right_on='Район RU', how='outer')
            filtered_data = filtered_data.merge(districts_data, left_on='Район BY', right_on='NL_NAME_2', how='outer')

            # Заменяем NaN на 0
            filtered_data['Выручка'] = filtered_data['Выручка'].fillna(0)

            # Создание цветовой шкалы
            max_value = filtered_data['Выручка'].max()
            min_value = filtered_data['Выручка'].min()
            colormap = cm.LinearColormap(colors=['green', 'yellow', 'orange', 'red'], vmin=min_value, vmax=max_value)
            colormap.caption = 'Выручка по районам (USD)'

            # Создаем карту
            m = folium.Map(location=[53.9, 27.5], zoom_start=7)

            # Добавление геообъектов на карту с цветовой заливкой
            for _, row in filtered_data.iterrows():
                geojson_data = row['geometry']

                # Добавление заливки полигона
                folium.GeoJson(
                    geojson_data,
                    style_function=lambda x, revenue=row['Выручка']: {
                        'fillColor': colormap(revenue) if revenue > 0 else 'none',
                        'color': 'black',
                        'weight': 1,
                        'fillOpacity': 0.6 if revenue > 0 else 0.3,
                    }
                ).add_to(m)

                # Вычисление центра полигона для размещения текста
                centroid = geojson_data.centroid

                # Расчет смещения влево на длину названия района
                district_name = row["Район RU"]
                offset = -len(district_name) * 0.002
                revenue_text = format_revenue(row["Выручка"])
                folium.map.Marker(
                    location=[centroid.y, centroid.x + offset],
                    icon=folium.DivIcon(html=f'<div style="font-size: 12pt; font-weight: bold; white-space: nowrap;">{district_name}: {revenue_text} USD</div>')
                ).add_to(m)

            # Добавление цветовой шкалы на карту
            colormap.add_to(m)

            # Сохранение карты в HTML
            map_html_file = 'sales_map_filtered.html'
            m.save(map_html_file)

            # Отображение карты на экране
            st.components.v1.html(m._repr_html_(), width=700, height=600)  # Отображение карты в Streamlit

        except Exception as e:
            st.error(f"Произошла ошибка: {e}")

