import pandas as pd
import geopandas as gpd
import folium
from shapely import wkt
import branca.colormap as cm
import ipywidgets as widgets
from IPython.display import display
from google.colab import files

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
group1_widget = widgets.Dropdown(options=['Все'] + sales_data['Группа (вид1)'].unique().tolist(), description='Группа (вид1):')
subgroup2_widget = widgets.Dropdown(options=['Все'] + sales_data['Подгруппа (вид2)'].unique().tolist(), description='Подгруппа (вид2):')
department1_widget = widgets.Dropdown(options=['Все'] + sales_data['Подразделение1'].unique().tolist(), description='Подразделение1:')
department2_widget = widgets.Dropdown(options=['Все'] + sales_data['Подразделение2'].unique().tolist(), description='Подразделение2:')

# Создаем кнопку для запуска формирования карты
generate_map_button = widgets.Button(description="Сформировать карту")

# Создаем область для отображения карты
map_output = widgets.Output()

# Функция для отображения карты с отфильтрованными данными
def update_map(button):
    with map_output:
        map_output.clear_output()  # Очищаем предыдущую карту
        
        group1 = group1_widget.value
        subgroup2 = subgroup2_widget.value
        department1 = department1_widget.value
        department2 = department2_widget.value
        
        # Попробуем отфильтровать данные
        try:
            filtered_data = filter_data(group1, subgroup2, department1, department2)
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
            m.save('sales_map_filtered.html')

            # Отображение карты на экране
            display(m)
        except Exception as e:
            print(f"Произошла ошибка: {e}")

# Привязываем функцию обновления карты к нажатию кнопки
generate_map_button.on_click(update_map)

# Создаем фиксированные окна
filter_box = widgets.VBox([group1_widget, subgroup2_widget, department1_widget, department2_widget, generate_map_button], layout=widgets.Layout(width='300px'))
map_box = widgets.VBox([map_output], layout=widgets.Layout(height='3600px'))

# Фиксация области с фильтрами и карты
ui = widgets.HBox([filter_box, map_box])

# Отображение виджетов для выбора фильтров и области для карты
display(ui)