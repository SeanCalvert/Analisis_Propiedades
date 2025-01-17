import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time

def build_url(min_rooms, max_rooms, min_price, max_price, min_age, max_age, offset=None):
    base_url = "https://inmuebles.mercadolibre.com.ar/departamentos/venta/apto-credito/"
    filters = f"{min_rooms}-a-{max_rooms}-ambientes/capital-federal/belgrano-barrancas-o-belgrano-c-o-belgrano-chico-o-belgrano-r-o-belgrano-o-botanico-o-caballito-o-coghlan-o-colegiales-o-las-canitas-o-nunez-o-palermo-o-palermo-chico-o-palermo-hollywood-o-palermo-nuevo-o-palermo-soho-o-palermo-viejo-o-villa-urquiza/deparamentos-2-ambientes"
    if offset:
        filters += f"_Desde_{offset}"
    filters += f"_PriceRange_{min_price}USD-{max_price}USD_NoIndex_True_PROPERTY*AGE_{min_age}-{max_age}#applied_filter_id%3DPROPERTY_AGE%26applied_filter_name%3DAntig%C3%BCedad%26applied_filter_order%3D14%26applied_value_id%3D{min_age}-{max_age}%26applied_value_name%3D{min_age}-{max_age}%26applied_value_order%3D6%26applied_value_results%3DUNKNOWN_RESULTS%26is_custom%3Dtrue"
    return base_url + filters

def main():
    min_rooms = input("Ingrese la cantidad mínima de ambientes: ")
    max_rooms = input("Ingrese la cantidad máxima de ambientes: ")
    min_price = input("Ingrese el precio mínimo en USD: ")
    max_price = input("Ingrese el precio máximo en USD: ")
    min_age = input("Ingrese la antigüedad mínima: ")
    max_age = input("Ingrese la antigüedad máxima: ")

    encabezados = {
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/71.0.3578.80 Chrome/71.0.3578.80 Safari/537.36"
    }

    # Listas para almacenar los datos
    titulos = []
    precios = []
    direcciones = []
    barrios = []
    ciudades = []
    links = []
    ambientes = []
    banios = []
    metros_cuadrados = []
    antiguedades = []

    offset = 0
    results_per_page = 48
    total_results = 693  # Ajusta este valor según el total de resultados esperados

    while offset < total_results:
        url = build_url(min_rooms, max_rooms, min_price, max_price, min_age, max_age, offset if offset else None)
        print(f"Analizando URL: {url}")
        
        try:
            response = requests.get(url, headers=encabezados, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error al realizar la solicitud: {e}")
            time.sleep(5)
            continue

        content = response.content
        soup = BeautifulSoup(content, 'html.parser')

        # Obtener todos los productos
        productos_html = soup.find_all('li', class_='ui-search-layout__item')
        if not productos_html:
            break

        # Extraer datos de cada producto
        for producto_html in productos_html:
            # Título
            titulo = producto_html.find('a', class_='poly-component__title').text.strip()
            titulos.append(titulo)
            
            # Precio
            precio = producto_html.find('span', class_='andes-money-amount__fraction').text.strip()
            precios.append(precio)
            
            # Ubicación
            ubicacion = producto_html.find('span', class_='poly-component__location').text.strip()
            ubicacion_parts = ubicacion.split(',')
            if len(ubicacion_parts) == 3:
                direcciones.append(ubicacion_parts[0].strip())
                barrios.append(ubicacion_parts[1].strip())
                ciudades.append(ubicacion_parts[2].strip())
            else:
                direcciones.append("No especificado")
                barrios.append("No especificado")
                ciudades.append("No especificado")
            
            # Link
            link = producto_html.find('a', class_='poly-component__title')['href']
            links.append(link)
            
            # Atributos
            atributos_html = producto_html.find_all('li', class_='poly-attributes-list__item')
            atributos_texto = [atributo.text.strip() for atributo in atributos_html]
            
            # Dividir los atributos en columnas individuales
            if len(atributos_texto) == 3:
                ambientes.append(atributos_texto[0])
                banios.append(atributos_texto[1])
                metros_cuadrados.append(atributos_texto[2])
            else:
                ambientes.append("No especificado")
                banios.append("No especificado")
                metros_cuadrados.append("No especificado")
            
            # Antigüedad
            antiguedad_element = producto_html.find('span', class_='ui-search-card-attributes__attribute')
            if antiguedad_element:
                antiguedad = antiguedad_element.text.strip()
            else:
                antiguedad = "No especificado"
            antiguedades.append(antiguedad)

        offset += results_per_page
        time.sleep(5)  # Pausa de 5 segundos entre solicitudes

    # Crear un DataFrame con los datos obtenidos
    data = {
        'Título': titulos,
        'Precio (US$)': precios,
        'Dirección': direcciones,
        'Barrio': barrios,
        'Ciudad': ciudades,
        'Link': links,
        'Ambientes': ambientes,
        'Baños': banios,
        'Metros Cuadrados': metros_cuadrados,
        'Antigüedad': antiguedades
    }

    df = pd.DataFrame(data)

    # Limpiar y convertir las columnas de precios y metros cuadrados
    df['Precio (US$)'] = df['Precio (US$)'].str.replace('.', '').astype(float)
    df['Metros Cuadrados Limpios'] = df['Metros Cuadrados'].apply(lambda x: re.search(r'^\d+\s*m²', x).group(0).split()[0] if re.search(r'^\d+\s*m²', x) else None).astype(float)

    # Calcular el precio por metro cuadrado
    df['$ x m2'] = df.apply(lambda row: round(row['Precio (US$)'] / row['Metros Cuadrados Limpios'], 2) if pd.notnull(row['Metros Cuadrados Limpios']) else None, axis=1)

    # Calcular el promedio del precio por metro cuadrado por barrio
    promedio_por_barrio = df.groupby('Barrio')['$ x m2'].mean().rename('Promedio $ x m2')

    # Unir el promedio al DataFrame original
    df = df.join(promedio_por_barrio, on='Barrio')

    # Calcular la diferencia con respecto al promedio de la zona
    df['Diferencia con Promedio'] = df['$ x m2'] - df['Promedio $ x m2']

    # Análisis del precio por metro cuadrado promedio, metros cuadrados promedio y conteo de departamentos por barrio
    analisis_barrio = df.groupby('Barrio').agg({
        '$ x m2': 'mean',
        'Metros Cuadrados Limpios': 'mean',
        'Título': 'count'
    }).rename(columns={'$ x m2': 'Precio Promedio x m2', 'Metros Cuadrados Limpios': 'Metros Cuadrados Promedio', 'Título': 'Cantidad de Departamentos'})

    # Redondear los valores a dos decimales
    analisis_barrio['Precio Promedio x m2'] = analisis_barrio['Precio Promedio x m2'].round(2)
    analisis_barrio['Metros Cuadrados Promedio'] = analisis_barrio['Metros Cuadrados Promedio'].round(2)

    # Obtener el departamento más barato y más caro por barrio
    df['Precio (US$)'] = df['Precio (US$)'].astype(float)
    mas_barato_por_barrio = df.loc[df.groupby('Barrio')['Precio (US$)'].transform('min') == df['Precio (US$)']]
    mas_caro_por_barrio = df.loc[df.groupby('Barrio')['Precio (US$)'].transform('max') == df['Precio (US$)']]

    # Crear un DataFrame con la información del más barato y más caro por barrio
    extremos_por_barrio = pd.concat([mas_barato_por_barrio, mas_caro_por_barrio]).drop_duplicates().sort_values(by='Barrio')
    extremos_por_barrio = extremos_por_barrio[['Barrio', 'Título', 'Precio (US$)', 'Link']]

    # Mostrar la cantidad de registros obtenidos
    print(f"Cantidad total de registros obtenidos: {len(df)}")

    # Guardar el DataFrame en un archivo CSV
    df.to_csv('departamentos.csv', index=False)

    # Guardar el análisis por barrio en un archivo CSV
    analisis_barrio.to_csv('analisis_por_barrio.csv')

    # Guardar la información del más barato y más caro por barrio en un archivo CSV
    extremos_por_barrio.to_csv('extremos_por_barrio.csv', index=False)

if __name__ == "__main__":
    main()