import asyncio
import logging
from app.db.mongodb import db_client, get_db
from app.schemas.content import ClientIndustryCreate, ClientCategoryCreate
from app.crud.content import create_client_industry, create_client_category, get_client_industries, get_client_categories, delete_client_industry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_grouped_partners")

async def seed():
    logger.info("Initializing database connection...")
    db_client.connect_db()
    db = get_db()
    
    def get_attr(obj, attr):
        if hasattr(obj, attr):
            return getattr(obj, attr)
        elif isinstance(obj, dict):
            return obj.get(attr)
        return None

    # First, let's delete the old "Global Partners" or "Turnpike Global Partners" if it exists to clean up
    industries = await get_client_industries(db, skip=0, limit=100)
    for i in industries:
        name = get_attr(i, 'name')
        if name in ["Global Partners", "Turnpike Global Partners"]:
            logger.info(f"Removing old industry {name}")
            # we don't have a reliable delete function exposed here easily, let's just drop it via motor
            await db.client_industries.delete_one({"name": name})
            await db.client_categories.delete_many({"category": name})

    categories_data = [
        {
            "name": "Technology & Communication",
            "icon": "Globe",
            "clients": [
                {"name": "Agilent", "img": "https://icon.horse/icon/agilent.com"},
                {"name": "Infor", "img": "https://icon.horse/icon/infor.com"},
                {"name": "Telekom", "img": "https://icon.horse/icon/telekom.com"},
                {"name": "ABB", "img": "https://icon.horse/icon/abb.com"}
            ]
        },
        {
            "name": "Insurance",
            "icon": "Shield",
            "clients": [
                {"name": "Security", "img": "https://ui-avatars.com/api/?name=Security&background=e2e8f0&color=475569&size=128"},
                {"name": "Kaiser", "img": "https://icon.horse/icon/kaiserpermanente.org"},
                {"name": "American National", "img": "https://icon.horse/icon/americannational.com"}
            ]
        },
        {
            "name": "Financial Services",
            "icon": "Landmark",
            "clients": [
                {"name": "Security America", "img": "https://ui-avatars.com/api/?name=Security+America&background=e2e8f0&color=475569&size=128"},
                {"name": "KeyBank", "img": "https://icon.horse/icon/key.com"},
                {"name": "Flaster", "img": "https://icon.horse/icon/flastergreenberg.com"},
                {"name": "Citi", "img": "https://icon.horse/icon/citi.com"},
                {"name": "Savings Bank", "img": "https://ui-avatars.com/api/?name=Savings+Bank&background=e2e8f0&color=475569&size=128"},
                {"name": "IBD", "img": "https://icon.horse/icon/investors.com"}
            ]
        },
        {
            "name": "Distribution & Retail",
            "icon": "ShoppingCart",
            "clients": [
                {"name": "BD", "img": "https://icon.horse/icon/bd.com"},
                {"name": "3M", "img": "https://icon.horse/icon/3m.com"},
                {"name": "Plexus", "img": "https://icon.horse/icon/plexus.com"}
            ]
        },
        {
            "name": "Travel & Transportation",
            "icon": "Plane",
            "clients": [
                {"name": "Truck", "img": "https://ui-avatars.com/api/?name=Truck&background=e2e8f0&color=475569&size=128"},
                {"name": "American Airlines", "img": "https://icon.horse/icon/aa.com"},
                {"name": "United Airlines", "img": "https://icon.horse/icon/united.com"},
                {"name": "ERA LLC", "img": "https://icon.horse/icon/era.com"}
            ]
        }
    ]

    for cat_data in categories_data:
        industry_name = cat_data["name"]
        
        industries = await get_client_industries(db, skip=0, limit=100)
        industry = next((i for i in industries if get_attr(i, 'name') == industry_name), None)
        
        if not industry:
            industry_data = ClientIndustryCreate(name=industry_name, icon=cat_data["icon"])
            await create_client_industry(db, industry_data)
            logger.info(f"Created industry: {industry_name}")
            
        cats = await get_client_categories(db, skip=0, limit=100)
        cat = next((c for c in cats if get_attr(c, 'category') == industry_name), None)
        
        if not cat:
            payload = ClientCategoryCreate(
                category=industry_name,
                cols=4,
                clients=cat_data["clients"]
            )
            await create_client_category(db, payload)
            logger.info(f"Created clients for {industry_name}.")
        else:
            from app.crud.content import update_client_category
            cat_id = get_attr(cat, 'id') or get_attr(cat, '_id')
            await update_client_category(db, str(cat_id), {"clients": cat_data["clients"], "cols": 4})
            logger.info(f"Updated clients for {industry_name}.")

    db_client.close_db()

if __name__ == "__main__":
    asyncio.run(seed())
