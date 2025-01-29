import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import unicodedata

def obtener_total_resultados(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        total_resultados_element = soup.find('span', class_='ui-search-search-result__quantity-results')
        total_resultados_text = total_resultados_element.text.strip()
        total_resultados = int(re.search(r'\d+', total_resultados_text.replace('.', '')).group())
        return total_resultados
    except Exception as e:
        print(f"Error al obtener el total de resultados: {e}")
        return 0

def seleccionar_localidad():
    localidades = [
        "Brasil", "BsAs GBA Norte", "BsAs GBA Sur", "BsAs Costa Atlantica", "BsAs Oeste", 
        "Buenos Aires Interior", "Capital Federal", "Chubut", "Cordoba", "Corrientes", 
        "Chaco", "Entre Rios", "La rioja", "Mendoza", "Misiones", "Neuquen", 
        "Rio Negro", "Salta", "San Juan", "San Luis", "Santa Fe", "Tucuman", 
        "Uruguay", "USA"
    ]
    
    print("Seleccione la localidad:")
    for i, localidad in enumerate(localidades, 1):
        print(f"{i}. {localidad}")
    
    while True:
        try:
            seleccion = int(input("Ingrese el número correspondiente a la localidad: "))
            if 1 <= seleccion <= len(localidades):
                return localidades[seleccion - 1]
            else:
                print("Número inválido. Por favor, intente nuevamente.")
        except ValueError:
            print("Entrada inválida. Por favor, ingrese un número.")

def normalize_string(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).replace('ñ', 'n')

def format_localidad(localidad):
    localidad = normalize_string(localidad)
    return localidad.lower().replace(' ', '-')

def format_barrios(barrios):
    barrios = normalize_string(barrios)
    barrios_list = [b.strip() for b in barrios.split(',')]
    barrios_list.sort()
    return '-o-'.join(barrios_list).replace(' ', '-')

def build_url(localidad, barrios, min_rooms, max_rooms, min_price, max_price, min_age, max_age, offset=None):
    base_url = "https://inmuebles.mercadolibre.com.ar/departamentos/venta/apto-credito/"
    filters = f"{min_rooms}-ambientes/{localidad}/{barrios}/departamentos"
    if offset:
        filters += f"_Desde_{offset}"
    filters += f"_PriceRange_{min_price}USD-{max_price}USD_NoIndex_True_PROPERTY*AGE_{min_age}-{max_age}#applied_filter_id%3DPROPERTY_AGE%26applied_filter_name%3DAntig%C3%BCedad%26applied_filter_order%3D14%26applied_value_id%3D{min_age}-{max_age}%26applied_value_name%3D{min_age}-{max_age}%26applied_value_order%3D6%26applied_value_results%3DUNKNOWN_RESULTS%26is_custom%3Dtrue"
    return base_url + filters

if __name__ == '__main__':
    localidad = seleccionar_localidad()
    localidad_formateada = format_localidad(localidad)
    print(f"Localidad seleccionada y formateada: {localidad_formateada}")
    
    barrios = input("Ingrese los barrios separados por comas (,): ")
    barrios_formateados = format_barrios(barrios)
    print(f"Barrios formateados: {barrios_formateados}")
    
    min_rooms = int(input("Ingrese el número mínimo de habitaciones: "))
    max_rooms = int(input("Ingrese el número máximo de habitaciones: "))
    min_price = int(input("Ingrese el precio mínimo en USD: "))
    max_price = int(input("Ingrese el precio máximo en USD: "))
    min_age = int(input("Ingrese la antigüedad mínima: "))
    max_age = int(input("Ingrese la antigüedad máxima: "))

    encabezados = {
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/71.0.3578.80 Chrome/71.0.3578.80 Safari/537.36"
    }

    # Construir la URL inicial para obtener el total de resultados
    url_inicial = build_url(localidad_formateada, barrios_formateados, min_rooms, max_rooms, min_price, max_price, min_age, max_age)
    total_results = obtener_total_resultados(url_inicial, encabezados)
    print(f"Total de resultados encontrados: {total_results}")

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
    #total_results = 95  # Ajusta este valor según el total de resultados esperados

    while offset < total_results:
        url = build_url(localidad_formateada, barrios_formateados, min_rooms, max_rooms, min_price, max_price, min_age, max_age, offset if offset else None)
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
            titulo_element = producto_html.find('a', class_='ui-search-item__group__element ui-search-link')
            titulo = titulo_element.text.strip() if titulo_element else 'N/A'
            titulos.append(titulo)

            # Precio
            precio_element = producto_html.find('span', class_='price-tag-fraction')
            precio = precio_element.text.strip() if precio_element else 'N/A'
            precios.append(precio)

            # Dirección
            direccion_element = producto_html.find('span', class_='ui-search-item__group__element ui-search-item__location')
            direccion = direccion_element.text.strip() if direccion_element else 'N/A'
            direcciones.append(direccion)

            # Barrio
            barrio_element = producto_html.find('span', class_='ui-search-item__group__element ui-search-item__location')
            barrio = barrio_element.text.strip() if barrio_element else 'N/A'
            barrios.append(barrio)

            # Ciudad
            ciudad_element = producto_html.find('span', class_='ui-search-item__group__element ui-search-item__location')
            ciudad = ciudad_element.text.strip() if ciudad_element else 'N/A'
            ciudades.append(ciudad)

            # Link
            link_element = producto_html.find('a', class_='ui-search-item__group__element ui-search-link')
            link = link_element['href'] if link_element else 'N/A'
            links.append(link)

            # Ambientes
            ambiente_element = producto_html.find('li', class_='ui-search-card-attributes__attribute')
            ambiente = ambiente_element.text.strip() if ambiente_element else 'N/A'
            ambientes.append(ambiente)

            # Baños
            bano_element = producto_html.find('li', class_='ui-search-card-attributes__attribute')
            bano = bano_element.text.strip() if bano_element else 'N/A'
            banios.append(bano)

            # Metros cuadrados
            metros_cuadrado_element = producto_html.find('li', class_='ui-search-card-attributes__attribute')
            metros_cuadrado = metros_cuadrado_element.text.strip() if metros_cuadrado_element else 'N/A'
            metros_cuadrados.append(metros_cuadrado)

            # Antigüedad
            antiguedad_element = producto_html.find('li', class_='ui-search-card-attributes__attribute')
            antiguedad = antiguedad_element.text.strip() if antiguedad_element else 'N/A'
            antiguedades.append(antiguedad)

        offset += results_per_page

    # Crear un DataFrame con los datos extraídos
    df = pd.DataFrame({
        'Titulo': titulos,
        'Precio': precios,
        'Direccion': direcciones,
        'Barrio': barrios,
        'Ciudad': ciudades,
        'Link': links,
        'Ambientes': ambientes,
        'Baños': banios,
        'Metros Cuadrados': metros_cuadrados,
        'Antigüedad': antiguedades
    })

    # Guardar el DataFrame en un archivo CSV
    df.to_csv('resultados_inmuebles.csv', index=False)
    print("Datos guardados en 'resultados_inmuebles.csv'")