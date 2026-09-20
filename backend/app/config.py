"""Configuración central del backend.

Todas las credenciales y parámetros sensibles provienen de variables de
entorno (nunca se escriben en el código fuente). Ver `.env.example`.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Parámetros de la aplicación leídos desde el entorno."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Aplicación
    app_name: str = "Energy Monitor"
    app_version: str = "1.0.0"
    environment: str = "production"

    # Base de datos
    database_url: str = "postgresql+psycopg2://energy:cambia_esta_clave_local@localhost:5432/energy_monitor"

    # API
    cors_origins: str = "*"  # Lista separada por comas, o "*" para red local
    max_csv_size_mb: float = 10.0  # Límite razonable de tamaño de CSV

    # Assets reemplazables (logo del PDF, etc.)
    assets_dir: str = "./assets"
    default_device_image: str = "default-device.png"

    # Moneda / localización (MVP: COP, Colombia)
    currency: str = "COP"

    @property
    def cors_origins_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def max_csv_size_bytes(self) -> int:
        return int(self.max_csv_size_mb * 1024 * 1024)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
