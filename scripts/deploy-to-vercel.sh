#!/bin/bash
#
# Vercel Deployment Script for Biz-Retriever
# 
# Usage:
#   ./scripts/deploy-to-vercel.sh [options]
#
# Options:
#   --preview    Deploy to preview environment (default)
#   --prod       Deploy to production environment
#   --env-only   Only sync environment variables (no deployment)
#   --help       Show this help message
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="preview"
ENV_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --prod)
            ENVIRONMENT="production"
            shift
            ;;
        --preview)
            ENVIRONMENT="preview"
            shift
            ;;
        --env-only)
            ENV_ONLY=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--preview|--prod] [--env-only] [--help]"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Biz-Retriever Vercel Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo -e "${RED}Error: Vercel CLI not found${NC}"
    echo "Install with: npm install -g vercel"
    exit 1
fi

echo -e "${GREEN}✓${NC} Vercel CLI found: $(vercel --version)"

# Check if logged in
if ! vercel whoami &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} Not logged in to Vercel"
    echo "Logging in..."
    vercel login
fi

echo -e "${GREEN}✓${NC} Logged in as: $(vercel whoami)"

# Pre-deployment checks
echo ""
echo -e "${BLUE}Running pre-deployment checks...${NC}"

# Check if git is clean (warning only)
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}⚠${NC} Warning: You have uncommitted changes"
    echo "  Consider committing your changes before deploying"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if vercel.json exists
if [ ! -f "vercel.json" ]; then
    echo -e "${RED}✗${NC} vercel.json not found"
    exit 1
fi
echo -e "${GREEN}✓${NC} vercel.json found"

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}✗${NC} requirements.txt not found"
    exit 1
fi
echo -e "${GREEN}✓${NC} requirements.txt found"

# Check critical API files
CRITICAL_FILES=(
    "api/auth/login.py"
    "api/auth/register.py"
    "api/bids/list.py"
    "api/bids/matched.py"
    "api/cron/crawl-g2b.py"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}✗${NC} Critical file missing: $file"
        exit 1
    fi
done
echo -e "${GREEN}✓${NC} All critical API files present"

# Environment variable check
echo ""
echo -e "${BLUE}Checking environment variables...${NC}"

if [ ! -f ".env.vercel.template" ]; then
    echo -e "${YELLOW}⚠${NC} .env.vercel.template not found (using defaults)"
else
    echo -e "${GREEN}✓${NC} Environment template found"
fi

# Sync environment variables (if .env.production exists)
if [ -f ".env.production" ]; then
    echo -e "${YELLOW}⚠${NC} Found .env.production - Do you want to sync to Vercel?"
    echo "  This will update environment variables in Vercel Dashboard"
    read -p "Sync environment variables? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Syncing environment variables..."
        
        # Read each line and add to Vercel
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            if [[ $key =~ ^#.*$ ]] || [[ -z $key ]]; then
                continue
            fi
            
            # Remove leading/trailing whitespace
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs)
            
            # Skip if value is empty or placeholder
            if [[ -z $value ]] || [[ $value =~ ^GENERATE.*$ ]] || [[ $value =~ ^YOUR.*$ ]]; then
                echo -e "${YELLOW}⚠${NC} Skipping $key (no value)"
                continue
            fi
            
            echo "  Adding: $key"
            echo "$value" | vercel env add "$key" "$ENVIRONMENT" --force 2>/dev/null || true
        done < .env.production
        
        echo -e "${GREEN}✓${NC} Environment variables synced"
    fi
else
    echo -e "${YELLOW}⚠${NC} .env.production not found"
    echo "  Please set environment variables in Vercel Dashboard:"
    echo "  https://vercel.com/dashboard → Settings → Environment Variables"
    echo ""
    read -p "Continue without syncing? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Exit if env-only mode
if [ "$ENV_ONLY" = true ]; then
    echo -e "${GREEN}✓${NC} Environment sync complete (env-only mode)"
    exit 0
fi

# Deployment
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Deploying to: $ENVIRONMENT${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Build deployment command
DEPLOY_CMD="vercel"

if [ "$ENVIRONMENT" = "production" ]; then
    DEPLOY_CMD="$DEPLOY_CMD --prod"
    echo -e "${YELLOW}⚠${NC} This will deploy to PRODUCTION"
    echo "  Your changes will be live immediately"
    echo ""
    read -p "Are you sure? (yes/N) " -r
    echo
    if [[ ! $REPLY =~ ^yes$ ]]; then
        echo "Deployment cancelled"
        exit 1
    fi
fi

# Run deployment
echo "Running: $DEPLOY_CMD"
echo ""

if $DEPLOY_CMD; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Deployment Successful! 🎉${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    # Get deployment URL
    if [ "$ENVIRONMENT" = "production" ]; then
        echo "Production URL: https://$(vercel ls --prod | grep -m1 'https://' | awk '{print $2}')"
    else
        echo "Preview URL: Check the output above"
    fi
    
    echo ""
    echo "Next steps:"
    echo "  1. Verify deployment: Check the URL above"
    echo "  2. Test API: curl https://YOUR-URL/api/health"
    echo "  3. Check cron jobs: Vercel Dashboard → Cron Jobs"
    echo "  4. Monitor logs: vercel logs --follow"
    echo ""
    
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  Deployment Failed ❌${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check build logs above for errors"
    echo "  2. Verify environment variables in Vercel Dashboard"
    echo "  3. Check vercel.json syntax"
    echo "  4. Run: vercel logs"
    echo ""
    exit 1
fi
