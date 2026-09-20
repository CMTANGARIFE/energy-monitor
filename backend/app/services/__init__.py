"""Capa de servicios: lógica de negocio de Energy Monitor.

Módulos:
- csv_parser:  parseo y validación de archivos CSV de consumo
- importer:    vista previa e importación UPSERT transaccional
- rates:       reglas de tarifas (solapamientos, vigencia)
- costs:       cálculo de costos día a día según tarifa aplicable
- stats:       estadísticas y agregaciones para dashboard e informes
- pdf_report:  generación de informes PDF profesionales
- backup:      respaldo de la base de datos
- formatting:  formato de números/fechas estilo Colombia
"""
