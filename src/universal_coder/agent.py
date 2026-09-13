import json, time, uuid
from universal_coder.models import Message
from universal_coder.tools.core import ToolRegistry
from universal_coder.workspace import Workspace
from universal_coder.verification import Verifier
from universal_coder.events import EventBus
from universal_coder.models import ModelResponse
from universal_coder.state import RunState, Phase
from universal_coder.persistence import RunStore
from universal_coder.approvals import ApprovalPolicy
from universal_coder.git import Git
from universal_coder.interop import ToolBroker, StdioToolServer

SYSTEM='''You are Universal Coder, an autonomous software engineering agent. Work only inside the supplied workspace. Inspect before editing. Make minimal, correct changes. Use tools for repository exploration and edits. Run relevant verification before claiming completion. Never fabricate tool results. If verification fails, diagnose and repair when possible. Do not use destructive commands.''' 

class Agent:
    def __init__(self, provider, workspace, max_steps=40, command_timeout=120, events=None, approvals=None, store=None, reviewer=None, tool_servers=None, tool_grant=None, sandbox_mode="trusted"):
        self.provider=provider; self.workspace=workspace if isinstance(workspace,Workspace) else Workspace(workspace)
        self.approvals=approvals or ApprovalPolicy(); self.tools=ToolRegistry(self.workspace,command_timeout,permissions=None,approvals=self.approvals,sandbox_mode=sandbox_mode); self.tool_broker=ToolBroker(self.tools, tool_grant)
        for server in (tool_servers or []): self.tool_broker.add_server(server)
        self.verifier=Verifier(self.workspace,command_timeout); self.max_steps=max_steps; self.events=events or EventBus(); self.store=store; self.reviewer=reviewer
    def _generate(self, messages, tools, run_id, stream=False):
        if not stream or not hasattr(self.provider, "stream"):
            return self.provider.generate(messages, tools)
        text=[]; calls={}; usage={}
        try:
            chunks=self.provider.stream(messages, tools)
            for chunk in chunks:
                if chunk.text:
                    text.append(chunk.text); self.events.emit("model.delta", text=chunk.text, run_id=run_id)
                usage.update(chunk.usage or {})
                for call in chunk.tool_calls:
                    idx=call.get("index",0); current=calls.setdefault(idx,{"id":call.get("id"),"function":{"name":"","arguments":""}})
                    if call.get("id"): current["id"]=call["id"]
                    fn=call.get("function",{})
                    if fn.get("name"): current["function"]["name"]=fn["name"]
                    current["function"]["arguments"] += fn.get("arguments","") or ""
            return ModelResponse(Message("assistant","".join(text),list(calls.values())),usage)
        except Exception:
            # Streaming is an optimization. Fall back to a normal request if the
            # provider fails before yielding a usable response.
            return self.provider.generate(messages, tools)

    def run(self, objective, verify=True, review=False, stream=False):
        run_id=uuid.uuid4().int>>96; state=RunState(objective); snapshot=self.workspace.snapshot(); git=Git(self.workspace.root)
        self.events.emit('run.started',objective=objective,run_id=run_id)
        context='\n'.join(self.workspace.tree()); messages=[Message('system',SYSTEM),Message('user',objective+'\n\nWorkspace tree:\n'+context)]
        if self.store:self.store.save(run_id,objective,state.phase.value,state.__dict__)
        try:
            state.phase=Phase.EXECUTE
            for i in range(self.max_steps):
                state.steps=i+1; self.events.emit('agent.step',step=state.steps,run_id=run_id)
                response=self._generate(messages,self.tool_broker.schemas(),run_id,stream); messages.append(response.message)
                if not response.message.tool_calls:
                    state.result=response.message.content or 'Agent finished without a textual summary.'
                    if verify:
                        state.phase=Phase.VERIFY; report=self.verifier.run()
                        if report.checks and not report.ok:
                            messages.append(Message('user','Verification failed. Diagnose and fix the failures, then run verification again.\n'+report.summary())); self.events.emit('verification.failed',summary=report.summary()); continue
                        if report.checks: state.result += '\n\nVerification:\n'+report.summary()
                    if review and self.reviewer:
                        review_text=self.reviewer.review(objective,git.diff(),self.tools.schemas()); state.result+='\n\nIndependent review:\n'+review_text
                        if not review_text.strip().upper().startswith('PASS'):
                            messages.append(Message('user','Independent review found issues. Fix them and verify again.\n'+review_text)); continue
                    state.phase=Phase.COMPLETE; self.events.emit('run.completed',steps=state.steps,run_id=run_id); self.tool_broker.close()
                    if self.store:self.store.save(run_id,objective,state.phase.value,state.__dict__)
                    return state.result
                for call in response.message.tool_calls:
                    fn=call.get('function',call); name=fn.get('name'); args=fn.get('arguments',{})
                    if isinstance(args,str):
                        try: args=json.loads(args)
                        except json.JSONDecodeError: args={}
                    self.events.emit('tool.started',name=name,args=args); result=self.tool_broker.call(name,args)
                    messages.append(Message('tool',result.output if result.ok else 'ERROR: '+result.error,tool_call_id=call.get('id')))
                    self.events.emit('tool.completed',name=name,ok=result.ok)
                if self.store:self.store.save(run_id,objective,state.phase.value,state.__dict__)
            state.phase=Phase.FAILED; self.workspace.restore(snapshot); self.events.emit('run.failed',reason='max_steps',run_id=run_id); self.tool_broker.close()
            return 'Agent stopped at the maximum step limit; workspace restored to the pre-run snapshot.'
        except Exception as e:
            state.phase=Phase.FAILED
            try:self.workspace.restore(snapshot)
            except Exception:pass
            self.events.emit('run.failed',error=str(e),run_id=run_id); self.tool_broker.close()
            if self.store:self.store.save(run_id,objective,state.phase.value,state.__dict__)
            raise
