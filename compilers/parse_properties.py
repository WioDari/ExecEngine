import os
import json

def parse_properties(filepath):
    props = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            props[key.strip()] = value.strip().strip('"')
    return props

def expand_version_syntax(version, syntax):
    if '${VERSION%%.*}' in syntax:
        major = version.split('.')[0]
        syntax = syntax.replace('${VERSION%%.*}', major)
    syntax = syntax.replace('$VERSION', version)
    return syntax

def process_language(dir_path):
    props_file = os.path.join(dir_path, 'properties')
    if not os.path.exists(props_file):
        print(f"Skipped: properties file not found in {dir_path}")
        return []

    props = parse_properties(props_file)
    
    name_template = props.get('NAME', '')
    versions_str = props.get('VERSIONS', '')
    source_file = props.get('SOURCE_FILE', '')
    compiled_file = props.get('COMPILED_FILE', '')
    compile_cmd = props.get('COMPILE_CMD', '').strip()
    run_cmd = props.get('RUN_CMD', '').strip()

    versions = versions_str.split() if versions_str else ['']

    result = []
    for version in versions:
        name = name_template.replace('$VERSION', version) if version else name_template

        src_file = source_file
        cmp_file = compiled_file

        if '$VERSION' in src_file:
            src_file = src_file.replace('$VERSION', version)
        elif '${VERSION%%.*}' in src_file:
            major = version.split('.')[0]
            src_file = src_file.replace('${VERSION%%.*}', major)

        if '$VERSION' in cmp_file:
            cmp_file = cmp_file.replace('$VERSION', version)
        elif '${VERSION%%.*}' in cmp_file:
            major = version.split('.')[0]
            cmp_file = cmp_file.replace('${VERSION%%.*}', major)

        expanded_compile_cmd = compile_cmd
        expanded_run_cmd = run_cmd

        if expanded_compile_cmd:
            expanded_compile_cmd = expand_version_syntax(version, expanded_compile_cmd)
            expanded_compile_cmd = expanded_compile_cmd.replace('$SOURCE_FILE', src_file)
            if '$COMPILED_FILE' in expanded_compile_cmd:
                expanded_compile_cmd = expanded_compile_cmd.replace('$COMPILED_FILE', cmp_file)

        expanded_run_cmd = expand_version_syntax(version, expanded_run_cmd)
        expanded_run_cmd = expanded_run_cmd.replace('$SOURCE_FILE', src_file)
        if '$COMPILED_FILE' in expanded_run_cmd:
            expanded_run_cmd = expanded_run_cmd.replace('$COMPILED_FILE', cmp_file)

        lang_obj = {
            "NAME": name,
            "VERSION": version,
            "SOURCE_FILE": src_file,
            "COMPILED_FILE": cmp_file if cmp_file else None,
            "COMPILE_CMD": expanded_compile_cmd if expanded_compile_cmd else None,
            "RUN_CMD": expanded_run_cmd
        }
        result.append(lang_obj)
    
    return result

def main():
    tests_dir = 'tests'
    output_file = 'languages.json'

    if not os.path.exists(tests_dir):
        print(f"Error: directory '{tests_dir}' not found.")
        return
    languages = []
    for entry in os.listdir(tests_dir):
        dir_path = os.path.join(tests_dir, entry)
        if not os.path.isdir(dir_path):
            continue
        if os.path.exists(os.path.join(dir_path, '.skip')):
            print(f"Skipped: {entry} (has .skip)")
            continue
        langs = process_language(dir_path)
        languages.extend(langs)
    languages.sort(key=lambda x: x["NAME"])
    for index, lang in enumerate(languages, start=1):
        lang["id"] = index
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(languages, f, indent=2, ensure_ascii=False)
    print(f"Success: {len(languages)} language versions written to {output_file}\n")

if __name__ == '__main__':
    main()
