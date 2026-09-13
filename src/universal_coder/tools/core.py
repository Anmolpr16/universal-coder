from dataclasses import dataclass
import subprocess, os
from universal_coder.workspace import Workspace
from universal_coder.permissions import PermissionManager
from universal_coder.approvals import ApprovalPolicy
from universal_coder.sandbox import CommandExecutor, SandboxConfig

@dataclass
class ToolResult:
    ok: bool
    output: str
    error: str = ""

class ToolRegistry:
    def __init__(self, ws: Workspace, timeout=120, max_output=12000, permissions=None, approvals=None, sandbox_mode="trusted"):
        self.ws, self.timeout, self.max_output = ws, timeout, max_output
        self.permissions=permissions or PermissionManager()
        self.approvals=approvals or ApprovalPolicy()
        self.executor=CommandExecutor(ws.root, SandboxConfig(mode=sandbox_mode, timeout=timeout, max_output=max_output))

    def schemas(self):
        return [
          {"type":"function","function":{"name":"list_files","description":"List project files inside the workspace.","parameters":{"type":"object","properties":{}}}},
          {"type":"function","function":{"name":"read_file","description":"Read a UTF-8 project file.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
          {"type":"function","function":{"name":"write_file","description":"Create or replace a project file.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
          {"type":"function","function":{"name":"delete_file","description":"Delete one project file only when necessary.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
          {"type":"function","function":{"name":"run_command","description":"Run a shell command with cwd set to the workspace. Avoid destructive commands.","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}},
        ]

    def call(self,name,args):
        try:
            if name=='list_files': return ToolResult(True,'\n'.join(self.ws.tree()))
            if name=='read_file': return ToolResult(True,self.ws.read(args['path']))
            if name=='write_file':
                if not self.permissions.check('write',args['path']) or not self.approvals.check('write',args['path']): return ToolResult(False,'','write permission denied')
                self.ws.write(args['path'],args['content']); return ToolResult(True,'written '+args['path'])
            if name=='delete_file':
                if not self.permissions.check('delete',args['path']) or not self.approvals.check('delete',args['path']): return ToolResult(False,'','delete permission denied')
                self.ws.delete(args['path']); return ToolResult(True,'deleted '+args['path'])
            if name=='run_command':
                command=args['command'].strip()
                if not self.permissions.check('command',command) or not self.approvals.check('command',command): return ToolResult(False,'','command permission denied')
                if not command: return ToolResult(False,'','empty command')
                banned=['rm -rf /','mkfs','dd if=','shutdown','reboot',':(){:|:&};:']
                if any(x in command for x in banned): return ToolResult(False,'','blocked dangerous command')
                ok,out,error=self.executor.run(command)
                return ToolResult(ok,out,error)
            return ToolResult(False,'',f'unknown tool: {name}')
        except Exception as e: return ToolResult(False,'',f'{type(e).__name__}: {e}')
