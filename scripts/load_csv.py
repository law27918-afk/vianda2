"""
Carga (o actualiza) supermercados_unificado.csv en la tabla store_products.
Correr cada vez que se actualicen los precios:

    python scripts/load_csv.py

Usa upsert por (store, sku): si el producto ya existe, actualiza precio y fecha;
si no existe, lo inserta.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.models import StoreProduct

COLUMN_MAP = {
    "supermercado": "store",
    "sku": "sku",
    "categoria": "category",
    "nombre": "name",
    "precio": "price",
    "moneda": "currency",
    "imagen": "image_url",
    "url_producto": "product_url",
    "fecha_extraccion": "scraped_at",
}


def main(csv_path: str = None):
    Base.metadata.create_all(bind=engine)

    path = csv_path or settings.csv_path
    df = pd.read_csv(path)
    df = df.rename(columns=COLUMN_MAP)
    df["sku"] = df["sku"].astype(str)
    df["scraped_at"] = pd.to_datetime(df["scraped_at"], errors="coerce")
    df = df.drop_duplicates(subset=["store", "sku"], keep="last")

    records = df[list(COLUMN_MAP.values())].to_dict(orient="records")

    db = SessionLocal()
    try:
        for i in range(0, len(records), 500):
            batch = records[i : i + 500]
            stmt = insert(StoreProduct).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["store", "sku"],
                set_={
                    "name": stmt.excluded.name,
                    "category": stmt.excluded.category,
                    "price": stmt.excluded.price,
                    "currency": stmt.excluded.currency,
                    "image_url": stmt.excluded.image_url,
                    "product_url": stmt.excluded.product_url,
                    "scraped_at": stmt.excluded.scraped_at,
                },
            )
            db.execute(stmt)
        db.commit()
        print(f"Cargados/actualizados {len(records)} productos.")
    finally:
        db.close()


if __name__ == "__main__":
    csv_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(csv_arg)
