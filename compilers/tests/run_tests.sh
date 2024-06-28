#!/bin/bash
read_properties() {
    local properties_file="$1"
    while IFS="=" read -r key value; do
        case "$key" in
            NAME) NAME="${value//\"/}" ;;
            VERSIONS) VERSIONS="${value//\"/}" ;;
            SOURCE_FILE) SOURCE_FILE="${value//\"/}" ;;
            COMPILED_FILE) COMPILED_FILE="${value//\"/}" ;;
            COMPILE_CMD) COMPILE_CMD="${value//\"/}" ;;
            RUN_CMD) RUN_CMD="${value//\"/}" ;;
        esac
    done < "$properties_file"
}

run_test() {
    local version="$1"
    local compile_cmd="$2"
    local run_cmd="$3"
    
    if [[ -n "$compile_cmd" ]]; then
        eval "${COMPILE_CMD//\{VERSION\}/$version}" || { printf "Compilation failed! \n"; }
    fi
    eval "${RUN_CMD//\{VERSION\}/$version}" || { printf "Execution failed! \n"; }
}

main() {
    local base_dir="."

    for dir in $(find "$base_dir" -type d); do
        local properties_file="${dir}/properties"
        if [[ -f "$properties_file" ]]; then
            read_properties "$properties_file"
        
            for version in $VERSIONS; do
            	printf "Running test for $NAME (v$version) \n"
                local compile_cmd="${COMPILE_CMD//\{VERSION\}/$version}"
                local run_cmd="${RUN_CMD//\{VERSION\}/$version}"
                run_test "$version" "$compile_cmd" "$run_cmd"
            done
            
            printf "\n"
        fi
    done
}

main
