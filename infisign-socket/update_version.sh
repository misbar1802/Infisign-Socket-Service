#!/usr/bin/env bash
set -e -o pipefail

# Set Git author and committer information
export GIT_AUTHOR_EMAIL="sheik@entrans.io"
export GIT_AUTHOR_NAME="infisign-socket CICD"
export GIT_COMMITTER_EMAIL="${GIT_AUTHOR_EMAIL}"
export GIT_COMMITTER_NAME="${GIT_AUTHOR_NAME}"
export GIT_USER_EMAIL="${GIT_AUTHOR_EMAIL}"
export GIT_USER_NAME="${GIT_USER_EMAIL}"

# Initialize CodeBuild environment variables
export CODEBUILD_RESOLVED_SOURCE_VERSION="${CODEBUILD_RESOLVED_SOURCE_VERSION:-$(git rev-parse HEAD)}"

echo "Setting CodeBuild variable: completed=false"

# Debugging: Print the current directory and contents
echo "Current directory: $(pwd)"
echo "Contents:"
ls -al

parent_branch=${1:-main}
if [ "$parent_branch" != "main" ] && [ "$parent_branch" != "staging" ]; then
  echo "This script can only be run on main or staging branches. Exiting."
  exit 1
fi

# Ensure the script is running inside a Git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  echo "Error: Not inside a Git repository."
  exit 128
fi

# Fetch and check out the parent branch
git fetch origin $parent_branch
git checkout $parent_branch

echo "Current branch: $parent_branch"

# Read the current version from the VERSION file
if [ ! -f VERSION ]; then
  echo "Error: VERSION file not found."
  exit 1
fi

CURRENT_VERSION=$(cat VERSION)
echo "Current version: $CURRENT_VERSION"

# Split VERSION into MAJOR and PATCH parts and increment the PATCH
MAJOR=$(echo "$CURRENT_VERSION" | cut -d '.' -f 1)
PATCH=$(echo "$CURRENT_VERSION" | cut -d '.' -f 2)

if ! [[ "$PATCH" =~ ^[0-9]+$ ]]; then
  echo "Error: Invalid version format in VERSION file. Expected numeric format like '3.0'."
  exit 1
fi

NEW_PATCH=$((PATCH + 1))
VERSION="$MAJOR.$NEW_PATCH"

echo "New version: $VERSION"
echo "$VERSION" > VERSION

# Commit the new version (but do not create a tag)
set +e +o pipefail
git add VERSION
git commit -m "Pipeline updating version to $VERSION [skip ci]"
set -e -o pipefail

# Push the updated branch
if [ ! -z "$GITHUB_TOKEN" ]; then
  git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/misbar1802/Infisign-Socket-Service.git"
fi
git push origin HEAD:$parent_branch

# Create and push a new branch for the release
RELEASE_BRANCH="infisign-socket/$VERSION"
git checkout -b $RELEASE_BRANCH
git push origin $RELEASE_BRANCH

last_commit=$(git rev-parse --short HEAD)

# Set CodeBuild variables
echo "Setting CodeBuild variable: last_commit=$last_commit"
echo "Setting CodeBuild variable: completed=true"
echo "Setting CodeBuild variable: major=$MAJOR"
echo "Setting CodeBuild variable: patch=$NEW_PATCH"
echo "Setting CodeBuild variable: version=$VERSION"
echo "Setting CodeBuild variable: repo=$(basename $(git remote get-url origin))"

# Output variables to a file to pass to CodeBuild environment
cat <<EOF > /tmp/codebuild_env
last_commit=$last_commit
completed=true
major=$MAJOR
patch=$NEW_PATCH
version=$VERSION
repo=$(basename $(git remote get-url origin))
EOF
