#!/usr/bin/env python3
"""
Script to send deployment events to Datadog for grv-api service.
This should be called during deployment to track releases and correlate with performance changes.
"""

import os
import sys
import json
import requests
import argparse
from datetime import datetime
from typing import Dict, Any, Optional


class DatadogDeployEvent:
    """Send deployment events to Datadog with proper correlation."""
    
    def __init__(self, api_key: str, app_key: str, site: str = "datadoghq.com"):
        self.api_key = api_key
        self.app_key = app_key
        self.site = site
        self.base_url = f"https://api.{site}/api/v1"
    
    def send_deployment_event(
        self,
        service: str,
        env: str,
        version: str,
        git_commit: Optional[str] = None,
        git_branch: Optional[str] = None,
        build_number: Optional[str] = None,
        deployer: Optional[str] = None,
        changes: Optional[str] = None,
        alert_type: str = "info"
    ) -> Dict[str, Any]:
        """Send a deployment event to Datadog."""
        
        # Get current timestamp
        timestamp = int(datetime.now().timestamp() * 1000)  # milliseconds
        
        # Build event title and text
        title = f"Deployed {service} v{version} to {env}"
        
        text_parts = [
            f"Service: {service}",
            f"Environment: {env}",
            f"Version: {version}",
        ]
        
        if git_commit:
            text_parts.append(f"Git Commit: {git_commit}")
        
        if git_branch:
            text_parts.append(f"Git Branch: {git_branch}")
        
        if build_number:
            text_parts.append(f"Build Number: {build_number}")
        
        if deployer:
            text_parts.append(f"Deployer: {deployer}")
        
        if changes:
            text_parts.append(f"Changes: {changes}")
        
        text_parts.append(f"Deployed at: {datetime.utcnow().isoformat()}")
        
        text = "\n".join(text_parts)
        
        # Build tags
        tags = [
            f"service:{service}",
            f"env:{env}",
            f"version:{version}",
            "deployment",
            "team:backend",
            "owner:grv-team"
        ]
        
        if git_commit:
            tags.append(f"git.commit:{git_commit}")
        
        if git_branch:
            tags.append(f"git.branch:{git_branch}")
        
        if build_number:
            tags.append(f"build.number:{build_number}")
        
        if deployer:
            tags.append(f"deployer:{deployer}")
        
        # Event payload
        event_data = {
            "title": title,
            "text": text,
            "tags": tags,
            "alert_type": alert_type,
            "source_type_name": "deployment",
            "priority": "normal"
        }
        
        # Send event
        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": self.api_key,
            "DD-APPLICATION-KEY": self.app_key
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/events",
                headers=headers,
                json=event_data,
                timeout=30
            )
            
            response.raise_for_status()
            
            result = response.json()
            event_id = result.get("event", {}).get("id")
            
            if event_id:
                print(f"✓ Deployment event sent successfully: {event_id}")
                return {"success": True, "event_id": event_id, "data": result}
            else:
                print("✗ Failed to get event ID from response")
                return {"success": False, "error": "No event ID in response", "data": result}
        
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to send deployment event: {e}")
            return {"success": False, "error": str(e)}
    
    def send_change_tracking_event(
        self,
        service: str,
        env: str,
        version: str,
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a change tracking event for configuration updates."""
        
        title = f"Configuration updated for {service} in {env}"
        
        text_parts = [
            f"Service: {service}",
            f"Environment: {env}",
            f"Version: {version}",
            "",
            "Changes:"
        ]
        
        for key, value in changes.items():
            text_parts.append(f"  {key}: {value}")
        
        text = "\n".join(text_parts)
        
        event_data = {
            "title": title,
            "text": text,
            "tags": [
                f"service:{service}",
                f"env:{env}",
                f"version:{version}",
                "configuration",
                "team:backend",
                "owner:grv-team"
            ],
            "alert_type": "info",
            "source_type_name": "configuration"
        }
        
        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": self.api_key,
            "DD-APPLICATION-KEY": self.app_key
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/events",
                headers=headers,
                json=event_data,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            event_id = result.get("event", {}).get("id")
            if event_id:
                print(f"✓ Change tracking event sent: {event_id}")
                return {"success": True, "event_id": event_id}
            else:
                return {"success": False, "error": "No event ID in response"}
        
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to send change tracking event: {e}")
            return {"success": False, "error": str(e)}


def get_git_info() -> Dict[str, str]:
    """Get git information for the current repository."""
    git_info = {}
    
    try:
        import subprocess
        
        # Get current commit
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            git_info["commit"] = result.stdout.strip()
        
        # Get current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            git_info["branch"] = result.stdout.strip()
        
        # Get commit message
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            git_info["message"] = result.stdout.strip()
        
        # Get remote URL
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            git_info["remote"] = result.stdout.strip()
    
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        pass
    
    return git_info


def main():
    """Main function to handle command line arguments and send deployment event."""
    parser = argparse.ArgumentParser(description="Send deployment events to Datadog")
    
    # Required arguments
    parser.add_argument("--api-key", required=True, help="Datadog API key")
    parser.add_argument("--app-key", required=True, help="Datadog application key")
    
    # Optional arguments with defaults
    parser.add_argument("--service", default="grv-api", help="Service name")
    parser.add_argument("--env", default="prod", help="Environment")
    parser.add_argument("--version", help="Version (overrides DD_VERSION)")
    parser.add_argument("--site", default="datadoghq.com", help="Datadog site")
    parser.add_argument("--git-commit", help="Git commit SHA")
    parser.add_argument("--git-branch", help="Git branch")
    parser.add_argument("--build-number", help="Build number")
    parser.add_argument("--deployer", help="Name/email of deployer")
    parser.add_argument("--changes", help="Description of changes")
    parser.add_argument("--alert-type", default="info", choices=["info", "warning", "error"], help="Alert type")
    
    # Special flags
    parser.add_argument("--auto-git", action="store_true", help="Auto-detect git information")
    parser.add_argument("--config-change", action="store_true", help="Send as configuration change event")
    
    args = parser.parse_args()
    
    # Get version from environment if not provided
    version = args.version or os.getenv("DD_VERSION", "v1.0.0")
    
    # Auto-detect git info if requested
    git_info = {}
    if args.auto_git:
        git_info = get_git_info()
        args.git_commit = args.git_commit or git_info.get("commit")
        args.git_branch = args.git_branch or git_info.get("branch")
        args.changes = args.changes or git_info.get("message")
    
    # Create deploy event sender
    deploy_event = DatadogDeployEvent(args.api_key, args.app_key, args.site)
    
    # Send event
    if args.config_change:
        # Send configuration change event
        changes = {
            "version": version,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if args.changes:
            changes["description"] = args.changes
        
        result = deploy_event.send_change_tracking_event(
            args.service,
            args.env,
            version,
            changes
        )
    else:
        # Send deployment event
        result = deploy_event.send_deployment_event(
            service=args.service,
            env=args.env,
            version=version,
            git_commit=args.git_commit,
            git_branch=args.git_branch,
            build_number=args.build_number,
            deployer=args.deployer,
            changes=args.changes,
            alert_type=args.alert_type
        )
    
    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
