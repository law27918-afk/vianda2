import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ---------- Enums ----------

class GoalType(str, enum.Enum):
    deficit = "deficit"
    mantenimiento = "mantenimiento"
    superavit = "superavit"


class MealType(str, enum.Enum):
    desayuno = "desayuno"
    almuerzo = "almuerzo"
    cena = "cena"
    snack = "snack"


class DietaryRuleType(str, enum.Enum):
    alergia = "alergia"
    restriccion = "restriccion"
    preferencia = "preferencia"


class RecipeSource(str, enum.Enum):
    manual = "manual"
    importada = "importada"


# ---------- Households ----------

class Household(Base):
    __tablename__ = "households"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    budget = Column(Float, nullable=True)
    num_people = Column(Integer, nullable=False, default=2)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("Member", back_populates="household", cascade="all, delete-orphan")
    dietary_rules = relationship("DietaryRule", back_populates="household", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="household", cascade="all, delete-orphan")


class Member(Base):
    __tablename__ = "members"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    household_id = Column(UUID(as_uuid=False), ForeignKey("households.id"), nullable=False)
    name = Column(String, nullable=False)
    goal = Column(Enum(GoalType), nullable=True)
    is_personal_mode = Column(Boolean, default=False)

    household = relationship("Household", back_populates="members")


class DietaryRule(Base):
    __tablename__ = "household_dietary_rules"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    household_id = Column(UUID(as_uuid=False), ForeignKey("households.id"), nullable=False)
    rule_type = Column(Enum(DietaryRuleType), nullable=False)
    value = Column(String, nullable=False)
    is_hard = Column(Boolean, default=True)

    household = relationship("Household", back_populates="dietary_rules")


# ---------- Catálogo de supermercados (desde el CSV) ----------

class StoreProduct(Base):
    __tablename__ = "store_products"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    store = Column(String, nullable=False, index=True)
    sku = Column(String, nullable=False, index=True)
    category = Column(String, nullable=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    product_url = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    scraped_at = Column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("store", "sku", name="uq_store_sku"),)


# ---------- Ingredientes propios ----------

class Ingredient(Base):
    """
    category: categoría amplia (ej: "cereales", "lacteos") — informativa.
    exclude_keywords: palabras separadas por coma que, si aparecen en el nombre
        de un producto del catálogo, lo EXCLUYEN de los resultados de búsqueda
        para este ingrediente. Ej: el ingrediente "Arroz blanco" puede tener
        exclude_keywords="con leche,dulce,postre" para que al buscar productos
        no aparezcan mezclados con "Arroz con leche".
    """
    __tablename__ = "ingredients"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False, unique=True)
    default_unit = Column(String, nullable=False, default="g")
    category = Column(String, nullable=True)
    exclude_keywords = Column(String, nullable=True)

    product_links = relationship("IngredientProductLink", back_populates="ingredient", cascade="all, delete-orphan")


class IngredientProductLink(Base):
    __tablename__ = "ingredient_product_links"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    ingredient_id = Column(UUID(as_uuid=False), ForeignKey("ingredients.id"), nullable=False)
    store_product_id = Column(UUID(as_uuid=False), ForeignKey("store_products.id"), nullable=False)
    is_preferred = Column(Boolean, default=False)

    ingredient = relationship("Ingredient", back_populates="product_links")
    store_product = relationship("StoreProduct")


# ---------- Recetas ----------

class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    source = Column(Enum(RecipeSource), default=RecipeSource.manual)
    source_url = Column(Text, nullable=True)
    servings = Column(Integer, nullable=False, default=4)
    instructions = Column(Text, nullable=True)
    prep_time_minutes = Column(Integer, nullable=True)
    image_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    recipe_id = Column(UUID(as_uuid=False), ForeignKey("recipes.id"), nullable=False)
    raw_text = Column(String, nullable=False)
    quantity = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    ingredient_id = Column(UUID(as_uuid=False), ForeignKey("ingredients.id"), nullable=True)

    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("Ingredient")


# ---------- Planificación ----------

class Plan(Base):
    """
    Antes era "WeeklyPlan" con solo week_start (siempre 7 días fijos).
    Ahora es un rango de fechas arbitrario: start_date .. end_date,
    para poder planificar 3 días, 1 semana, 2 semanas, lo que sea.
    """
    __tablename__ = "plans"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    household_id = Column(UUID(as_uuid=False), ForeignKey("households.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    household = relationship("Household", back_populates="plans")
    meals = relationship("PlanMeal", back_populates="plan", cascade="all, delete-orphan")


class PlanMeal(Base):
    """
    member_id: si es null, la comida es para todo el hogar (lo normal para
        desayuno/almuerzo/cena). Si tiene valor, es una comida individual
        (ej: la merienda de un solo integrante).
    is_required: desayuno/almuerzo/cena son obligatorios por defecto;
        snack es opcional. Es solo informativo para la UI.
    """
    __tablename__ = "plan_meals"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    plan_id = Column(UUID(as_uuid=False), ForeignKey("plans.id"), nullable=False)
    recipe_id = Column(UUID(as_uuid=False), ForeignKey("recipes.id"), nullable=False)
    day = Column(Date, nullable=False)
    meal_type = Column(Enum(MealType), nullable=False)
    member_id = Column(UUID(as_uuid=False), ForeignKey("members.id"), nullable=True)
    is_required = Column(Boolean, default=True)
    servings_override = Column(Integer, nullable=True)

    plan = relationship("Plan", back_populates="meals")
    recipe = relationship("Recipe")
    member = relationship("Member")


# ---------- Lista de compras (siempre derivada del plan) ----------

class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    plan_id = Column(UUID(as_uuid=False), ForeignKey("plans.id"), nullable=False)
    ingredient_id = Column(UUID(as_uuid=False), ForeignKey("ingredients.id"), nullable=False)
    quantity_needed = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    cheapest_store_product_id = Column(UUID(as_uuid=False), ForeignKey("store_products.id"), nullable=True)
    estimated_cost = Column(Float, nullable=True)
    is_checked = Column(Boolean, default=False)

    plan = relationship("Plan")
    ingredient = relationship("Ingredient")
    cheapest_store_product = relationship("StoreProduct")
