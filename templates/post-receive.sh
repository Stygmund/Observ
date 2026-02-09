#!/bin/bash
# Post-receive hook for Deployment Paradigm
# This hook is called by git after receiving a push

set -e

# Read stdin (old_commit new_commit ref_name)
while read oldrev newrev refname; do
    # Only deploy on main/master branch
    if [[ "$refname" == "refs/heads/main" ]] || [[ "$refname" == "refs/heads/master" ]]; then
        echo "=== Deployment Paradigm ==="
        echo "Deploying $refname: $newrev"

        # Call deployment script
        /usr/local/bin/deploy-paradigm execute "$GIT_DIR" "$newrev"

        exit_code=$?
        if [ $exit_code -eq 0 ]; then
            echo "✓ Deployment successful"
        else
            echo "❌ Deployment failed"
            exit $exit_code
        fi
    else
        echo "Skipping deployment for branch: $refname"
    fi
done
