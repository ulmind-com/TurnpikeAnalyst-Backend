import asyncio
import logging
from app.db.mongodb import db_client, get_db
from app.schemas.content import ClientIndustryCreate, ClientCategoryCreate
from app.crud.content import create_client_industry, create_client_category, get_client_industries, get_client_categories

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_global_partners")

async def seed():
    logger.info("Initializing database connection...")
    db_client.connect_db()
    db = get_db()
    
    # 1. Create Industry
    industry_name = "Global Partners"
    industries = await get_client_industries(db, skip=0, limit=100)
    
    # Handle dict vs object access safely
    def get_attr(obj, attr):
        if hasattr(obj, attr):
            return getattr(obj, attr)
        elif isinstance(obj, dict):
            return obj.get(attr)
        return None

    industry = next((i for i in industries if get_attr(i, 'name') == industry_name), None)
    
    if not industry:
        industry_data = ClientIndustryCreate(name=industry_name, icon="Globe")
        industry = await create_client_industry(db, industry_data)
        logger.info(f"Created industry: {industry_name}")
    else:
        logger.info(f"Industry '{industry_name}' already exists.")
        
    # 2. Create Clients Category
    clients = [
        {"name": "Agilent", "img": "https://icon.horse/icon/agilent.com"},
        {"name": "Infor", "img": "https://icon.horse/icon/infor.com"},
        {"name": "Telekom", "img": "https://icon.horse/icon/telekom.com"},
        {"name": "ABB", "img": "https://icon.horse/icon/abb.com"},
        {"name": "Kaiser Permanente", "img": "https://icon.horse/icon/kaiserpermanente.org"},
        {"name": "American National", "img": "https://icon.horse/icon/americannational.com"},
        {"name": "KeyBank", "img": "https://icon.horse/icon/key.com"},
        {"name": "Flaster", "img": "https://icon.horse/icon/flastergreenberg.com"},
        {"name": "Citi", "img": "https://icon.horse/icon/citi.com"},
        {"name": "IBD", "img": "https://icon.horse/icon/investors.com"},
        {"name": "BD", "img": "https://icon.horse/icon/bd.com"},
        {"name": "3M", "img": "https://icon.horse/icon/3m.com"},
        {"name": "Plexus", "img": "https://icon.horse/icon/plexus.com"},
        {"name": "American Airlines", "img": "https://icon.horse/icon/aa.com"},
        {"name": "United Airlines", "img": "https://icon.horse/icon/united.com"},
        {"name": "ERA LLC", "img": "https://icon.horse/icon/era.com"}
    ]
    
    cats = await get_client_categories(db, skip=0, limit=100)
    cat = next((c for c in cats if get_attr(c, 'category') == industry_name), None)
    
    if not cat:
        payload = ClientCategoryCreate(
            category=industry_name,
            cols=4,
            clients=clients
        )
        await create_client_category(db, payload)
        logger.info("Created clients for Global Partners.")
    else:
        # Update existing
        from app.crud.content import update_client_category
        cat_id = get_attr(cat, 'id') or get_attr(cat, '_id')
        await update_client_category(db, str(cat_id), {"clients": clients, "cols": 4})
        logger.info("Updated clients for Global Partners.")

    db_client.close_db()

if __name__ == "__main__":
    asyncio.run(seed())
