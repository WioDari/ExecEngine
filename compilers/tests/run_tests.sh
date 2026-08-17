#!/usr/bin/env bash
set -u

read_properties() {
    local properties_file="$1"
    NAME=""
    VERSIONS=""
    SOURCE_FILE=""
    COMPILED_FILE=""
    COMPILE_CMD=""
    RUN_CMD=""

    while IFS="=" read -r key value; do
        value="${value%\"}"
        value="${value#\"}"
        case "$key" in
            NAME) NAME="$value" ;;
            VERSIONS) VERSIONS="$value" ;;
            SOURCE_FILE) SOURCE_FILE="$value" ;;
            COMPILED_FILE) COMPILED_FILE="$value" ;;
            COMPILE_CMD) COMPILE_CMD="$value" ;;
            RUN_CMD) RUN_CMD="$value" ;;
        esac
    done < "$properties_file"
}

expand_value() {
    local value="$1"
    local version="$2"
    local major="${version%%.*}"

    value="${value//\$\{VERSION%%.*\}/$major}"
    value="${value//\$VERSION/$version}"
    value="${value//\$SOURCE_FILE/$SOURCE_FILE}"
    value="${value//\$COMPILED_FILE/$COMPILED_FILE}"
    value="${value//\$args/}"
    value="${value//\?\//}"
    printf '%s' "$value"
}

run_test() {
    local dir="$1"
    local version="$2"
    local compile_cmd
    local run_cmd

    compile_cmd="$(expand_value "$COMPILE_CMD" "$version")"
    run_cmd="$(expand_value "$RUN_CMD" "$version")"

    printf 'Running test for %s\n' "${NAME//\$VERSION/$version}"
    (
        cd "$dir"
        if [[ -n "$compile_cmd" ]] && ! eval "$compile_cmd"; then
            return 1
        fi
        eval "$run_cmd"
    )
}

main() {
    local script_dir
    local base_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    base_dir="${1:-$script_dir}"
    local failed=0

    while IFS= read -r -d '' properties_file; do
        local dir
        dir="$(dirname "$properties_file")"
        read_properties "$properties_file"

        for version in $VERSIONS; do
            if ! run_test "$dir" "$version"; then
                printf 'FAILED: %s (v%s)\n' "$NAME" "$version" >&2
                failed=1
            fi
        done
        printf '\n'
    done < <(find "$base_dir" -mindepth 2 -maxdepth 2 -type f -name properties -print0 | sort -z)

    return "$failed"
}

main "$@"
