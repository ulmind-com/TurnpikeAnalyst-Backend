import os

def replace_in_file(src, dst, replacements):
    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created {dst}")

def main():
    src_form = 'src/features/services/service-form-dialog.tsx'
    dst_form = 'src/features/industries/industry-form-dialog.tsx'
    
    replacements_form = {
        'service': 'industry',
        'Service': 'Industry',
        'SERVICES': 'INDUSTRIES',
        'sub_service_type': 'short_description', # Hack to remove sub_service_type
        'sub_industry_type': 'short_description',
        'useCreateIndustry': 'useCreateIndustry',
        'useUpdateIndustry': 'useUpdateIndustry',
        'SUB_SERVICE_TYPES': 'PARENT_CATEGORIES',
    }
    # Actually it's better to manually write the form since it's tricky to regex sub_service_type out.
    pass

if __name__ == '__main__':
    main()
