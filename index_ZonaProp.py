import sys
import pandas as pd
import datetime
import os
import re
import time
from bs4 import BeautifulSoup
import cloudscraper
import unicodedata

# Funciones utilitarias
def remove_host_from_url(url):
    host_regex = r'(^https?://)(.*/)'
    return re.sub(host_regex, '', url)

def get_filename_from_datetime(base_url, extension):
    base_url_without_host = remove_host_from_url(base_url)
    return f'analisis_zonaprop/{base_url_without_host}-{datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.{extension}'

def save_df_to_csv(df, filename):
    create_root_directory(filename)
    df.to_csv(filename, index=False)

def parse_zonaprop_url(url):
    return url.replace('.html', '')

def create_root_directory(filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)

def normalize_string(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).replace('ñ', 'n')

# Clase Browser
class Browser():
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()

    def get(self, url):
        return self.scraper.get(url)

    def post(self, url, data):
        return self.scraper.post(url, data)

    def get_text(self, url):
        return self.scraper.get(url).text

# Clase Scraper
PAGE_URL_SUFFIX = '-pagina-'
HTML_EXTENSION = '.html'

class Scraper:
    def __init__(self, browser, base_url):
        self.browser = browser
        self.base_url = base_url

    def scrap_website(self):
        page_number = 1
        estates = []
        estates_scraped = 0
        estates_quantity = self.get_estates_quantity()
        common_keys = {'url', 'price_value', 'price_type', 'expenses_value', 'expenses_type', 'location', 'description', 'area', 'rooms', 'bedrooms', 'bathrooms'}
        
        while estates_quantity > estates_scraped:
            print(f'Página: {page_number}')
            page_estates = self.scrap_page(page_number)
            if page_estates is None:
                break
            for estate in page_estates:
                for key in common_keys:
                    if key not in estate:
                        estate[key] = None
            estates += page_estates
            page_number += 1
            estates_scraped = len(estates)
            time.sleep(3)
        return estates
    
    def scrap_page(self, page_number):
        if page_number == 1:
            page_url = f'{self.base_url}{HTML_EXTENSION}'
        else:
            page_url = f'{self.base_url}{PAGE_URL_SUFFIX}{page_number}{HTML_EXTENSION}'

        print(f'URL: {page_url}')

        page = self.browser.get_text(page_url)
        soup = BeautifulSoup(page, 'lxml')
        
        # Encontrar todos los contenedores de propiedades
        property_containers = soup.find_all('div', {'data-posting-type': 'PROPERTY'})
        estates = []

        # Iterar sobre cada contenedor de propiedad y extraer datos
        for property_container in property_containers:
            estate = {}
            # Extraer la URL de la propiedad
            data_to_posting = property_container.get('data-to-posting')
            if data_to_posting:
                estate['url'] = f'https://www.zonaprop.com.ar{data_to_posting}'
            else:
                estate['url'] = None
            estate['price_value'] = property_container.find('div', {'data-qa': 'POSTING_CARD_PRICE'}).text
            estate['expenses_value'] = property_container.find('div', {'data-qa': 'expensas'}).text
            estate['address'] = property_container.find('div', class_='postingLocations-module__location-address__k8Ip7').text
            estate['location'] = property_container.find('h2', {'data-qa': 'POSTING_CARD_LOCATION'}).text
            features = property_container.find_all('span', class_='postingMainFeatures-module__posting-main-features-span__ror2o')

            if len(features) > 0:
                estate['area'] = features[0].text
            if len(features) > 1:
                estate['rooms'] = features[1].text
            if len(features) > 2:
                estate['bedrooms'] = features[2].text
            if len(features) > 3:
                estate['bathrooms'] = features[3].text

            # Limpiar y convertir price_value y area
            price_value = estate['price_value'].replace('USD', '').replace('.', '').replace(',', '').strip()
            area = estate['area'].replace(' m² tot.', '').replace(',', '').strip()
            
            # Calcular precio por metro cuadrado
            try:
                estate['price_per_m2'] = float(price_value) / float(area)
            except ValueError:
                estate['price_per_m2'] = None

            estates.append(estate)
        
        return estates

    def get_estates_quantity(self):
        page_url = f'{self.base_url}{HTML_EXTENSION}'
        page = self.browser.get_text(page_url)
        soup = BeautifulSoup(page, 'lxml')
        soup.find_all('h1')[0].text

        estates_quantity = re.findall(r'\d+\.?\d+', soup.find_all('h1')[0].text)[0]

        estates_quantity = estates_quantity.replace('.', '')

        estates_quantity = int(estates_quantity)
        return estates_quantity

# Función principal
def main(url):
    base_url = parse_zonaprop_url(url)
    print(f'Ejecutando scraper para {base_url}')
    print(f'Esto puede tardar un momento...')
    browser = Browser()
    scraper = Scraper(browser, base_url)
    estates = scraper.scrap_website()
    
    # Depuración: Imprimir los datos de las propiedades
    #print(f'Número de propiedades extraídas: {len(estates)}')
    #print(f'Datos de propiedades: {estates}')
    
    # Convertir propiedades a DataFrame
    df = pd.DataFrame(estates)
    
    # Eliminar columnas vacías
    df = df.drop(columns=['expenses_type', 'price_type', 'description'], errors='ignore')
    
    # Limpiar y convertir columnas price_value y area
    df['price_value'] = df['price_value'].str.replace('USD', '').str.replace('$', '').str.replace(',', '').str.replace('.', '').astype(float)
    df['area'] = df['area'].str.extract(r'(\d+\.?\d*)').astype(float)
    
    # Calcular precio por metro cuadrado
    df['price_per_m2'] = df['price_value'] / df['area']
    
    # Guardar el DataFrame principal en CSV
    print('Scraping terminado !!!')
    print('Guardando datos en archivo csv')
    #filename = get_filename_from_datetime(base_url, 'csv')
    save_df_to_csv(df, 'analisis_zonaprop/departamentos.csv')
    #print(f'Datos guardados en {filename}')
    
    # Agrupar por ubicación y calcular el precio promedio por metro cuadrado, área promedio y cantidad de propiedades
    analisis_barrio = df.groupby('location').agg({
        'price_per_m2': 'mean',
        'area': 'mean',
        'url': 'count'
    }).rename(columns={'price_per_m2': 'Precio Promedio x m2', 'area': 'Metros Cuadrados Promedio', 'url': 'Cantidad de Departamentos'}).reset_index()
    
    # Redondear los valores a dos decimales
    analisis_barrio['Precio Promedio x m2'] = analisis_barrio['Precio Promedio x m2'].round(2)
    analisis_barrio['Metros Cuadrados Promedio'] = analisis_barrio['Metros Cuadrados Promedio'].round(2)
    
    # Guardar el DataFrame de análisis en CSV
    #analisis_barrio_filename = get_filename_from_datetime(base_url, 'analisis_barrio.csv')
    analisis_barrio.to_csv('analisis_zonaprop/analisis_por_barrio.csv', index=False)
    #print(f'Datos de análisis guardados en {analisis_barrio_filename}')
    
    # Encontrar las propiedades más caras y más baratas por ubicación
    df['price_value'] = df['price_value'].astype(float)
    mas_barato_por_barrio = df.loc[df.groupby('location')['price_value'].transform('min') == df['price_value']]
    mas_caro_por_barrio = df.loc[df.groupby('location')['price_value'].transform('max') == df['price_value']]
    
    # Combinar las propiedades más caras y más baratas en un solo DataFrame
    extremos_por_barrio = pd.concat([mas_barato_por_barrio, mas_caro_por_barrio]).drop_duplicates().sort_values(by='location')
    #extremos_por_barrio_filename = get_filename_from_datetime(base_url, 'most_expensive_and_cheapest.csv')
    extremos_por_barrio.to_csv('analisis_zonaprop/extremos_por_barrio.csv', index=False)
    #print(f'Datos de propiedades más caras y más baratas guardados en {extremos_por_barrio_filename}')
    
    print('Scraping terminado !!!')

if __name__ == '__main__':
    barrios = input("Ingrese los barrios separados por comas (,): ")
    min_rooms = int(input("Ingrese el número mínimo de habitaciones: "))
    max_rooms = int(input("Ingrese el número máximo de habitaciones: "))
    min_price = int(input("Ingrese el precio mínimo: "))
    max_price = int(input("Ingrese el precio máximo: "))
    max_age = int(input("Ingrese la antigüedad máxima de la propiedad: "))
    
    # Normalizar y formatear los barrios
    barrios = normalize_string(barrios)
    barrios = barrios.replace(' ', '').replace(',', '-')

    url = sys.argv[1] if len(sys.argv) > 1 else f'https://www.zonaprop.com.ar/departamentos-ph-venta-{barrios}-con-apto-credito-desde-{min_rooms}-hasta-{max_rooms}-ambientes-hasta-{max_age}-anos-{min_price}-{max_price}-dolar.html'
    main(url)