# Useful Git Commands

## Repository Analysis and Maintenance

### Size and Content Analysis
```bash
# Show repository size and number of objects
git count-objects -v

# Find the largest objects in your repository
git verify-pack -v .git/objects/pack/pack-*.idx | sort -k 3 -n | tail -5
```

### Repository Health
```bash
# Check repository integrity
git fsck

# Aggressively clean and optimize the repository
git gc --aggressive
```

### Configuration and Remote Management
```bash
# Show all git configuration settings
git config --list

# Remove a remote
git remote remove origin

# Add a remote (SSH)
git remote add origin git@github.com:user/repo.git

# Add a remote (HTTPS)
git remote add origin https://github.com/user/repo.git
```

### File Tracking
```bash
# Show all tracked files
git ls-tree -r HEAD --name-only

# Remove files from git tracking but keep them locally
git rm --cached <file>
```

### History Cleaning
```bash
# Remove files from entire git history
git filter-repo --path-glob 'pattern' --invert-paths
```

## Common Use Cases

### Cleaning Large Files from Repository
1. Check repository size: `git count-objects -v`
2. Find large files: `git verify-pack -v .git/objects/pack/pack-*.idx | sort -k 3 -n | tail -5`
3. Clean history: `git filter-repo --path-glob 'pattern' --invert-paths`
4. Optimize: `git gc --aggressive`

### Setting Up New Remote
1. Remove old remote: `git remote remove origin`
2. Add new remote: `git remote add origin <url>`
3. Push with tracking: `git push -u origin master`

### Troubleshooting
1. Check repository health: `git fsck`
2. View configuration: `git config --list`
3. List tracked files: `git ls-tree -r HEAD --name-only` 