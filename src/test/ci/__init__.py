"""
CI module for the Borrow Rate & Locate Fee Pricing Engine test package.

This module provides utilities and helpers for CI/CD workflows, particularly for GitHub Actions 
workflows that automate testing processes for the Borrow Rate & Locate Fee Pricing Engine.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Constants and global variables
CI_ROOT = Path(__file__).parent
GITHUB_ACTIONS_DIR = CI_ROOT / 'github_actions'
logger = logging.getLogger(__name__)
__version__ = '1.0.0'


def is_running_in_ci() -> bool:
    """
    Determines if the code is currently running in a CI environment.
    
    Returns:
        bool: True if running in CI environment, False otherwise
    """
    ci_env_vars = ['CI', 'GITHUB_ACTIONS', 'GITLAB_CI', 'JENKINS_URL', 'CIRCLECI', 'TRAVIS']
    return any(os.environ.get(var) for var in ci_env_vars)


def get_workflow_path(workflow_name: str) -> Path:
    """
    Gets the absolute path to a GitHub Actions workflow file.
    
    Args:
        workflow_name (str): Name of the workflow file
        
    Returns:
        Path: Absolute path to the workflow file
    """
    if not workflow_name.endswith('.yml'):
        workflow_name += '.yml'
    
    return GITHUB_ACTIONS_DIR / workflow_name


def setup_ci_logging() -> None:
    """
    Sets up logging configuration for CI environments.
    
    This function configures logging with appropriate format for CI environments,
    setting log level based on environment variables and adding handlers for console output.
    """
    log_level = os.environ.get('CI_LOG_LEVEL', 'INFO')
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure module logger
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s] %(message)s')
        )
        logger.addHandler(console_handler)
    
    logger.setLevel(getattr(logging, log_level))
    logger.info(f"CI logging configured with level: {log_level}")


class CIEnvironment:
    """Class representing a CI environment with configuration and utilities."""
    
    def __init__(self):
        """
        Initialize a new CI environment instance.
        
        Detects the current CI environment, sets properties based on the environment,
        and collects relevant environment variables.
        """
        self._name = "local"
        self._env_vars: Dict[str, Any] = {}
        self._is_github_actions = False
        
        # Detect CI environment
        if os.environ.get('GITHUB_ACTIONS'):
            self.name = "github_actions"
            self.is_github_actions = True
            
            # Collect GitHub Actions specific environment variables
            github_env_vars = [
                'GITHUB_WORKFLOW', 'GITHUB_RUN_ID', 'GITHUB_RUN_NUMBER', 
                'GITHUB_ACTOR', 'GITHUB_REPOSITORY', 'GITHUB_SHA', 
                'GITHUB_REF', 'GITHUB_HEAD_REF', 'GITHUB_BASE_REF'
            ]
            for var in github_env_vars:
                self.env_vars[var] = os.environ.get(var)
                
        elif os.environ.get('GITLAB_CI'):
            self.name = "gitlab_ci"
            
            # Collect GitLab CI specific environment variables
            gitlab_env_vars = [
                'CI_JOB_ID', 'CI_JOB_NAME', 'CI_PIPELINE_ID',
                'CI_PROJECT_PATH', 'CI_COMMIT_SHA', 'CI_COMMIT_REF_NAME'
            ]
            for var in gitlab_env_vars:
                self.env_vars[var] = os.environ.get(var)
                
        elif os.environ.get('JENKINS_URL'):
            self.name = "jenkins"
            
            # Collect Jenkins specific environment variables
            jenkins_env_vars = [
                'BUILD_ID', 'BUILD_NUMBER', 'JOB_NAME',
                'GIT_COMMIT', 'GIT_BRANCH'
            ]
            for var in jenkins_env_vars:
                self.env_vars[var] = os.environ.get(var)
        
        elif os.environ.get('TRAVIS'):
            self.name = "travis_ci"
            
            # Collect Travis CI specific environment variables
            travis_env_vars = [
                'TRAVIS_JOB_ID', 'TRAVIS_BUILD_ID', 'TRAVIS_REPO_SLUG',
                'TRAVIS_COMMIT', 'TRAVIS_BRANCH'
            ]
            for var in travis_env_vars:
                self.env_vars[var] = os.environ.get(var)
                
        elif os.environ.get('CIRCLECI'):
            self.name = "circle_ci"
            
            # Collect CircleCI specific environment variables
            circle_env_vars = [
                'CIRCLE_JOB', 'CIRCLE_BUILD_NUM', 'CIRCLE_PROJECT_REPONAME',
                'CIRCLE_SHA1', 'CIRCLE_BRANCH'
            ]
            for var in circle_env_vars:
                self.env_vars[var] = os.environ.get(var)
                
        elif os.environ.get('CI'):
            self.name = "generic_ci"
            
            # Collect generic CI environment variables
            self.env_vars = {
                'CI': os.environ.get('CI')
            }
            
        logger.debug(f"Detected CI environment: {self.name}")
    
    @property
    def name(self) -> str:
        """
        Get the name of the CI environment.
        
        Returns:
            str: Name of the CI environment
        """
        return self._name
    
    @name.setter
    def name(self, value: str) -> None:
        """
        Set the name of the CI environment.
        
        Args:
            value (str): Name of the CI environment
        """
        self._name = value
    
    @property
    def env_vars(self) -> Dict[str, Any]:
        """
        Get the environment variables for the CI environment.
        
        Returns:
            Dict[str, Any]: Dictionary of environment variables
        """
        return self._env_vars
    
    @env_vars.setter
    def env_vars(self, value: Dict[str, Any]) -> None:
        """
        Set the environment variables for the CI environment.
        
        Args:
            value (Dict[str, Any]): Dictionary of environment variables
        """
        self._env_vars = value
    
    @property
    def is_github_actions(self) -> bool:
        """
        Check if the CI environment is GitHub Actions.
        
        Returns:
            bool: True if GitHub Actions, False otherwise
        """
        return self._is_github_actions
    
    @is_github_actions.setter
    def is_github_actions(self, value: bool) -> None:
        """
        Set whether the CI environment is GitHub Actions.
        
        Args:
            value (bool): True if GitHub Actions, False otherwise
        """
        self._is_github_actions = value
    
    def get_env_var(self, name: str, default: str = '') -> str:
        """
        Gets the value of an environment variable with fallback.
        
        Args:
            name (str): Name of the environment variable
            default (str, optional): Default value if environment variable is not set. Defaults to ''.
            
        Returns:
            str: Value of the environment variable or default
        """
        # Check if the variable exists in our collected env_vars
        if name in self.env_vars and self.env_vars[name] is not None:
            return self.env_vars[name]
        
        # Fall back to os.environ
        return os.environ.get(name, default)
    
    def set_output(self, name: str, value: str) -> bool:
        """
        Sets an output variable in GitHub Actions.
        
        Args:
            name (str): Name of the output variable
            value (str): Value of the output variable
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_github_actions:
            logger.warning("Not running in GitHub Actions, cannot set output.")
            return False
        
        # GitHub Actions has changed how outputs are set over time
        # This approach works with newer versions
        github_output = os.environ.get('GITHUB_OUTPUT')
        if github_output:
            # New way: Write to GITHUB_OUTPUT file
            with open(github_output, 'a') as f:
                f.write(f"{name}={value}\n")
            logger.debug(f"Set output {name}={value} in GITHUB_OUTPUT file")
            return True
        else:
            # Fallback to the older way (deprecated but included for backward compatibility)
            print(f"::set-output name={name}::{value}")
            logger.debug(f"Set output {name}={value} using ::set-output syntax")
            return True
    
    def get_workflow_run_url(self) -> Optional[str]:
        """
        Gets the URL for the current workflow run.
        
        Returns:
            Optional[str]: URL to the workflow run or None if not available
        """
        if not self.is_github_actions:
            return None
        
        repository = self.get_env_var('GITHUB_REPOSITORY')
        run_id = self.get_env_var('GITHUB_RUN_ID')
        
        if repository and run_id:
            return f"https://github.com/{repository}/actions/runs/{run_id}"
        
        return None