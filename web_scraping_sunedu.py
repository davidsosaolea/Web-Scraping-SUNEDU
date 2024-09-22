import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pytesseract
import cv2
import time
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from concurrent.futures import ThreadPoolExecutor, as_completed

# Lee el DataFrame desde un archivo
df = pd.read_csv('data_trujillo/resultados_medicina_trujillo.csv')  # Ajusta la ruta a tu archivo

# Crear la nueva columna 'Nombre completo'
df['Nombre completo'] = df['Apellido Paterno'] + ' ' + df['Apellido Materno'] + ' ' + df['Nombres']

# Lista para almacenar los resultados
resultados = []

def obtener_datos(driver):
    try:
        # Verificar si se muestra el resultado
        WebDriverWait(driver, 40).until(
            EC.visibility_of_element_located((By.XPATH, "//h4[text()='Resultado']"))
        )

        # Intentar obtener los datos de la primera fila
        try:
            nombre = driver.find_element(By.XPATH, "/html/body/div[1]/div/div/div/div/div[1]/div[3]/div/div[1]/div[2]/div/table/tbody[1]/tr[1]/td[1]").text
            titulo = driver.find_element(By.XPATH, "/html/body/div[1]/div/div/div/div/div[1]/div[3]/div/div[1]/div[2]/div/table/tbody[1]/tr[1]/td[2]").text
            institucion = driver.find_element(By.XPATH, "/html/body/div[1]/div/div/div/div/div[1]/div[3]/div/div[1]/div[2]/div/table/tbody[1]/tr[1]/td[3]").text
            print('primera fila')
        except NoSuchElementException:
            # Si la primera fila no existe, intentar con la segunda fila
            nombre = driver.find_element(By.XPATH, "/html/body/div[1]/div/div/div/div/div[1]/div[3]/div/div[1]/div[2]/div/table/tbody[1]/tr[2]/td[1]").text
            titulo = driver.find_element(By.XPATH, "/html/body/div[1]/div/div/div/div/div[1]/div[3]/div/div[1]/div[2]/div/table/tbody[1]/tr[2]/td[2]").text
            institucion = driver.find_element(By.XPATH, "/html/body/div[1]/div/div/div/div/div[1]/div[3]/div/div[1]/div[2]/div/table/tbody[2]/tr[1]/td[3]").text
            print('segunda fila')

        return nombre, titulo, institucion

    except (NoSuchElementException, TimeoutException):
        print("No se encontraron los datos o el resultado no se cargó correctamente.")
        return None, None, None

def ejecutar_proceso(nombre_completo, numero):
    # Configura las opciones del navegador
    chrome_options = Options()
    chrome_options.add_argument("--headless")  
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--disable-gpu")

    # Configura el servicio de ChromeDriver con la ruta a tu ChromeDriver
    service = Service('C:/Users/Usuario/Documents/sunedu/chromedriver-win64/chromedriver.exe')

    # Inicializa el navegador con las opciones configuradas
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Maximizar la ventana del navegador
        driver.maximize_window()

        # Abre la página web
        driver.get("https://enlinea.sunedu.gob.pe/")

        # Esperar a que el botón del menú esté visible en la pantalla y hacer clic
        menu_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[2]/div[3]/div/div[2]/div/a/div"))
        )
        menu_button.click()

        # Cambiar al iframe usando su ID
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrmShowFormConstancias"))
        )

        # Esperar a que el campo de texto del ID 'nombre' esté listo y visible dentro del iframe
        nombre_input = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.ID, "nombre"))
        )
        
        # Esperar a que la imagen del captcha esté visible y completamente cargada
        captcha_image = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div/div/div/div[1]/div[1]/div/form/div[3]/div[2]/fieldset/span/img"))
        )

        # Verificar si el src del captcha no está vacío
        captcha_src = captcha_image.get_attribute("src")
        if not captcha_src or captcha_src == "":
            print("La imagen del captcha no se ha cargado correctamente.")
            return False

        # Asegurar que la imagen esté visible y cargada
        driver.execute_script("arguments[0].scrollIntoView();", captcha_image)

        # Guarda la imagen del captcha
        captcha_image_path = "captcha.png"
        captcha_image.screenshot(captcha_image_path)

        # Procesar la imagen con OpenCV y Tesseract para extraer el texto
        image = cv2.imread(captcha_image_path)
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, threshold_image = cv2.threshold(gray_image, 150, 255, cv2.THRESH_BINARY)
        text = pytesseract.image_to_string(threshold_image, lang='eng').strip()

        print("Texto detectado:")
        print(text)
        
        time.sleep(5)

        # Escribir el nombre completo en el campo de texto
        nombre_input.send_keys(nombre_completo)

        # Mover el cursor al campo del captcha e ingresar el texto
        captcha_input = driver.find_element(By.ID, "captcha")  
        captcha_input.send_keys(text)

        # Mover el cursor al botón buscar y hacer clic
        buscar_button = driver.find_element(By.XPATH, "/html/body/div[1]/div/div/div/div/div[1]/div[1]/div/form/div[4]/div[2]/fieldset/button[1]")  
        buscar_button.click()

        # Llamar a la función para obtener los datos
        nombre, titulo, institucion = obtener_datos(driver)

        if nombre and titulo and institucion:
            resultados.append({
                'Nombre Completo': nombre_completo,
                'Nombre': nombre,
                'Titulo': titulo,
                'Institucion': institucion
            })

            print(f"Proceso completado con éxito para {nombre_completo}.")
            return True
        else:
            print(f"No se encontraron resultados para {nombre_completo}.")
            return False

    except Exception as e:
        print(f"Error durante la ejecución para {nombre_completo}: {e}")
        return False

    finally:
        driver.quit()

# Define a function to process each row with retries
def process_row(row):
    max_attempts = 4
    nombre_completo = row['Nombre completo']
    numero = row['N']
    attempt = 0
    success = False

    while attempt < max_attempts and not success:
        print(f"Intento {attempt + 1} de {max_attempts} para {nombre_completo}")
        success = ejecutar_proceso(nombre_completo, numero)
        attempt += 1

    if not success:
        print(f"Error tras {max_attempts} intentos para {nombre_completo}, proceso terminado.")
    else:
        print(f"Proceso completado con éxito para {nombre_completo}.")

# Use ThreadPoolExecutor to parallelize the process
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(process_row, row) for _, row in df.iterrows()]

    for future in as_completed(futures):
        future.result()  # Retrieve the result to ensure exceptions are raised

# Guardar los resultados en un archivo CSV
resultados_df = pd.DataFrame(resultados)
resultados_df.to_csv('data/resultados_medicina_trujillo_2.csv', index=False)
print("Los resultados se han guardado en 'resultados_medicina_trujillo_2.csv'.")
