#!/bin/sh
set -eu

config_file=/run/execengine/execengine.ini
cgroup_state_file=/run/isolate/cgroup

if [ ! -r "$config_file" ]; then
    echo "ExecEngine worker configuration is not readable: $config_file" >&2
    exit 78
fi

if [ ! -s "$cgroup_state_file" ]; then
    echo "Isolate cgroup state was not initialized: $cgroup_state_file" >&2
    exit 78
fi

if ! cgroup_root="$(isolate --print-cg-root)"; then
    echo "Isolate could not resolve its delegated cgroup root" >&2
    exit 78
fi

case "$cgroup_root" in
    /sys/fs/cgroup|/sys/fs/cgroup/*) ;;
    *)
        echo "Isolate returned an unexpected cgroup root: $cgroup_root" >&2
        exit 78
        ;;
esac

for required_file in cgroup.procs cpuset.cpus cpuset.mems memory.current; do
    if [ ! -e "$cgroup_root/$required_file" ]; then
        echo "Isolate cgroup root is missing $required_file: $cgroup_root" >&2
        exit 78
    fi
done

exec /usr/bin/python3 -m app.worker.main
