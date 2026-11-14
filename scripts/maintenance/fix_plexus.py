import asyncio
import logging
from app.db.mongodb import db_client, get_db
from app.crud.content import get_client_categories, update_client_category

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fix_plexus")

async def fix():
    db_client.connect_db()
    db = get_db()
    
    cats = await get_client_categories(db, skip=0, limit=100)
    for cat in cats:
        cat_dict = cat.model_dump() if hasattr(cat, 'model_dump') else dict(cat)
        clients = cat_dict.get('clients', [])
        
        updated = False
        for c in clients:
            if c['name'] == 'Plexus':
                c['img'] = 'https://icon.horse/icon/plexusworldwide.com'
                updated = True
                logger.info("Found Plexus, updating image URL.")
                
        if updated:
            cat_id = cat.id if hasattr(cat, 'id') else cat_dict['_id']
            await update_client_category(db, str(cat_id), {"clients": clients})
            logger.info(f"Updated category {cat_dict.get('category')} with fixed Plexus.")

    db_client.close_db()

if __name__ == "__main__":
    asyncio.run(fix())
