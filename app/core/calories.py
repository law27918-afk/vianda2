"""
Estimación APROXIMADA de calorías por ingrediente.

No es una base de datos nutricional precisa (no considera marca, preparación,
ni corte específico) — es una tabla interna de valores típicos por 100g/100ml,
pensada para dar una idea general de cuántas calorías tiene una comida
planeada, no para un conteo nutricional exacto.

Cómo funciona:
1. Se normaliza el nombre del ingrediente (minúsculas, sin tildes).
2. Se busca la palabra clave más específica que aparezca en ese nombre
   (por ejemplo "pollo" o "arroz").
3. Se convierte la cantidad + unidad de la receta a gramos/mililitros
   aproximados usando CONVERSIONES_A_GRAMOS.
4. kcal = (gramos / 100) * kcal_por_100g
"""

import unicodedata

# kcal aproximadas por 100g (o 100ml para líquidos). Valores típicos/promedio.
CALORIAS_POR_100G = {
    # proteínas
    "pollo": 165, "pechuga de pollo": 165, "muslo de pollo": 175,
    "carne de res": 250, "carne molida": 250, "res": 250,
    "cerdo": 242, "chuleta": 231, "tocino": 541, "bacon": 541,
    "pescado": 140, "atun": 132, "salmon": 208, "tilapia": 96, "camaron": 99, "camarones": 99,
    "huevo": 155, "huevos": 155,
    "jamon": 145, "salchicha": 300, "chorizo": 455, "embutido": 300,
    "queso": 350, "queso crema": 342, "mozzarella": 280,
    "tofu": 76,
    # lácteos
    "leche": 61, "yogurt": 59, "yogur": 59, "crema": 340, "mantequilla": 717, "margarina": 717,
    # granos y cereales
    "arroz": 130, "arroz blanco": 130, "arroz integral": 111,
    "pasta": 131, "espagueti": 131, "fideos": 138,
    "pan": 265, "pan integral": 247, "tortilla": 218,
    "avena": 389, "cereal": 379, "harina": 364,
    "quinoa": 120,
    # leguminosas
    "frijoles": 127, "frijol": 127, "lentejas": 116, "garbanzos": 164, "habichuelas": 127,
    # vegetales
    "papa": 77, "patata": 77, "camote": 86, "yuca": 160, "platano": 122, "platanos": 122,
    "tomate": 18, "cebolla": 40, "ajo": 149, "zanahoria": 41, "lechuga": 15,
    "brocoli": 34, "espinaca": 23, "pepino": 15, "pimiento": 20, "chile": 40,
    "aguacate": 160, "elote": 86, "maiz": 86, "calabaza": 26,
    # frutas
    "manzana": 52, "banana": 89, "naranja": 47, "limon": 29, "fresa": 32, "fresas": 32,
    "mango": 60, "piña": 50, "sandia": 30, "uva": 69, "uvas": 69,
    # grasas / condimentos
    "aceite": 884, "aceite de oliva": 884, "mayonesa": 680, "salsa": 100,
    "azucar": 387, "sal": 0, "vinagre": 18, "miel": 304,
    "chocolate": 546, "cacao": 228,
    "nuez": 654, "nueces": 654, "almendra": 579, "almendras": 579, "mani": 567,
    # otros
    "agua": 0, "caldo": 10,
}

# Conversión aproximada de unidades comunes de recetas a gramos/mililitros.
# Estas son aproximaciones generales (varían según el ingrediente real),
# pero sirven para dar un estimado razonable.
CONVERSIONES_A_GRAMOS = {
    "g": 1, "gr": 1, "gramo": 1, "gramos": 1,
    "kg": 1000, "kilo": 1000, "kilos": 1000,
    "ml": 1, "mililitro": 1, "mililitros": 1,
    "l": 1000, "litro": 1000, "litros": 1000,
    "taza": 240, "tazas": 240,
    "cda": 15, "cdas": 15, "cucharada": 15, "cucharadas": 15,
    "cdta": 5, "cdtas": 5, "cucharadita": 5, "cucharaditas": 5,
    "unidad": 50, "unidades": 50, "u": 50,  # aproximación genérica para "1 unidad" de algo
}

DEFAULT_GRAMOS_SIN_UNIDAD = 100  # si no hay unidad reconocible, se asume 1 porción ~100g


def _normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto


def _buscar_kcal_por_100g(nombre_ingrediente: str):
    nombre = _normalizar(nombre_ingrediente)
    if not nombre:
        return None

    # Prioriza coincidencias de frases más largas y específicas primero
    # (ej: "arroz blanco" antes que solo "arroz").
    candidatos = sorted(CALORIAS_POR_100G.items(), key=lambda kv: -len(kv[0]))
    for palabra_clave, kcal in candidatos:
        if palabra_clave in nombre:
            return kcal
    return None


def _cantidad_a_gramos(quantity, unit) -> float:
    if quantity is None:
        return DEFAULT_GRAMOS_SIN_UNIDAD
    unidad_norm = _normalizar(unit) if unit else None
    factor = CONVERSIONES_A_GRAMOS.get(unidad_norm, 1 if unidad_norm in ("g", "ml") else None)
    if factor is None:
        # unidad no reconocida (o vacía): asumimos que la cantidad ya es
        # razonablemente proporcional a gramos, para no perder el dato.
        factor = 1
    return quantity * factor


def estimar_kcal_ingrediente(nombre_ingrediente: str, quantity, unit) -> float | None:
    """Devuelve las kcal estimadas para esta línea de ingrediente, o None si
    no se reconoce el ingrediente."""
    kcal_por_100g = _buscar_kcal_por_100g(nombre_ingrediente)
    if kcal_por_100g is None:
        return None
    gramos = _cantidad_a_gramos(quantity, unit)
    return round((gramos / 100) * kcal_por_100g, 1)


def estimar_kcal_receta(recipe_ingredients) -> dict:
    """
    recipe_ingredients: lista de objetos con .raw_text, .quantity, .unit
    (y opcionalmente .ingredient.name si ya está vinculado, que es más preciso
    que el texto libre).

    Devuelve {"total_kcal": float|None, "ingredientes_reconocidos": int,
    "ingredientes_totales": int} — si no se reconoce ningún ingrediente,
    total_kcal es None (no se puede estimar nada).
    """
    total = 0.0
    reconocidos = 0
    totales = len(recipe_ingredients)

    for ri in recipe_ingredients:
        nombre = None
        if getattr(ri, "ingredient", None) is not None:
            nombre = ri.ingredient.name
        if not nombre:
            nombre = ri.raw_text

        kcal = estimar_kcal_ingrediente(nombre, ri.quantity, ri.unit)
        if kcal is not None:
            total += kcal
            reconocidos += 1

    return {
        "total_kcal": round(total, 0) if reconocidos > 0 else None,
        "ingredientes_reconocidos": reconocidos,
        "ingredientes_totales": totales,
    }
