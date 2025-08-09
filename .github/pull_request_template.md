# Pull Request

## 📋 Description
<!-- Provide a clear and concise description of what this PR does -->

### Changes Made
<!-- List the main changes in this PR -->
- [ ] 
- [ ] 
- [ ] 

### Related Issues
<!-- Link to related issues using "Fixes #123" or "Closes #123" -->
- Fixes #
- Related to #

## 🔍 Type of Change
<!-- Mark the type of change this PR represents -->

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🔧 Refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] 🔒 Security fix
- [ ] 🚀 CI/CD changes
- [ ] 🧪 Tests
- [ ] 📦 Dependencies update

## 🧪 Testing
<!-- Describe the tests that you ran to verify your changes -->

### Test Coverage
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated  
- [ ] Manual testing completed
- [ ] Performance testing completed (if applicable)

### Test Results
<!-- Provide evidence that tests pass -->
```bash
# Paste test results or link to CI run
```

## 📸 Screenshots/Videos
<!-- If applicable, add screenshots or videos to help explain your changes -->

| Before | After |
|--------|--------|
| <!-- Screenshot --> | <!-- Screenshot --> |

## 🔒 Security Checklist
<!-- For security-related changes -->

- [ ] No sensitive data exposed in logs
- [ ] Authentication/authorization properly implemented
- [ ] Input validation added where needed
- [ ] Security headers configured (if applicable)
- [ ] Secrets properly managed
- [ ] Dependencies scanned for vulnerabilities

## 📦 Package/Component Impact
<!-- Check all packages/components affected by this PR -->

- [ ] **MCP Server** (`packages/mcp-server/`)
- [ ] **Dashboard API** (`packages/dashboard-api/`)  
- [ ] **Database** (`packages/database/`)
- [ ] **Shared** (`packages/shared/`)
- [ ] **Docker Configuration** (`docker/`)
- [ ] **CI/CD Workflows** (`.github/workflows/`)
- [ ] **Documentation** (`docs/`)
- [ ] **Scripts** (`scripts/`)

## 🚀 Deployment Considerations

### Database Changes
- [ ] Database migrations included
- [ ] Migrations tested on development environment
- [ ] Data migration strategy documented (if applicable)
- [ ] Rollback plan documented

### Environment Changes
- [ ] New environment variables documented
- [ ] Configuration changes documented
- [ ] Secrets/credentials updated (if needed)

### Infrastructure Changes
- [ ] Docker image changes documented
- [ ] Service dependencies updated
- [ ] Resource requirements changes noted

## ✅ Pre-Submission Checklist

### Code Quality
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Code is properly documented
- [ ] Complex logic has comments explaining the reasoning
- [ ] No debugging code or commented-out code left

### Testing & Validation
- [ ] All tests pass locally
- [ ] New code has appropriate test coverage (aim for >80%)
- [ ] Manual testing completed for affected functionality
- [ ] Error handling tested
- [ ] Edge cases considered and tested

### Documentation
- [ ] Code changes are documented
- [ ] API documentation updated (if applicable)
- [ ] README updated (if applicable)  
- [ ] Changelog entry added (for significant changes)

### Dependencies & Compatibility
- [ ] New dependencies are justified and documented
- [ ] Backward compatibility maintained (or breaking changes documented)
- [ ] Python version compatibility verified
- [ ] No unnecessary dependencies added

### Security & Performance
- [ ] Security implications considered
- [ ] Performance impact assessed
- [ ] No sensitive information in commit history
- [ ] Logging appropriate (not too verbose, not too sparse)

## 👥 Reviewers
<!-- Tag specific people or teams that should review this PR -->

**Required Reviewers:**
- @backend-team (for backend changes)
- @devops-team (for infrastructure/CI changes)
- @security-team (for security-related changes)
- @database-team (for database changes)

**Optional Reviewers:**
- @technical-writers (for documentation changes)
- @performance-team (for performance-related changes)

## 📝 Additional Notes
<!-- Any additional information that reviewers should know -->

### Migration Guide
<!-- If this includes breaking changes, provide migration instructions -->

### Known Issues
<!-- List any known issues or limitations with this PR -->

### Future Work
<!-- List any related work that should be done in future PRs -->

---

## 🤖 Automated Checks
<!-- This section will be populated by CI/CD -->

The following checks will run automatically:

- ✅ **Lint & Format**: Code style and formatting
- ✅ **Tests**: Unit and integration test suite  
- ✅ **Security**: Dependency and code security scan
- ✅ **Build**: Package building and Docker images
- ✅ **Performance**: Performance impact assessment (if applicable)

---

**By submitting this PR, I confirm that:**

- [ ] I have read and followed the contributing guidelines
- [ ] This PR is ready for review (not a draft)
- [ ] I have tested my changes thoroughly
- [ ] I am prepared to address reviewer feedback promptly