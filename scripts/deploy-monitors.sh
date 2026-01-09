#!/bin/bash

# Deployment script for Datadog monitors
# This script deploys all monitors to Datadog for grv-api observability

set -e

# Configuration
DD_API_KEY=${DD_API_KEY:-$(grep DD_API_KEY .env | cut -d'=' -f2)}
DD_APP_KEY=${DD_APP_KEY:-$(grep DD_APP_KEY .env | cut -d'=' -f)}
DD_SITE=${DD_SITE:-$(grep DD_SITE .env | cut -d'=' -f2)}
SERVICE=${DD_SERVICE:-grv-api}
ENV=${DD_ENV:-prod}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v curl &> /dev/null; then
        print_error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        print_error "jq is required but not installed"
        exit 1
    fi
    
    print_status "Dependencies check passed"
}

# Validate environment variables
validate_env() {
    print_status "Validating environment variables..."
    
    if [[ -z "$DD_API_KEY" ]]; then
        print_error "DD_API_KEY is not set"
        exit 1
    fi
    
    if [[ -z "$DD_APP_KEY" ]]; then
        print_error "DD_APP_KEY is not set"
        exit 1
    fi
    
    print_status "Environment validation passed"
}

# Test Datadog API connection
test_api_connection() {
    print_status "Testing Datadog API connection..."
    
    response=$(curl -s -X GET "https://api.${DD_SITE}/api/v1/validate" \
        -H "Content-Type: application/json" \
        -H "DD-API-KEY: ${DD_API_KEY}")
    
    if [[ "$response" == *"valid"* ]]; then
        print_status "Datadog API connection successful"
    else
        print_error "Failed to connect to Datadog API: $response"
        exit 1
    fi
}

# Deploy a single monitor
deploy_monitor() {
    local monitor_file=$1
    local monitor_name=$(basename "$monitor_file" .json)
    
    print_status "Deploying monitor: $monitor_name"
    
    # Read monitor configuration
    monitor_config=$(cat "$monitor_file")
    
    # Create monitor via API
    response=$(curl -s -X POST "https://api.${DD_SITE}/api/v1/monitor" \
        -H "Content-Type: application/json" \
        -H "DD-API-KEY: ${DD_API_KEY}" \
        -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
        -d "$monitor_config")
    
    # Check if monitor was created successfully
    monitor_id=$(echo "$response" | jq -r '.id // empty')
    
    if [[ -n "$monitor_id" && "$monitor_id" != "null" ]]; then
        print_status "✓ Monitor created successfully: ID $monitor_id"
        echo "$monitor_id" >> "deployed_monitors_${ENV}.txt"
    else
        print_error "Failed to create monitor: $monitor_name"
        print_error "Response: $response"
        return 1
    fi
}

# Update existing monitor
update_monitor() {
    local monitor_file=$1
    local monitor_name=$(basename "$monitor_file" .json)
    local monitor_id=$2
    
    print_status "Updating monitor: $monitor_name (ID: $monitor_id)"
    
    # Read monitor configuration
    monitor_config=$(cat "$monitor_file")
    
    # Update monitor via API
    response=$(curl -s -X PUT "https://api.${DD_SITE}/api/v1/monitor/${monitor_id}" \
        -H "Content-Type: application/json" \
        -H "DD-API-KEY: ${DD_API_KEY}" \
        -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
        -d "$monitor_config")
    
    # Check if monitor was updated successfully
    updated_id=$(echo "$response" | jq -r '.id // empty')
    
    if [[ -n "$updated_id" && "$updated_id" == "$monitor_id" ]]; then
        print_status "✓ Monitor updated successfully: ID $monitor_id"
    else
        print_error "Failed to update monitor: $monitor_name"
        print_error "Response: $response"
        return 1
    fi
}

# Check if monitor already exists
check_monitor_exists() {
    local monitor_name=$1
    
    # Get all monitors and search for existing one
    response=$(curl -s -X GET "https://api.${DD_SITE}/api/v1/monitor" \
        -H "Content-Type: application/json" \
        -H "DD-API-KEY: ${DD_API_KEY}" \
        -H "DD-APPLICATION-KEY: ${DD_APP_KEY}")
    
    # Search for monitor by name
    existing_id=$(echo "$response" | jq -r --arg name "$monitor_name" '.[] | select(.name == $name) | .id')
    
    echo "$existing_id"
}

# Deploy all monitors
deploy_all_monitors() {
    print_status "Starting monitor deployment..."
    
    # Clear previous deployment file
    > "deployed_monitors_${ENV}.txt"
    
    # Find all monitor files
    monitor_files=$(find datadog/monitors -name "*.json" -type f)
    
    if [[ -z "$monitor_files" ]]; then
        print_warning "No monitor files found in datadog/monitors/"
        return 0
    fi
    
    total_monitors=0
    successful_deployments=0
    
    for monitor_file in $monitor_files; do
        ((total_monitors++))
        
        # Extract monitor name from JSON
        monitor_name=$(jq -r '.name' "$monitor_file")
        
        print_status "Processing monitor: $monitor_name"
        
        # Check if monitor already exists
        existing_id=$(check_monitor_exists "$monitor_name")
        
        if [[ -n "$existing_id" && "$existing_id" != "null" ]]; then
            print_warning "Monitor already exists (ID: $existing_id), updating..."
            if update_monitor "$monitor_file" "$existing_id"; then
                ((successful_deployments++))
                echo "$existing_id" >> "deployed_monitors_${ENV}.txt"
            fi
        else
            if deploy_monitor "$monitor_file"; then
                ((successful_deployments++))
            fi
        fi
        
        # Small delay to avoid rate limiting
        sleep 1
    done
    
    print_status "Deployment completed: $successful_deployments/$total_monitors monitors deployed successfully"
    
    if [[ $successful_deployments -eq $total_monitors ]]; then
        print_status "✓ All monitors deployed successfully!"
    else
        print_warning "Some monitors failed to deploy. Check the logs above."
    fi
}

# Create deployment event in Datadog
create_deployment_event() {
    local version=${DD_VERSION:-$(grep DD_VERSION .env | cut -d'=' -f2)}
    local git_commit=${GIT_COMMIT:-$(git rev-parse HEAD 2>/dev/null || echo "unknown")}
    local build_number=${BUILD_NUMBER:-"manual"}
    
    print_status "Creating deployment event..."
    
    event_data=$(cat <<EOF
{
    "title": "Deployed grv-api monitors",
    "text": "Deployed Datadog monitors for grv-api service\n\nEnvironment: $ENV\nVersion: $version\nGit Commit: $git_commit\nBuild Number: $build_number\n\nMonitors deployed: $(wc -l < deployed_monitors_${ENV}.txt)",
    "tags": [
        "service:grv-api",
        "env:$ENV",
        "deployment",
        "monitor-deployment",
        "team:backend",
        "owner:grv-team"
    ],
    "alert_type": "info",
    "source_type_name": "deployment"
}
EOF
)
    
    response=$(curl -s -X POST "https://api.${DD_SITE}/api/v1/events" \
        -H "Content-Type: application/json" \
        -H "DD-API-KEY: ${DD_API_KEY}" \
        -d "$event_data")
    
    event_id=$(echo "$response" | jq -r '.event.id // empty')
    
    if [[ -n "$event_id" && "$event_id" != "null" ]]; then
        print_status "✓ Deployment event created: ID $event_id"
    else
        print_warning "Failed to create deployment event"
    fi
}

# Main execution
main() {
    print_status "Starting Datadog monitor deployment for grv-api"
    print_status "Environment: $ENV"
    print_status "Service: $SERVICE"
    
    check_dependencies
    validate_env
    test_api_connection
    deploy_all_monitors
    
    if [[ -f "deployed_monitors_${ENV}.txt" && -s "deployed_monitors_${ENV}.txt" ]]; then
        create_deployment_event
    fi
    
    print_status "Monitor deployment completed successfully!"
    print_status "Deployed monitor IDs saved to: deployed_monitors_${ENV}.txt"
}

# Run main function
main "$@"
