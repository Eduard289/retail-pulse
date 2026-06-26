# Retail Pulse – Analítica de Ventas en Tiempo Real

Retail Pulse es una demo interactiva que conecta con la API de Square (sandbox) para obtener datos de ventas y analizar el rendimiento de la fuerza de ventas en tiempo real.

----------------------------------------------------------------

## Características

- Conexión directa con Square – sin necesidad de exportar CSV manualmente.
- Dashboard interactivo con KPIs clave (Ventas, VPH, AOV, Conversión, etc.).
- Gráfico de VPH por vendedor con línea de media.
- Dictamen automático de cada vendedor (cuadrante y recomendación).
- Descarga de informe en PDF con los resultados.

----------------------------------------------------------------

## Tecnologías utilizadas

- Streamlit – interfaz interactiva (frontend/backend en Python).
- Square API – obtención de datos de ventas (sandbox).
- Pandas / NumPy – procesamiento y transformación de datos.
- Plotly – gráficos interactivos.
- ReportLab – generación de informes PDF.

----------------------------------------------------------------

## Instalación local

1. Clona el repositorio:
   git clone https://github.com/tu-usuario/retail-pulse.git
   cd retail-pulse

2. Instala las dependencias:
   pip install -r requirements.txt

3. Configura el token de Square (opcional):
   - Crea un archivo .env en la raíz
   - Añade tu token de sandbox:
     SQUARE_ACCESS_TOKEN=tu_token_de_sandbox

4. Ejecuta la aplicación:
   streamlit run app.py

----------------------------------------------------------------

## Configuración del token de Square

Para obtener un token de sandbox gratuito:

1. Ve a Square Developer Dashboard: https://developer.squareup.com/apps
2. Crea una aplicación (o usa una existente).
3. En "Credentials", copia el "Sandbox Access Token".
4. Úsalo como variable de entorno o en los secretos de Streamlit Cloud.

----------------------------------------------------------------

## Demo en vivo

Prueba la demo aquí: https://retail-pulse.streamlit.app

(Actualiza este enlace cuando tengas la URL real de Streamlit Cloud)

----------------------------------------------------------------

## Ejemplo de uso

1. Selecciona un rango de fechas (ej. últimos 7 días).
2. Haz clic en "Sincronizar con Square".
3. Visualiza los KPIs, gráficos y dictamen de vendedores.
4. Descarga el informe en PDF con un clic.

----------------------------------------------------------------

## Licencia

Este proyecto está bajo la licencia GNU General Public License v3.0.
Consulta el archivo LICENSE para más detalles.

----------------------------------------------------------------

## Agradecimientos

- Square por proporcionar una API tan completa y un sandbox gratuito.
- Streamlit por hacer que desarrollar dashboards sea tan rápido y divertido.

----------------------------------------------------------------

Desarrollado con ❤️ por [Jose Luis Asenjo]
