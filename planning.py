from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.database import get_db

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.get("/", response_model=list[schemas.IngredientOut])
def list_ingredients(db: Session = Depends(get_db)):
    return db.query(models.Ingredient).all()


@router.post("/", response_model=schemas.IngredientOut)
def create_ingredient(payload: schemas.IngredientCreate, db: Session = Depends(get_db)):
    ing = models.Ingredient(**payload.model_dump())
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return ing


@router.post("/{ingredient_id}/link/{store_product_id}")
def link_ingredient_to_product(ingredient_id: str, store_product_id: str, is_preferred: bool = False, db: Session = Depends(get_db)):
    """Vincula manualmente un ingrediente propio a un producto del catálogo de supermercados."""
    ing = db.query(models.Ingredient).get(ingredient_id)
    product = db.query(models.StoreProduct).get(store_product_id)
    if not ing or not product:
        raise HTTPException(404, "Ingrediente o producto no encontrado")
    link = models.IngredientProductLink(
        ingredient_id=ingredient_id,
        store_product_id=store_product_id,
        is_preferred=is_preferred,
    )
    db.add(link)
    db.commit()
    return {"ok": True}


@router.get("/products/search", response_model=list[schemas.StoreProductOut])
def search_store_products(q: str, db: Session = Depends(get_db)):
    """Buscar en el catálogo de supermercados para vincular a un ingrediente."""
    return (
        db.query(models.StoreProduct)
        .filter(models.StoreProduct.name.ilike(f"%{q}%"))
        .order_by(models.StoreProduct.price.asc())
        .limit(30)
        .all()
    )
