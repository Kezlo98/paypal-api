# Phase 05: GitHub Actions CI/CD (Optional)

## Context Links
- [Main Plan](./plan.md)
- [Phase 01: Dockerfile](./phase-01-dockerfile-creation.md)
- [Phase 04: Documentation](./phase-04-documentation.md)

## Overview
- **Priority**: P3 (Optional)
- **Status**: Pending
- **Effort**: 30m

Create GitHub Actions workflow for automated Docker image building and publishing to Docker Hub on main branch commits.

## Key Insights

### CI/CD Benefits
- Automated builds on every push
- Consistent build environment
- Automated versioning (tags)
- No manual Docker Hub pushes
- Quality gates before deployment

### GitHub Actions Features
- Free for public repositories
- Docker Hub integration
- Secret management
- Multi-platform builds (optional)
- Caching for faster builds

## Requirements

### Functional
- Trigger on push to main branch
- Build Docker image
- Tag with version and latest
- Push to Docker Hub
- Use GitHub secrets for credentials
- Optional: Run tests before build

### Non-Functional
- Build time < 5 minutes
- Secure secret handling
- Clear build logs
- Failed builds block deployment

## Architecture

### Workflow Triggers
```yaml
on:
  push:
    branches: [main]
  release:
    types: [created]
```

### Workflow Steps
1. Checkout code
2. Set up Docker Buildx
3. Login to Docker Hub
4. Extract metadata (tags, labels)
5. Build and push image
6. Optional: Run tests

### Secrets Required
- `DOCKERHUB_USERNAME`: Docker Hub username
- `DOCKERHUB_TOKEN`: Docker Hub access token

## Related Code Files

### Files to Create
- `.github/workflows/docker-publish.yml`

### Files Referenced
- `Dockerfile` (built by workflow)
- `requirements.txt` (dependencies)

## Implementation Steps

### 1. Create GitHub Secrets

Before creating workflow, add secrets in GitHub:

1. Go to repository Settings → Secrets and variables → Actions
2. Add `DOCKERHUB_USERNAME` (your Docker Hub username)
3. Add `DOCKERHUB_TOKEN` (create at hub.docker.com → Account Settings → Security → New Access Token)

### 2. Create GitHub Actions Workflow

Create file: `.github/workflows/docker-publish.yml`

```yaml
name: Docker Build and Publish

on:
  push:
    branches: [main]
    tags:
      - 'v*.*.*'
  pull_request:
    branches: [main]

env:
  REGISTRY: docker.io
  IMAGE_NAME: ${{ secrets.DOCKERHUB_USERNAME }}/paypal-api

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      # Checkout repository
      - name: Checkout code
        uses: actions/checkout@v4

      # Set up Docker Buildx (for advanced builds)
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      # Login to Docker Hub
      - name: Login to Docker Hub
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      # Extract metadata (tags, labels)
      - name: Extract Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}

      # Build and push Docker image
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      # Optional: Display image digest
      - name: Image digest
        if: github.event_name != 'pull_request'
        run: echo "Image pushed with tags: ${{ steps.meta.outputs.tags }}"
```

### 3. Alternative: Simpler Workflow (Minimal Version)

For a more straightforward approach:

```yaml
name: Publish Docker Image

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and push
        run: |
          docker build -t ${{ secrets.DOCKERHUB_USERNAME }}/paypal-api:latest .
          docker push ${{ secrets.DOCKERHUB_USERNAME }}/paypal-api:latest

          # Tag with commit SHA
          docker tag ${{ secrets.DOCKERHUB_USERNAME }}/paypal-api:latest \
                     ${{ secrets.DOCKERHUB_USERNAME }}/paypal-api:${{ github.sha }}
          docker push ${{ secrets.DOCKERHUB_USERNAME }}/paypal-api:${{ github.sha }}
```

### 4. Add Tests Before Build (Optional Enhancement)

Add test job before build:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run tests
        run: |
          pytest tests/ -v

  build-and-push:
    needs: test  # Only build if tests pass
    runs-on: ubuntu-latest
    # ... rest of build job
```

### 5. Test Workflow

```bash
# Commit and push workflow file
git add .github/workflows/docker-publish.yml
git commit -m "ci: add Docker Hub publishing workflow"
git push origin main

# Monitor workflow
# Go to GitHub → Actions tab
# Watch build progress

# Verify image on Docker Hub
# Visit: https://hub.docker.com/r/yourusername/paypal-api/tags
```

## Todo List

- [ ] Create GitHub secrets (DOCKERHUB_USERNAME, DOCKERHUB_TOKEN)
- [ ] Create .github/workflows directory
- [ ] Create docker-publish.yml workflow file
- [ ] Configure workflow triggers (push to main)
- [ ] Add checkout step
- [ ] Add Docker Buildx setup
- [ ] Add Docker Hub login step
- [ ] Add metadata extraction step
- [ ] Add build and push step
- [ ] Configure caching for faster builds
- [ ] Optional: Add test job before build
- [ ] Test workflow with dummy commit
- [ ] Verify image appears on Docker Hub
- [ ] Update README with CI/CD badge
- [ ] Document workflow in README

## Success Criteria

- GitHub Actions workflow file created
- Secrets configured in GitHub
- Workflow triggers on main branch push
- Image builds successfully in CI
- Image pushed to Docker Hub with tags
- Build completes in < 5 minutes
- Failed builds don't push images
- Workflow logs clear and informative
- Optional: Tests run before build
- Optional: GitHub Actions badge in README

## Risk Assessment

### Potential Issues
1. **Missing secrets**: Workflow fails on first run
   - Mitigation: Document secret setup clearly
2. **Rate limits**: Docker Hub free tier limits
   - Mitigation: Use caching, monitor usage
3. **Build failures**: Break main branch
   - Mitigation: Test locally first, add PR checks
4. **Long build times**: Slow CI feedback
   - Mitigation: Enable build caching

### Mitigation Strategies
- Test workflow on feature branch first
- Use Docker layer caching (gha cache)
- Set up branch protection rules
- Monitor Docker Hub usage

## Security Considerations

### Secrets Management
- Never hardcode credentials in workflow
- Use GitHub secrets for all sensitive data
- Rotate Docker Hub tokens periodically
- Limit secret access with permissions

### Token Security
```yaml
# Use read-only token where possible
# Create token at: hub.docker.com → Settings → Security
# Permissions: Read, Write, Delete (for push)
```

### Workflow Permissions
```yaml
permissions:
  contents: read    # Read repository
  packages: write   # Push to registry
```

## Next Steps

After GitHub Actions setup:
1. Test workflow with commit to main
2. Verify image on Docker Hub
3. Add GitHub Actions badge to README
4. Document workflow behavior
5. Optional: Set up branch protection

### Adding GitHub Actions Badge to README

```markdown
![Docker Build](https://github.com/yourusername/paypal-api/actions/workflows/docker-publish.yml/badge.svg)
```

## Unresolved Questions

1. Should we support multi-platform builds (linux/amd64, linux/arm64)?
   - Decision: No for now, add later if needed
   - Would require setup-qemu-action
2. Should we run tests in workflow?
   - Decision: Yes, if tests exist. Good practice
3. Should we tag with version numbers automatically?
   - Decision: Yes, use semver tags on releases
4. Separate workflows for dev/staging/prod?
   - Decision: No, single workflow sufficient for now
