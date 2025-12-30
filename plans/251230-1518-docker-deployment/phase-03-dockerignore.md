# Phase 03: Dockerignore Configuration

## Context Links
- [Main Plan](./plan.md)
- [Phase 01: Dockerfile](./phase-01-dockerfile-creation.md)

## Overview
- **Priority**: P2
- **Status**: Pending
- **Effort**: 15m

Create .dockerignore file to exclude unnecessary files from Docker build context, reducing build time and image size.

## Key Insights

### Docker Build Context
- Docker sends entire context directory to daemon
- Large contexts slow down builds
- Unnecessary files increase image size
- .dockerignore works like .gitignore

### Files to Exclude
- Git metadata (.git/)
- Python cache (__pycache__, *.pyc)
- Virtual environments (venv/, .venv/)
- Development files (.env, *.local.*)
- Documentation (README.md, docs/)
- Test files (tests/, pytest cache)
- CI/CD configs (.github/)
- IDE configs (.vscode/, .idea/)
- Build artifacts (*.log, *.pid)
- Plan files (plans/, ai_docs/)

## Requirements

### Functional
- Exclude version control files
- Exclude Python cache files
- Exclude virtual environments
- Exclude environment files with secrets
- Exclude test files
- Exclude documentation
- Exclude development configs

### Non-Functional
- Reduce build context size by 80%+
- Speed up build time
- Prevent secret leakage
- Keep Docker images clean

## Architecture

### .dockerignore Structure
```
# Version Control
.git/
.gitignore

# Python
__pycache__/
*.py[cod]
venv/

# Environment
.env
.env.*

# Development
.vscode/
.idea/
tests/

# Documentation
README.md
docs/
plans/

# CI/CD
.github/
```

## Related Code Files

### Files to Create
- `.dockerignore` (root directory)

## Implementation Steps

### 1. Create .dockerignore File

Create file at project root: `.dockerignore`

```
# Version Control
.git
.gitignore
.gitattributes

# Python
__pycache__
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# Virtual Environments
venv/
.venv/
env/
ENV/

# Environment Variables
.env
.env.local
.env.*.local
*.env

# IDE & Editors
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Testing
tests/
test_*.py
*_test.py
.pytest_cache/
.coverage
htmlcov/
.tox/

# Documentation
README.md
README.*.md
docs/
*.md
!requirements.txt

# CI/CD
.github/
.gitlab-ci.yml
.travis.yml
Jenkinsfile

# Docker
Dockerfile*
docker-compose*.yml
.dockerignore

# Plans & AI Docs
plans/
ai_docs/
.claude/

# Logs & Databases
*.log
*.sql
*.sqlite
*.db

# OS
.DS_Store
Thumbs.db

# Misc
*.bak
*.tmp
*.temp
.cache/
```

### 2. Verify .dockerignore

```bash
# Check what files are included in build context
docker build --no-cache -t test-context . 2>&1 | grep "Sending build context"

# Compare before and after adding .dockerignore
# Before: May show large context (e.g., 50MB)
# After: Should show smaller context (e.g., 5MB)
```

### 3. Test Build Optimization

```bash
# Build with .dockerignore
time docker build -t paypal-api:test .

# Verify build context size reduced
# Verify no unnecessary files in image
docker run --rm paypal-api:test ls -la /app
```

## Todo List

- [ ] Create .dockerignore in project root
- [ ] Add .git and version control exclusions
- [ ] Add Python cache exclusions (__pycache__, *.pyc)
- [ ] Add virtual environment exclusions (venv/, .venv/)
- [ ] Add .env and environment file exclusions
- [ ] Add IDE config exclusions (.vscode/, .idea/)
- [ ] Add test file exclusions (tests/, .pytest_cache/)
- [ ] Add documentation exclusions (README.md, docs/)
- [ ] Add CI/CD config exclusions (.github/)
- [ ] Add plan/AI doc exclusions (plans/, .claude/)
- [ ] Add log and database exclusions
- [ ] Add Docker file exclusions (docker-compose.yml, etc.)
- [ ] Test build context size before/after
- [ ] Verify build time improvement
- [ ] Verify no secrets in image

## Success Criteria

- .dockerignore file created successfully
- Build context size reduced by 80%+
- Build time improved (measurable)
- No .env files in final image
- No test files in final image
- No .git directory in final image
- Only app/ and static/ directories in image
- requirements.txt still included (not ignored)

## Risk Assessment

### Potential Issues
1. **Over-exclusion**: Accidentally exclude needed files
   - Mitigation: Test build thoroughly, verify app runs
2. **Under-exclusion**: Still include unnecessary files
   - Mitigation: Review image contents, add more exclusions
3. **Requirements.txt excluded**: Build fails
   - Mitigation: Use !requirements.txt to force include

### Mitigation Strategies
- Test build after creating .dockerignore
- Verify application runs correctly in container
- Check image size before/after
- Inspect image contents to verify exclusions

## Security Considerations

### Secret Protection
- Ensure .env files excluded
- Exclude any files with credentials
- Exclude private keys
- Exclude sensitive configs

### Verification
```bash
# Check for secrets in image
docker run --rm paypal-api:latest find /app -name ".env*"
# Should return nothing

# Verify no .git directory
docker run --rm paypal-api:latest ls -la /app/.git
# Should show "No such file or directory"
```

## Next Steps

After .dockerignore creation:
1. Verify build context optimization
2. Update documentation with build metrics
3. Proceed to README documentation phase

## Unresolved Questions

None - .dockerignore is straightforward configuration.
