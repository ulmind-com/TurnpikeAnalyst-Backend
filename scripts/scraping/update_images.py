import re

file_path = r'c:\turnpike\frontend\turnpike-insight-suite-main\src\content\services-dynamic-data.ts'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

image_map = {
    'aerospace-defense': '/images/hero_aerospace_1786220842957.png',
    'insurance': '/images/hero_insurance_1786220854416.png',
    'professional-services': '/images/hero_professional_1786220868325.png',
    'public-sector': '/images/hero_public_sector_1786220879240.png',
    'education': '/images/hero_education_1786220893121.png',
    'life-sciences-pharma': '/images/hero_life_sciences_1786220903658.png',
    'medical-devices': '/images/hero_medical_devices_1786220914143.png',
    'industrial-process-manufacturing': '/images/hero_manufacturing_1786220927949.png',
    'engineering-construction-operations': '/images/hero_construction_1786220943552.png',
    'natural-resources': '/images/hero_natural_resources_1786220953861.png',
    'oil-gas': '/images/hero_oil_gas_1786220964588.png',
    'utilities': '/images/hero_utilities_1786220979156.png',
    'consumer-packaged-goods': '/images/hero_cpg_1786220991475.png'
}

def replace_hero(match):
    key = match.group(1)
    if key in image_map:
        return f'"{key}": {{\n    heroImage: "{image_map[key]}",'
    else:
        # use unsplash placeholder
        query = key.replace('-', ' ')
        url = f'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&q=80&w=1000' # using a generic abstract green unsplash as fallback so it doesn\'t 404
        return f'"{key}": {{\n    heroImage: "{url}",'

new_content = re.sub(r'"([a-zA-Z0-9\-]+)"\s*:\s*\{\s*heroImage\s*:\s*"[^"]+",', replace_hero, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Done replacing images.")
