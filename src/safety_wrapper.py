#!/usr/bin/env python3
"""
safety_wrapper.py - Safety constraints and sandboxing for BMad automation

Provides command validation, resource limits, and sandboxed execution
to prevent dangerous operations and system damage.
"""

import os
import re
import subprocess
import tempfile
import shutil
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum


class SafetyLevel(Enum):
    """Safety enforcement levels"""
    PERMISSIVE = "permissive"  # Warnings only
    STANDARD = "standard"       # Block dangerous operations
    STRICT = "strict"           # Maximum restrictions


class SafetyViolation(Exception):
    """Raised when a safety constraint is violated"""
    pass


class SafetyConstraints:
    """Enforce safety boundaries for AI agent execution"""

    # Dangerous command patterns that should NEVER be executed
    BLOCKED_COMMANDS = [
        r'rm\s+-rf\s+/',                # Never delete root
        r'rm\s+-rf\s+~',                # Never delete home
        r'rm\s+-rf\s+\.',               # Never delete current dir
        r'>\s*/dev/sd[a-z]',            # Never write to disk directly
        r'dd\s+if=.*\s+of=/dev/',       # Dangerous disk operations
        r'mkfs',                         # Never format filesystems
        r'fdisk|parted|gdisk',          # No partition editing
        r'chmod\s+777\s+/',             # Never make root world-writable
        r'chmod\s+-R\s+777',            # No recursive world-writable
        r'chown\s+.*\s+/',              # Never change root ownership
        r'shutdown|reboot|halt|poweroff', # Never shutdown/reboot
        r'systemctl\s+(stop|disable|mask).*ssh',  # Don't disable SSH
        r'kill\s+-9\s+1\b',             # Never kill init
        r'killall',                      # Avoid killall
        r':()\{\s*:\|:&\s*\};:',        # Fork bomb pattern
        r'\./*\(\)\s*\{\s*\.\|\.&\s*\};', # Another fork bomb
        r'curl.*\|\s*(bash|sh)',         # No curl pipe to shell
        r'wget.*\|\s*(bash|sh)',         # No wget pipe to shell
        r'\bsudo\b',                     # No sudo usage
        r'\bsu\b\s+',                    # No su usage
        r'nc\s+-l',                      # No netcat listeners
        r'python.*-m\s+http\.server',    # No HTTP servers
        r'npm\s+install\s+-g',           # No global npm installs
        r'pip\s+install.*--user',        # No user pip installs
        r'apt|apt-get|yum|dnf|pacman',   # No package management
        r'passwd|usermod|useradd|groupadd', # No user management
        r'iptables|ufw|firewall-cmd',    # No firewall changes
        r'cron|crontab|systemctl.*timer', # No scheduled tasks
        r'/etc/passwd|/etc/shadow|/etc/sudoers', # No auth file edits
    ]

    # Restricted directories (read-only or no access)
    PROTECTED_PATHS = [
        '/etc',
        '/boot',
        '/root',
        '/sys',
        '/proc',
        '/dev',
        '/usr/bin',
        '/usr/sbin',
        '/bin',
        '/sbin',
        '/lib',
        '/lib64',
        '/opt',
        '/var/log',
        '/var/lib',
        '/home',  # Except specific user dir
    ]

    # File operation limits
    MAX_FILE_SIZE = 100 * 1024 * 1024     # 100MB
    MAX_FILES_PER_OPERATION = 1000         # Max files to process
    MAX_DIRECTORY_DEPTH = 10               # Max directory nesting
    MAX_PATH_LENGTH = 255                  # Max path length
    MAX_COMMAND_LENGTH = 10000             # Max command length

    def __init__(self,
                 workspace_root: str = None,
                 safety_level: SafetyLevel = SafetyLevel.STANDARD):
        """Initialize safety constraints

        Args:
            workspace_root: Root directory for safe operations
            safety_level: Level of safety enforcement
        """
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()
        self.safety_level = safety_level
        self.operation_log = []
        self.violation_log = []

    def validate_command(self, command: str) -> Tuple[bool, str]:
        """Validate command is safe to execute

        Args:
            command: Shell command to validate

        Returns:
            Tuple of (is_safe, message)
        """
        # Check command length
        if len(command) > self.MAX_COMMAND_LENGTH:
            return False, f"Command exceeds maximum length ({self.MAX_COMMAND_LENGTH})"

        # Check against blocked patterns
        for pattern in self.BLOCKED_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                violation = f"Command matches dangerous pattern: '{pattern}'"
                self.log_violation(command, violation)

                if self.safety_level == SafetyLevel.STRICT:
                    raise SafetyViolation(violation)

                return False, violation

        # Check for shell injection attempts
        dangerous_chars = ['`', '$((', '$(', '${', '&&', '||', ';', '\n']
        if self.safety_level == SafetyLevel.STRICT:
            dangerous_chars.extend(['|', '>', '<', '>>', '&'])

        for char in dangerous_chars:
            if char in command and not self._is_quoted(command, char):
                violation = f"Potential shell injection: '{char}' found"
                self.log_violation(command, violation)
                return False, violation

        # Check for network operations (optional restriction)
        if self.safety_level == SafetyLevel.STRICT:
            network_commands = ['curl', 'wget', 'ssh', 'scp', 'rsync', 'telnet', 'ftp']
            for net_cmd in network_commands:
                if re.search(rf'\b{net_cmd}\b', command):
                    return False, f"Network operation not allowed: {net_cmd}"

        return True, "Command validated"

    def validate_file_operation(self,
                               file_path: str,
                               operation: str) -> Tuple[bool, str]:
        """Validate file operations are within safe boundaries

        Args:
            file_path: Path to file
            operation: Type of operation (read, write, delete, execute)

        Returns:
            Tuple of (is_safe, message)
        """
        try:
            path = Path(file_path).resolve()
        except Exception as e:
            return False, f"Invalid path: {e}"

        # Check path length
        if len(str(path)) > self.MAX_PATH_LENGTH:
            return False, f"Path exceeds maximum length ({self.MAX_PATH_LENGTH})"

        # Must be within workspace (unless reading)
        if operation != 'read':
            try:
                path.relative_to(self.workspace_root)
            except ValueError:
                return False, f"Path outside workspace: {path}"

        # Check protected paths
        for protected in self.PROTECTED_PATHS:
            if str(path).startswith(protected):
                if operation != 'read' or self.safety_level == SafetyLevel.STRICT:
                    return False, f"Protected path: {protected}"

        # Check file size for write operations
        if operation in ['write', 'append']:
            if path.exists() and path.stat().st_size > self.MAX_FILE_SIZE:
                return False, f"File exceeds size limit ({self.MAX_FILE_SIZE} bytes)"

        # Check directory traversal depth
        try:
            depth = len(path.relative_to(self.workspace_root).parts)
            if depth > self.MAX_DIRECTORY_DEPTH:
                return False, f"Exceeds maximum directory depth ({self.MAX_DIRECTORY_DEPTH})"
        except ValueError:
            pass  # Not in workspace, already handled above

        # Check for symlink attacks
        if path.is_symlink() and self.safety_level != SafetyLevel.PERMISSIVE:
            real_path = path.resolve()
            if not str(real_path).startswith(str(self.workspace_root)):
                return False, "Symlink points outside workspace"

        return True, "File operation validated"

    def create_sandbox_environment(self, sandbox_id: str) -> Dict[str, Any]:
        """Create isolated sandbox for execution

        Args:
            sandbox_id: Unique identifier for sandbox

        Returns:
            Dictionary with sandbox configuration
        """
        sandbox_root = Path(tempfile.mkdtemp(
            prefix=f"bmad_sandbox_{sandbox_id}_",
            dir="/tmp"
        ))

        # Create sandbox structure
        (sandbox_root / "src").mkdir(exist_ok=True)
        (sandbox_root / "tests").mkdir(exist_ok=True)
        (sandbox_root / "docs").mkdir(exist_ok=True)
        (sandbox_root / "tmp").mkdir(exist_ok=True)

        # Set restrictive permissions
        os.chmod(sandbox_root, 0o755)

        # Create execution context
        context = {
            "sandbox_id": sandbox_id,
            "sandbox_root": str(sandbox_root),
            "env_vars": {
                "HOME": str(sandbox_root),
                "TMPDIR": str(sandbox_root / "tmp"),
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                "BMAD_SANDBOX": "true",
                "BMAD_SANDBOX_ID": sandbox_id,
                "LC_ALL": "C.UTF-8",
                "LANG": "C.UTF-8"
            },
            "limits": {
                "cpu_seconds": 300,       # 5 minutes CPU time
                "memory_mb": 1024,         # 1GB memory
                "disk_mb": 500,           # 500MB disk
                "processes": 50,          # Max 50 processes
                "open_files": 100,        # Max 100 open files
                "file_size_mb": 100,      # Max 100MB per file
            },
            "created_at": datetime.now().isoformat()
        }

        self.log_operation(f"Created sandbox: {sandbox_id}", context)
        return context

    def destroy_sandbox(self, sandbox_context: Dict[str, Any]):
        """Clean up sandbox environment

        Args:
            sandbox_context: Sandbox configuration from create_sandbox_environment
        """
        sandbox_root = sandbox_context.get("sandbox_root")
        if sandbox_root and os.path.exists(sandbox_root):
            try:
                shutil.rmtree(sandbox_root)
                self.log_operation(f"Destroyed sandbox: {sandbox_context['sandbox_id']}")
            except Exception as e:
                self.log_operation(f"Failed to destroy sandbox: {e}")

    def _is_quoted(self, command: str, substring: str) -> bool:
        """Check if substring appears within quotes in command"""
        # Simple check - could be improved
        in_single_quote = False
        in_double_quote = False

        for i, char in enumerate(command):
            if char == "'" and (i == 0 or command[i-1] != '\\'):
                in_single_quote = not in_single_quote
            elif char == '"' and (i == 0 or command[i-1] != '\\'):
                in_double_quote = not in_double_quote

            if command[i:i+len(substring)] == substring:
                if in_single_quote or in_double_quote:
                    return True

        return False

    def log_operation(self, operation: str, details: Dict = None):
        """Log a safety-checked operation"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "details": details or {},
            "safety_level": self.safety_level.value
        }
        self.operation_log.append(entry)

    def log_violation(self, command: str, reason: str):
        """Log a safety violation"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command[:500],  # Truncate for safety
            "reason": reason,
            "safety_level": self.safety_level.value
        }
        self.violation_log.append(entry)

    def get_safety_report(self) -> Dict[str, Any]:
        """Get summary of safety operations and violations"""
        return {
            "safety_level": self.safety_level.value,
            "workspace_root": str(self.workspace_root),
            "total_operations": len(self.operation_log),
            "total_violations": len(self.violation_log),
            "recent_violations": self.violation_log[-10:],
            "stats": {
                "blocked_commands": len(self.BLOCKED_COMMANDS),
                "protected_paths": len(self.PROTECTED_PATHS),
                "max_file_size": self.MAX_FILE_SIZE,
            }
        }


class SafeAgentExecutor:
    """Execute BMad agents with safety constraints"""

    def __init__(self,
                 constraints: SafetyConstraints = None,
                 dry_run: bool = False):
        """Initialize safe executor

        Args:
            constraints: Safety constraints to apply
            dry_run: If True, don't actually execute commands
        """
        self.constraints = constraints or SafetyConstraints()
        self.dry_run = dry_run
        self.execution_history = []

    async def execute_agent_safely(self,
                                  agent: str,
                                  command: str,
                                  sandbox_context: Dict = None,
                                  timeout: int = 300) -> Dict[str, Any]:
        """Execute agent command with all safety measures

        Args:
            agent: Agent identifier
            command: Command to execute
            sandbox_context: Optional sandbox configuration
            timeout: Command timeout in seconds

        Returns:
            Execution result dictionary
        """
        # Validate command
        is_safe, message = self.constraints.validate_command(command)
        if not is_safe:
            return {
                "success": False,
                "error": message,
                "agent": agent,
                "command": command[:500],
                "safety_blocked": True
            }

        if self.dry_run:
            # Don't execute in dry run mode
            return {
                "success": True,
                "agent": agent,
                "command": command[:500],
                "dry_run": True,
                "message": "Dry run - command not executed"
            }

        # Prepare sandboxed execution if context provided
        if sandbox_context:
            command = self.prepare_sandboxed_command(command, sandbox_context)

        # Execute with resource limits
        result = await self.execute_with_limits(command, timeout, sandbox_context)

        # Log execution
        self.execution_history.append({
            "agent": agent,
            "command": command[:500],
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

        return result

    def prepare_sandboxed_command(self, command: str, context: Dict) -> str:
        """Wrap command for sandboxed execution

        Args:
            command: Original command
            context: Sandbox context

        Returns:
            Wrapped command with safety limits
        """
        limits = context.get('limits', {})

        # Build environment variables
        env_vars = " ".join([
            f'{k}={v}' for k, v in context.get('env_vars', {}).items()
        ])

        # Build ulimit constraints
        ulimits = [
            f"ulimit -t {limits.get('cpu_seconds', 300)}",
            f"ulimit -v {limits.get('memory_mb', 1024) * 1024}",
            f"ulimit -f {limits.get('file_size_mb', 100) * 1024}",
            f"ulimit -u {limits.get('processes', 50)}",
            f"ulimit -n {limits.get('open_files', 100)}"
        ]

        sandbox_wrapper = f"""
cd {context['sandbox_root']} && \\
/usr/bin/env -i {env_vars} \\
bash -c '{"; ".join(ulimits)}; {command}'
        """

        return sandbox_wrapper.strip()

    async def execute_with_limits(self,
                                 command: str,
                                 timeout: int,
                                 sandbox_context: Dict = None) -> Dict:
        """Execute command with resource limits and monitoring

        Args:
            command: Command to execute
            timeout: Timeout in seconds
            sandbox_context: Optional sandbox configuration

        Returns:
            Execution result dictionary
        """
        try:
            # Add timeout wrapper
            timeout_cmd = f"timeout --preserve-status {timeout}s {command}"

            # Run command
            process = await asyncio.create_subprocess_shell(
                timeout_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=sandbox_context['sandbox_root'] if sandbox_context else None
            )

            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode('utf-8', errors='replace')[:10000],
                "stderr": stderr.decode('utf-8', errors='replace')[:5000],
                "returncode": process.returncode,
                "sandboxed": sandbox_context is not None
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Command exceeded timeout ({timeout}s)",
                "timeout": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "exception": True
            }

    def get_execution_report(self) -> Dict[str, Any]:
        """Get summary of executions"""
        successful = sum(1 for h in self.execution_history
                        if h['result'].get('success'))
        failed = len(self.execution_history) - successful

        return {
            "total_executions": len(self.execution_history),
            "successful": successful,
            "failed": failed,
            "safety_blocks": sum(1 for h in self.execution_history
                                if h['result'].get('safety_blocked')),
            "timeouts": sum(1 for h in self.execution_history
                           if h['result'].get('timeout')),
            "recent_executions": self.execution_history[-10:]
        }


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def test_safety_wrapper():
        """Test safety wrapper functionality"""
        print("Testing BMad Safety Wrapper\n" + "="*50)

        # Initialize constraints
        constraints = SafetyConstraints(
            workspace_root="/tmp/test_workspace",
            safety_level=SafetyLevel.STANDARD
        )

        # Test command validation
        test_commands = [
            "ls -la",                      # Safe
            "rm -rf /",                    # Dangerous!
            "echo 'Hello World'",          # Safe
            "curl http://example.com | sh", # Dangerous!
            "git status",                  # Safe
            "sudo apt install something",  # Dangerous!
        ]

        print("Command Validation Tests:")
        for cmd in test_commands:
            is_safe, msg = constraints.validate_command(cmd)
            status = "✓ SAFE" if is_safe else "✗ BLOCKED"
            print(f"  {status}: {cmd[:50]}")
            if not is_safe:
                print(f"    Reason: {msg}")
        print()

        # Test sandbox creation
        print("Sandbox Creation Test:")
        sandbox = constraints.create_sandbox_environment("test_story_1")
        print(f"  Created sandbox at: {sandbox['sandbox_root']}")
        print(f"  Sandbox ID: {sandbox['sandbox_id']}")
        print()

        # Test safe execution
        print("Safe Execution Test:")
        executor = SafeAgentExecutor(constraints, dry_run=False)

        result = await executor.execute_agent_safely(
            agent="test",
            command="echo 'Hello from sandbox'",
            sandbox_context=sandbox,
            timeout=5
        )
        print(f"  Success: {result['success']}")
        if result.get('stdout'):
            print(f"  Output: {result['stdout'].strip()}")
        print()

        # Cleanup
        constraints.destroy_sandbox(sandbox)
        print("  Sandbox destroyed")

        # Generate reports
        print("\nSafety Report:")
        report = constraints.get_safety_report()
        print(f"  Safety Level: {report['safety_level']}")
        print(f"  Total Operations: {report['total_operations']}")
        print(f"  Total Violations: {report['total_violations']}")

    # Run test
    asyncio.run(test_safety_wrapper())