"""
Scraper de Prueba - ArtStation Jobs
Proyecto: Sistema de Búsqueda Indie/Outsourcing
Autor: Cristian Meza Venegas
Fecha: Diciembre 2024

Objetivo: Verificar viabilidad técnica de scraping en ArtStation
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import sys


def test_connection():
    """Prueba 1: Verificar que podemos conectarnos"""
    print("\n" + "="*60)
    print("PRUEBA 1: Conexión a ArtStation")
    print("="*60)

    url = "https://www.artstation.com/jobs/all"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        print(f"→ Intentando conexión a: {url}")
        response = requests.get(url, headers=headers, timeout=15)

        print(f"✓ Status Code: {response.status_code}")
        print(f"✓ Content-Type: {response.headers.get('Content-Type')}")
        print(f"✓ Tamaño respuesta: {len(response.text)} caracteres")

        if response.status_code == 200:
            print("\n✅ CONEXIÓN EXITOSA")
            return response
        else:
            print(f"\n❌ ERROR: Código {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\n❌ ERROR DE CONEXIÓN: {e}")
        return None


def test_html_structure(response):
    """Prueba 2: Analizar estructura HTML"""
    print("\n" + "="*60)
    print("PRUEBA 2: Análisis de Estructura HTML")
    print("="*60)

    soup = BeautifulSoup(response.text, 'html.parser')
    print("✓ HTML parseado correctamente con BeautifulSoup")

    # Guardar HTML para análisis manual
    html_file = '../../research/platform_tests/artstation_sample.html'
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(response.text)
    print(f"✓ HTML guardado en: {html_file}")

    # Buscar posibles contenedores de trabajos
    print("\n→ Buscando posibles contenedores de trabajos...")

    # Estrategia: buscar múltiples patrones comunes
    possible_containers = [
        soup.find_all('div', class_='job'),
        soup.find_all('article'),
        soup.find_all('div', {'data-job': True}),
        soup.find_all('li', class_=lambda x: x and 'job' in x.lower()),
    ]

    for i, containers in enumerate(possible_containers):
        if containers:
            print(f"  ✓ Patrón {i+1}: Encontrados {len(containers)} elementos")
        else:
            print(f"  ✗ Patrón {i+1}: No encontrado")

    # IMPORTANTE: Aquí deberás ajustar los selectores según la estructura real
    print("\n⚠️  ACCIÓN REQUERIDA:")
    print("    1. Abre el archivo artstation_sample.html")
    print("    2. Busca la estructura de los trabajos")
    print("    3. Identifica los selectores CSS correctos")
    print("    4. Actualiza este script con los selectores reales")

    return soup


def test_data_extraction(soup):
    """Prueba 3: Extraer datos de prueba"""
    print("\n" + "="*60)
    print("PRUEBA 3: Extracción de Datos")
    print("="*60)

    # PLACEHOLDER - Deberás actualizar estos selectores
    print("⚠️  USANDO SELECTORES PLACEHOLDER - DEBES ACTUALIZARLOS")

    # Intenta varios patrones comunes
    job_containers = (
            soup.find_all('div', class_='job-listing') or
            soup.find_all('article', class_='job') or
            soup.find_all('li', class_='job-item')
    )

    if not job_containers:
        print("❌ No se encontraron trabajos con selectores placeholder")
        print("   → Revisa artstation_sample.html para identificar selectores correctos")
        return False

    print(f"✓ Encontrados {len(job_containers)} trabajos potenciales")

    # Intentar extraer primer trabajo
    if job_containers:
        first_job = job_containers[0]

        # Extraer todos los textos como fallback
        all_text = first_job.get_text(separator=' | ', strip=True)

        test_result = {
            'platform': 'ArtStation',
            'raw_text': all_text[:500],  # Primeros 500 caracteres
            'html_snippet': str(first_job)[:500],
            'timestamp': datetime.now().isoformat(),
            'status': 'MANUAL_REVIEW_NEEDED'
        }

        # Guardar resultado
        result_file = '../../research/platform_tests/artstation_test_result.json'
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(test_result, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Resultado guardado en: {result_file}")
        print(f"\n→ Texto extraído (preview):")
        print(f"   {all_text[:200]}...")

        return True

    return False


def main():
    """Función principal"""
    print("\n" + "="*60)
    print("SCRAPER DE PRUEBA - ARTSTATION JOBS")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Objetivo: Validar viabilidad técnica")
    print("="*60)

    # Ejecutar pruebas en secuencia
    response = test_connection()

    if not response:
        print("\n❌ FALLÓ: No se pudo conectar a ArtStation")
        sys.exit(1)

    soup = test_html_structure(response)
    success = test_data_extraction(soup)

    # Resumen final
    print("\n" + "="*60)
    print("RESUMEN DE PRUEBA")
    print("="*60)

    if success:
        print("✅ Prueba PARCIALMENTE EXITOSA")
        print("\n📋 PRÓXIMOS PASOS:")
        print("   1. Revisa artstation_sample.html")
        print("   2. Identifica selectores CSS correctos")
        print("   3. Actualiza función test_data_extraction()")
        print("   4. Ejecuta script nuevamente")
    else:
        print("⚠️  Prueba REQUIERE AJUSTES")
        print("\n📋 ACCIONES:")
        print("   1. Analiza artstation_sample.html manualmente")
        print("   2. Busca patrones de estructura de trabajos")
        print("   3. Actualiza selectores en el código")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
```

5. **Ctrl+S** para guardar

---

## 🎯 PASO 7: EJECUTAR PRIMER SCRAPER

### **7.1 Configurar Run Configuration en IntelliJ**

1. **Click derecho** en `test_artstation.py`
2. **Run 'test_artstation'**

O bien:

1. **Run → Edit Configurations**
2. **+ (Add) → Python**
3. Configurar:
- **Name:** Test ArtStation Scraper
- **Script path:** [Seleccionar test_artstation.py]
- **Working directory:** [raíz del proyecto]
- **Python interpreter:** Seleccionar el venv del proyecto
4. **OK**
5. **Run → Run 'Test ArtStation Scraper'**

### **7.2 Resultados esperados**

En la consola de IntelliJ deberías ver:
```
============================================================
SCRAPER DE PRUEBA - ARTSTATION JOBS
============================================================
Fecha: 2024-12-09 15:30:00
Objetivo: Validar viabilidad técnica
============================================================

============================================================
PRUEBA 1: Conexión a ArtStation
============================================================
→ Intentando conexión a: https://www.artstation.com/jobs
✓ Status Code: 200
✓ Content-Type: text/html; charset=utf-8
✓ Tamaño respuesta: 125000 caracteres

✅ CONEXIÓN EXITOSA

============================================================
PRUEBA 2: Análisis de Estructura HTML
============================================================
✓ HTML parseado correctamente con BeautifulSoup
✓ HTML guardado en: ../../research/platform_tests/artstation_sample.html
...