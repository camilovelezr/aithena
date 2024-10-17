#!/bin/bash

# Derive the tool name from the folder name
script_dir=$(dirname "$(realpath "$0")")
parent_folder=$(basename "$script_dir")
tool_name=$parent_folder

# The root of the repo
repo_root=$(git rev-parse --show-toplevel)

# Get the path to this tool from the repository root
tool_dir=$(python3 -c "import os.path; print(os.path.relpath('$script_dir', '$repo_root'))")

echo "Building docker image for tool: ${tool_name}"
echo "Tool path from root: ${tool_dir}"

# The version is read from the VERSION file
version=$(<VERSION)

# Determine the platform
ARCH=$(uname -m)

# Set the tag suffix to the architecture if it is not x86_64
ARCH_SUFFIX=-$ARCH
if [ "$ARCH_SUFFIX" == "-x86_64" ]; then
    ARCH_SUFFIX=""
fi

org=${DOCKER_ORG:-polusai}
tag="${org}/${tool_name}:${version}"
tag=$tag${ARCH_SUFFIX}

echo "Building docker image with tag: ${tag}"

# The Dockerfile and .dockerignore files are copied to the repository root before building the image
mkdir -p ${repo_root}/docker_build/${tool_dir}

# copy all necessary files to the staging directory (the common directory is a dependency for all tools)
echo "Creating staging directory ${repo_root}/docker_build/"
cd ${repo_root}/docker_build
cp ${repo_root}/.gitignore .dockerignore
cp -r ${repo_root}/${tool_dir}/* ${tool_dir}

# --BEGIN CUSTOMIZATION add all project dependencies.--
cp -r ${repo_root}/common .
cp -r ${repo_root}/jobs/oaipmh-client jobs/
# --END CUSTOMIZATION--

# build the docker image
build_cmd="build . -f ${tool_dir}/Dockerfile -t ${tag} --build-arg TOOL_DIR=${tool_dir}"
echo "build docker image : $build_cmd"
docker $build_cmd

# clean up staging directory
cd ${cur_dir}
echo "deleting staging directory ${repo_root}/docker_build/"
rm -rf ${repo_root}/docker_build/
