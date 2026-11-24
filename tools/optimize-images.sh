#!/usr/bin/env bash
set -euo pipefail

# Optimize images in a directory using the given optimizer.
# -ca = convert all
# -fd = force delete original images (if converting from png to jpg)
optimize_images() {
    uv tool run --from optimize-images optimize-images "$@"
}

if [ "$#" -eq 0 ]; then
    optimize_images docs/assets -ca -fd
    exit 0
fi

target_dirs=()
while IFS= read -r image_dir; do
    target_dirs+=("$image_dir")
done < <(
    for image_path in "$@"; do
        if [ -e "$image_path" ]; then
            dirname "$image_path"
        fi
    done | sort -u
)

for image_dir in "${target_dirs[@]}"; do
    optimize_images "$image_dir" -ca -fd
done
