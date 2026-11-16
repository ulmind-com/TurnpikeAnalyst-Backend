import re
import random
import json
from datetime import datetime, timedelta

titles = [
    'Unlocking AI Innovation with IBM watsonx: A Comprehensive Guide',
    'Tungsten Automation (Kofax)',
    'Hyland Nuxeo',
    'CMOD To FileNet P8 Migration',
    'OpenText Upgrade',
    'FileNet Content Manager',
    'Migrating IBM FileNet P8 to Hyland OnBase: A Comprehensive Guide',
    'Opentext Documentum installation and configuration',
    'Unlocking Business Potential How ICC for SAP Can Transform Your Operations',
    'IBM Datacap',
    'Overview of Documentum Migration',
    'Salesforce: The Ultimate CRM Powerhouse Transforming Modern Business',
    'Document Capture Automation Proposal using Datacap',
    'IBM Image Services',
    'OpenText Documentum integration',
    'Hyland OnBase',
    'IBM FileNet P8 5.2.1 on Windows 2012 to IBM FileNet 5.5.9 on Windows 2019/2022',
    'Adobe',
    'Datacap Install and Configuration on AWS',
    'BlackLine',
    'IBM FileNet P8 Migration, Extract Content and Properties from IBM FileNet P8 v 5.2.1 and Ingest into Target System',
    'DATACAP The Battle That Will Change Your Business Forever',
    'Maximizing ROI with Enterprise Content Management',
    'The Future of Cloud Migration Strategy',
    'Automating Workflows in the Healthcare Sector',
    'Security Best Practices for Document Management',
    'Scaling Digital Transformation Initiatives'
]

def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

def generate_blog(index, title):
    slug = slugify(title)
    date_obj = datetime.now() - timedelta(days=random.randint(1, 365))
    date_str = date_obj.strftime('%B %d, %Y')
    keywords = ['business', 'technology', 'server', 'cloud', 'data', 'office', 'computer', 'network']
    kw = random.choice(keywords)
    image_url = f'https://source.unsplash.com/800x600/?{kw}&sig={index}'
    
    excerpt = f"Dive into our detailed analysis of {title}. In this comprehensive guide, we explore the best practices, strategies, and methodologies to help your enterprise succeed in today's digital landscape. Read more to discover expert insights."
    
    content = f"# {title}\n\n## Introduction\n\nWelcome to our comprehensive deep dive into **{title}**. As organizations continue to modernize their IT infrastructure, staying ahead of the curve is more critical than ever. This guide covers everything you need to know.\n\n## Key Challenges\n\nEnterprises face numerous hurdles when dealing with legacy systems, compliance, and scalability. By strategically approaching the problem, organizations can streamline operations and reduce overhead.\n\n## Strategic Solutions\n\nImplementing modern platforms requires careful planning. We recommend a phased rollout, prioritizing data integrity, and conducting extensive user acceptance testing (UAT). Partnering with experienced consultants can mitigate risks.\n\n## Conclusion\n\nIn conclusion, mastering {title} empowers your organization to leverage data effectively, optimize workflows, and maintain a competitive edge. Contact Turnpike Analyst for tailored consulting services."

    return f"""  {{
    "title": {json.dumps(title)},
    "slug": "{slug}",
    "date": "{date_str}",
    "author": "admin",
    "excerpt": {json.dumps(excerpt)},
    "image_url": "{image_url}",
    "content": {json.dumps(content)}
  }}"""

blogs_str = ",\n".join([generate_blog(i, t) for i, t in enumerate(titles)])
new_blogs_data = f"BLOGS_DATA = [\n{blogs_str}\n]"

with open('c:/turnpike/backend/scripts/seed_content.py', 'r') as f:
    content = f.read()

# We will split the file around `BLOGS_DATA = [` or whatever broken syntax is there.
# Everything before line 84 is good. Everything after line 318 is good.
# Wait, I don't know exactly what line numbers are now, but I can use a more robust split.

head = content.split('BLOGS_DATA = [')[0]
tail = content.split('async def seed():')[1]

new_content = head + new_blogs_data + "\n\nasync def seed():" + tail

with open('c:/turnpike/backend/scripts/seed_content.py', 'w') as f:
    f.write(new_content)

print(f"Rebuilt seed_content.py with {len(titles)} blogs.")
