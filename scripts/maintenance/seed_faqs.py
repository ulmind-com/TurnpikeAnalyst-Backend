import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
# Connection details come from configuration, never hardcoded: these are
# one-off maintenance scripts and they live in a public repository.
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings

async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client.get_database("turnpike_analyst")
    
    faqs = [
        {
            "question": "What Is ECM (Enterprise Content Management)?",
            "answer": "ECM, or Enterprise Content Management, organizes, stores, and manages an organization's documents, facilitating efficient collaboration and content control"
        },
        {
            "question": "How Does ECM Improve Workflow?",
            "answer": "ECM streamlines processes, automates tasks, and ensures easy access to information, enhancing overall efficiency and productivity within an organization."
        },
        {
            "question": "What Security Features Does ECM Offer?",
            "answer": "ECM provides robust security protocols, including access controls, encryption, and audit trails, safeguarding sensitive business information from unauthorized access or data breaches."
        },
        {
            "question": "Can ECM Integrate With Existing Systems?",
            "answer": "Yes, ECM systems are designed to integrate seamlessly with various existing applications, ensuring a smooth transition and compatibility with an organization's current technology infrastructure."
        },
        {
            "question": "How Does ECM Support Compliance?",
            "answer": "ECM assists in compliance by enforcing document retention policies, tracking changes, and providing audit trails, ensuring adherence to regulatory requirements and industry standards."
        },
        {
            "question": "What Is The Role Of Metadata In ECM?",
            "answer": "Metadata in ECM categorizes and tags content, making it easily searchable and retrievable. It enhances organization and accessibility of documents within the system."
        },
        {
            "question": "Can ECM Be Accessed Remotely?",
            "answer": "Yes, ECM systems often offer remote access capabilities, allowing users to retrieve, edit, and collaborate on documents from anywhere with an internet connection."
        },
        {
            "question": "How Scalable Is An ECM Solution?",
            "answer": "ECM solutions are scalable and can grow with your organization. They accommodate increased data and user volumes, ensuring long-term flexibility and adaptability."
        }
    ]
    
    # clear existing FAQs just in case there are some garbage records
    await db.faqs.delete_many({})
    
    # insert
    await db.faqs.insert_many(faqs)
    print("inserted faqs")

if __name__ == "__main__":
    asyncio.run(main())
