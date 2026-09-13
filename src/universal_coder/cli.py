import argparse, os, shlex
from universal_coder.agent import Agent
from universal_coder.config import Config
from universal_coder.providers import OpenAICompatibleProvider, AnthropicProvider, MockProvider, GeminiProvider, OpenAIResponsesProvider
from universal_coder.server import serve
from universal_coder.persistence import RunStore
from universal_coder.approvals import ApprovalPolicy
from universal_coder.router import ModelRouter
from universal_coder.team import TeamRunner
from universal_coder.parallel import ParallelCoder
from universal_coder.integration import Integrator
from universal_coder.autonomous import AutonomousPipeline
from universal_coder.events import EventBus
from universal_coder.routing import RoutedProvider
from universal_coder.interop import StdioToolServer, ToolGrant
from universal_coder.doctor import main as doctor_main

def make_provider(c):
    if c.provider=='mock': return MockProvider()
    if c.provider=='anthropic': return AnthropicProvider(c.api_key,c.model)
    if c.provider=='gemini': return GeminiProvider(c.api_key,c.model,c.base_url if c.base_url != 'http://localhost:11434/v1' else 'https://generativelanguage.googleapis.com/v1beta')
    if c.provider=='openai-responses': return OpenAIResponsesProvider(c.api_key,c.model,c.base_url if c.base_url != 'http://localhost:11434/v1' else 'https://api.openai.com/v1')
    return OpenAICompatibleProvider(c.base_url,c.api_key,c.model)

def main():
    p=argparse.ArgumentParser(prog='coder'); sub=p.add_subparsers(dest='command')
    run=sub.add_parser('run'); run.add_argument('objective'); run.add_argument('--workspace',default='.'); run.add_argument('--provider',choices=['mock','openai-compatible','openai-responses','anthropic','gemini','auto']); run.add_argument('--base-url'); run.add_argument('--model'); run.add_argument('--api-key'); run.add_argument('--max-steps',type=int); run.add_argument('--no-verify',action='store_true'); run.add_argument('--review',action='store_true'); run.add_argument('--approve',action='store_true'); run.add_argument('--team',action='store_true'); run.add_argument('--parallel',action='store_true'); run.add_argument('--autonomous',action='store_true'); run.add_argument('--integrate-role',choices=['coder','tester','reviewer']); run.add_argument('--stream',action='store_true'); run.add_argument('--sandbox',choices=['trusted','isolated']); run.add_argument('--tool-server',action='append',default=[], help='Explicit stdio tool server command; may be repeated')
    srv=sub.add_parser('serve'); srv.add_argument('--host',default='127.0.0.1'); srv.add_argument('--port',type=int,default=8765)
    hist=sub.add_parser('history'); hist.add_argument('--db',default='.universal-coder/runs.db')
    sub.add_parser('doctor')
    p.add_argument('legacy_objective',nargs='?'); a=p.parse_args()
    if a.command=='serve': return serve(a.host,a.port)
    if a.command=='doctor': return doctor_main()
    if a.command=='history':
        for x in RunStore(a.db).recent(): print(x['id'],x['phase'],x['objective'])
        return 0
    if a.command=='run': obj=a.objective
    else:
        obj=a.legacy_objective
        if not obj:p.print_help();return 2
        a.provider=a.base_url=a.model=a.api_key=None;a.max_steps=None;a.no_verify=False;a.review=False;a.approve=False;a.team=False;a.parallel=False;a.autonomous=False;a.integrate_role=None;a.stream=False;a.sandbox=None;a.tool_server=[];a.workspace='.'
    c=Config.from_env()
    for k,v in [('provider',a.provider),('base_url',a.base_url),('model',a.model),('api_key',a.api_key),('max_steps',a.max_steps),('sandbox_mode',a.sandbox)]:
        if v is not None:setattr(c,k,v)
    primary=make_provider(c) if c.provider != 'auto' else make_provider(Config.from_env())
    if c.provider == 'auto':
        # Environment-defined fallback endpoints: CODER_FALLBACK_URLS=url1,url2
        router = ModelRouter()
        router.register(primary, priority=100, name=getattr(primary, 'name', 'primary'))
        for i, url in enumerate(filter(None, os.getenv('CODER_FALLBACK_URLS','').split(','))):
            fc=Config.from_env(); fc.base_url=url.strip(); router.register(make_provider(fc), priority=90-i, name=f'fallback-{i+1}')
        primary=RoutedProvider(router)
    if a.autonomous:
        result = AutonomousPipeline(lambda role: primary, a.workspace, c.max_steps, c.command_timeout).run(obj, verify=not a.no_verify)
        print(result.output)
        if result.plan.tasks:
            print('\nPLAN:\n- ' + '\n- '.join(result.plan.tasks))
        selected = result.selected_role or 'direct'
        status = 'PASS' if result.ok else 'FAIL'
        print(f'\nSELECTED: {selected}\nSTATUS: {status}')
        return 0 if result.ok else 1
    if a.parallel:
        roles = {
            'coder': obj + '\nImplement the requested change completely. Work directly in your isolated worktree. Add or update tests.',
            'tester': obj + '\nImplement the requested change with special emphasis on regression tests and verification.',
            'reviewer': obj + '\nImplement the requested change defensively, focusing on correctness, security, and integration risks.',
        }
        runner = ParallelCoder(lambda role: primary, max_workers=3)
        results = runner.run(a.workspace, roles)
        for r in results:
            print(f'\n=== {r.role.upper()} ===\n{r.output}\nDIFF:\n{r.diff[:12000]}')
        if a.integrate_role:
            selected = next((r for r in results if r.role == a.integrate_role), None)
            if not selected:
                print('Requested integration role did not produce a result.')
                return 2
            result = Integrator(a.workspace).apply_diff(selected.diff, selected.role)
            print(f'\nINTEGRATION: {result.message}')
            return 0 if result.ok else 1
        return 0 if any(r.ok for r in results) else 1
    if a.team:
        # Specialists may use the same backend; heterogeneous providers can be supplied by API users.
        providers={'architect':primary,'tester':primary,'reviewer':primary}
        opinions=TeamRunner(providers).consult(obj, '\n'.join(Agent(primary,a.workspace,c.max_steps,c.command_timeout).workspace.tree()))
        synthesis=TeamRunner.synthesize(opinions)
        if synthesis: obj=obj+'\n\nTEAM CONSULTATION (advisory; verify independently):\n'+synthesis
    events=EventBus()
    events.subscribe(lambda e: print(f'[event] {e.type} {e.data}', flush=True))
    servers=[]
    for i, command in enumerate(a.tool_server):
        servers.append(StdioToolServer(shlex.split(command), f'cli-{i+1}'))
    agent=Agent(primary,a.workspace,c.max_steps,c.command_timeout,events=events,approvals=ApprovalPolicy(interactive=a.approve),store=RunStore(os.path.join(a.workspace,'.universal-coder','runs.json')),tool_servers=servers,sandbox_mode=c.sandbox_mode)
    print(agent.run(obj,not a.no_verify,a.review,a.stream)); return 0
if __name__=='__main__': raise SystemExit(main())
