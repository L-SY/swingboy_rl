#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/../.." && pwd)
DDT_LAB_DIR=${1:-${DDT_LAB_DIR:-}}

if [[ -z "${DDT_LAB_DIR}" || ! -d "${DDT_LAB_DIR}/source/ddt_lab" ]]; then
  echo "Usage: $0 /path/to/DDT_Lab" >&2
  exit 2
fi

OVERLAY_DIR="${SCRIPT_DIR}/ddt_lab_overlay"
while IFS= read -r -d '' source_file; do
  relative_path=${source_file#"${OVERLAY_DIR}/"}
  target_file="${DDT_LAB_DIR}/${relative_path}"
  mkdir -p "$(dirname -- "${target_file}")"
  cp "${source_file}" "${target_file}"
done < <(
  find "${OVERLAY_DIR}" -type f ! -name '*.pyc' ! -path '*/__pycache__/*' -print0
)

DESCRIPTION_DIR="${DDT_LAB_DIR}/ddt_ros2_control/urdfs/swingboy_description/urdf"
mkdir -p "${DESCRIPTION_DIR}"
cp "${SCRIPT_DIR}/robot/robot.urdf" "${DESCRIPTION_DIR}/robot.urdf"

if [[ -e "${DESCRIPTION_DIR}/meshes" && ! -L "${DESCRIPTION_DIR}/meshes" ]]; then
  echo "Refusing to replace non-symlink mesh directory: ${DESCRIPTION_DIR}/meshes" >&2
  exit 1
fi
ln -sfn "${REPO_ROOT}/assets/meshes" "${DESCRIPTION_DIR}/meshes"

echo "Installed Swingboy DDT_Lab overlay into ${DDT_LAB_DIR}"
