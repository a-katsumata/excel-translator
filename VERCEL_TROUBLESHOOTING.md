# Vercel Deployment Troubleshooting Guide

## Step-by-Step Debugging Process

### 1. Check Vercel Logs
```bash
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Check logs
vercel logs --follow

# Check specific function logs
vercel logs https://your-deployment-url.vercel.app/api/index
```

### 2. Test Simplified Version First
If main deployment fails, test with backup version:

1. Rename `api/index.py` to `api/index_complex.py`
2. Rename `api/backup_index.py` to `api/index.py`
3. Deploy and test basic functionality
4. If successful, gradually add complexity back

### 3. Common Error Messages and Solutions

#### Error: "All checks have failed"
**Likely Causes:**
- Import errors
- Missing dependencies
- Incorrect handler function
- Environment variables not set

**Solutions:**
1. Check function logs in Vercel dashboard
2. Verify all dependencies in requirements.txt
3. Test imports locally with `python -c "import module_name"`
4. Check environment variables in Vercel dashboard

#### Error: "ModuleNotFoundError"
**Solutions:**
1. Ensure all modules are in requirements.txt
2. Check Python path configuration
3. Verify file structure matches imports
4. Use absolute imports where possible

#### Error: "Application not found"
**Solutions:**
1. Verify handler function is correct:
   ```python
   def handler(environ, start_response):
       return app(environ, start_response)
   ```
2. Check vercel.json configuration
3. Ensure Flask app is named 'app'

#### Error: "Timeout"
**Solutions:**
1. Increase maxDuration in vercel.json
2. Optimize slow operations
3. Add caching for repeated operations
4. Check for infinite loops

### 4. Local Testing Before Deployment

#### Test with Vercel CLI
```bash
# Install dependencies
pip install -r requirements.txt

# Test locally with Vercel
vercel dev

# Check health endpoint
curl http://localhost:3000/health
```

#### Test Python imports
```bash
# From project root
python -c "
import sys
sys.path.append('.')
from excel_translator import ExcelTranslator
from utils.validators import ValidationError
print('All imports successful')
"
```

### 5. Vercel.json Configuration Options

#### Option 1: Current Configuration
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "50mb",
        "runtime": "python3.9"
      }
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ],
  "functions": {
    "api/index.py": {
      "maxDuration": 60
    }
  }
}
```

#### Option 2: Simplified Configuration
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

#### Option 3: With Environment Variables
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ],
  "env": {
    "DEEPL_API_KEY": "@deepl_api_key",
    "SECRET_KEY": "@secret_key"
  }
}
```

### 6. Environment Variables Setup

#### In Vercel Dashboard:
1. Go to Project Settings
2. Environment Variables tab
3. Add:
   - `DEEPL_API_KEY` = your-api-key
   - `SECRET_KEY` = your-secret-key

#### Using Vercel CLI:
```bash
# Add environment variables
vercel env add DEEPL_API_KEY
vercel env add SECRET_KEY

# List environment variables
vercel env ls
```

### 7. File Structure Requirements

```
project/
├── api/
│   ├── index.py          # Main Flask app
│   └── backup_index.py   # Simplified version for testing
├── utils/
│   ├── __init__.py       # Package initialization
│   ├── validators.py     # Validation functions
│   └── response_helpers.py # Response utilities
├── templates/
│   ├── index.html        # Upload form
│   └── result.html       # Results page
├── excel_translator.py   # Main translation logic
├── requirements.txt      # Python dependencies
├── vercel.json          # Vercel configuration
└── .env.example         # Environment variables template
```

### 8. Debugging Deployment Issues

#### Check Build Logs
1. Go to Vercel dashboard
2. Click on your project
3. Go to "Deployments" tab
4. Click on failed deployment
5. Check "Build Logs" and "Function Logs"

#### Common Build Issues:
- Python version mismatch
- Missing dependencies
- File path issues
- Import errors

#### Runtime Issues:
- Environment variable problems
- Handler function errors
- Module import failures
- Timeout issues

### 9. Testing Checklist

Before deploying:
- [ ] All imports work locally
- [ ] Environment variables are set
- [ ] Handler function is correct
- [ ] Requirements.txt is complete
- [ ] Vercel.json is valid
- [ ] File structure is correct
- [ ] Health endpoint works

After deploying:
- [ ] Health check responds: `/health`
- [ ] Main page loads: `/`
- [ ] API endpoints work: `/api/translate`
- [ ] File uploads work
- [ ] Error handling works

### 10. Alternative Deployment Strategies

If Vercel continues to fail:

#### Option 1: Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy to Railway
railway login
railway deploy
```

#### Option 2: Render
1. Connect GitHub repo to Render
2. Configure build command: `pip install -r requirements.txt`
3. Configure start command: `python app.py`

#### Option 3: Heroku
```bash
# Install Heroku CLI
npm install -g heroku

# Create Heroku app
heroku create your-app-name

# Add Python buildpack
heroku buildpacks:set heroku/python

# Deploy
git push heroku main
```

### 11. Performance Optimization

#### Reduce Cold Start Times:
1. Minimize dependencies
2. Use caching
3. Optimize imports
4. Reduce function size

#### Memory Management:
1. Use generators for large files
2. Clear variables after use
3. Implement file streaming
4. Monitor memory usage

### 12. Security Considerations

#### Environment Variables:
- Never commit API keys
- Use Vercel's environment variables
- Rotate keys regularly
- Use different keys for different environments

#### File Uploads:
- Validate file types
- Check file sizes
- Scan for malware
- Use secure filenames

### 13. Next Steps

1. **If deployment still fails**: Use the backup_index.py version
2. **If imports fail**: Check all paths and dependencies
3. **If performance issues**: Optimize code and use caching
4. **If security concerns**: Implement proper validation and rate limiting

### 14. Getting Help

#### Vercel Support Resources:
- [Vercel Documentation](https://vercel.com/docs)
- [Vercel Community](https://github.com/vercel/vercel/discussions)
- [Python Runtime Documentation](https://vercel.com/docs/functions/serverless-functions/runtimes/python)

#### Common Support Topics:
- Function timeouts
- Import errors
- Memory limits
- Build failures