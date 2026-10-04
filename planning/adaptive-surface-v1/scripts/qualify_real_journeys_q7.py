#!/usr/bin/env python3
"""Real installed PC broker journeys; no native Todo authority or mocked turns."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys, threading, time, tomllib

GPU = ['GPU-cf22c41f-5b58-77b1-3535-8fadd1ca6505', 'GPU-6c1cac7f-a360-0aef-ba98-2828bfd1db1a']
PROTOCOL='Each turn must contain exactly ONE JSON object: one tool call OR one final answer. Never emit consecutive JSON objects. Once the requested file is present in observed command evidence, answer from that evidence with one cited finding; do not repeat the read or call search unnecessarily. '
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n'); path.chmod(0o600)
def wait(fn, seconds=240):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        value=fn()
        if value: return value
        time.sleep(.1)
    raise RuntimeError('bounded wait expired')

def main():
    p=argparse.ArgumentParser(); p.add_argument('--candidate', type=Path, required=True); p.add_argument('--pc-commit',required=True); p.add_argument('--skills-commit',required=True); p.add_argument('--observer-runtime-sha256',required=True); p.add_argument('--output',type=Path,required=True); p.add_argument('--state',type=Path,required=True); p.add_argument('--smoke',action='store_true')
    a=p.parse_args(); candidate=a.candidate.resolve(strict=True); skills=candidate/'runtime-skills'
    manifest=json.loads((candidate/'release-manifest.json').read_text())
    assert manifest['project_control_commit']==a.pc_commit
    assert manifest['todo_commit']==a.skills_commit
    assert sha(skills/'local-coding-worker/local_worker/observer_runtime.py')==a.observer_runtime_sha256
    assert Path(sys.executable).parent==candidate/'bin'
    sys.path[:0]=[str(skills/'local-coding-worker'),str(skills/'todo-orchestrator'),str(skills/'cuda/scripts')]
    from local_worker.supervisor import ProductionBackend
    from local_worker.residency import observe_residency
    from cuda_controller import compute_processes
    from project_control.as1_jobs import JobService, TrustedObserverFactory, TERMINAL
    from project_control.as1_skill import SkillObserverFactory, SkillService
    from project_control.as1_context import InformationService, ContextHost
    from project_control.as1_packets import SQLitePacketStore, mask_payload
    from project_control.config import ProjectControlConfig, RepositoryConfig, WorkspaceConfig
    from project_control.models import ProjectSnapshot, RepositoryIdentity
    import project_control.as1_jobs as loaded
    assert Path(loaded.__file__).resolve().is_relative_to(candidate)
    a.state.mkdir(parents=True,exist_ok=False,mode=0o700); a.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    project=a.state/'project'; project.mkdir(mode=0o700)
    (project/'README.md').write_text('# SQA fixture\nPurpose: source-bound observer qualification.\n')
    (project/'module.py').write_text('def calculate_total(value):\n    return value + 1\n')
    for args in [('init','-b','main'),('add','README.md','module.py'),('-c','user.name=SQA Fixture','-c','user.email=sqa@example.invalid','commit','-m','SQA source fixture')]:
        subprocess.run(['git','-C',str(project),*args],check=True,capture_output=True)
    head=subprocess.check_output(['git','-C',str(project),'rev-parse','HEAD'],text=True).strip()
    profile=tomllib.loads((skills/'local-coding-worker/config/production-profile.toml').read_text())
    profile['deployment_policy'].update(allowed_gpu_uuids=GPU,max_real_workers=1)
    backend=ProductionBackend(project,service_state_root=a.state/'private-backend',profile=profile)
    scope={'principal':'sqa-real','profile':'observer','project':'sqa'}
    config=ProjectControlConfig(workspaces={'sqa':WorkspaceConfig(authority_repository='source',repositories={'source':RepositoryConfig(root=project)})})
    snapshot=ProjectSnapshot(workspace_id='sqa',project_uuid='sqa-git-only',observed_at='2026-10-04T00:00:00Z',todo_revision=0,repositories={'source':RepositoryIdentity(commit=head,dirty=False)},todo_tables={})
    packets=SQLitePacketStore(a.state/'packets'); turns=[]; sessions=[]; turn_lock=threading.Lock()
    checkpoint_ready=threading.Event(); continue_checkpoint=threading.Event(); pause=[False]
    documents={'approval':{'format':'as1-sqa-root-approval/1','root_claim':'SKclaim957','run_id':'SK-AS1-RUN-1','authorized':True,'resource_ids':['accelerator:'+g for g in GPU],'prior_q4_receipt_sha256':'d470ad46708cb2fb5a2d6cd1836b9eb7a91cb1cdd6b6c26a29570bada9a0d9ce','sequencing':'Root-approved HostCoordinator active-service admission and protected residency before model load; actual CUDA foreground admission independently preempts the owned model; no conflicting foreground lease during inference.'},'source_identity':{'candidate_root':str(candidate),'pc_commit':manifest['project_control_commit'],'skills_commit':manifest['todo_commit'],'release_sha256':sha(candidate/'release-manifest.json'),'observer_runtime_sha256':sha(skills/'local-coding-worker/local_worker/observer_runtime.py'),'fixture_commit':head,'helper_sha256':sha(__file__),'native_catalog_sha256':sha(skills/'integrations/native-skill-catalog.json'),'native_routing_sha256':sha(skills/'integrations/native-skill-routing.md')}}
    write(a.output/'approval.json',documents['approval'])
    unrelated=lambda:sorted((r['uuid'],r['pid'],r['process']) for r in compute_processes() if r['uuid'] not in GPU)
    def protected_identity():
        result={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'processes':{}}
        for pid in [2348,32750]:
            proc=Path('/proc')/str(pid); stat=proc.joinpath('stat').read_text(); fields=stat[stat.rfind(')')+2:].split()
            result['processes'][str(pid)]={'start_ticks':int(fields[19]),'cmdline_sha256':sha(proc/'cmdline')}
        return result
    before=unrelated(); protected_before=protected_identity(); jobs=None; controller=None
    class Adapter:
        def open_sessions(self,count,compute_profile='narrow',parallelism='default'):
            try:
                endpoint=backend.warm(compute_profile=compute_profile,parallelism=parallelism)
                assert sorted(endpoint['gpu_uuids'])==sorted(GPU)
                sessions.append(endpoint); write(a.output/'sessions.json',sessions)
                return {'status':'available','session_ids':[endpoint['service_lease_id']]}
            except Exception as error: return {'status':'unavailable','reason':str(error)}
        def close_session(self,session): return backend.release(session)
        def preemption_status(self,session): return backend.preemption_status(session)
        def run_observer_turn(self,request):
            started=time.monotonic(); result=backend.run_observer_turn(request)
            endpoint=next(s for s in reversed(sessions) if s['service_lease_id']==request.get('session_id'))
            metric={'session_id':request.get('session_id'),'model_id':result.get('model_id'),'model_pid':endpoint['server_pid'],'request':request,'response':result,'request_visible_bytes':len(json.dumps(request).encode()),'duration_seconds':time.monotonic()-started,'output_visible_bytes':len(result.get('text','').encode()),'result':result}
            with turn_lock:
                turns.append(metric); write(a.output/'turns.json',turns)
            print(json.dumps({'event':'real_turn','index':len(turns),'status':result.get('status'),'usage':result.get('usage'),'duration_seconds':metric['duration_seconds']}),flush=True)
            return result
    adapter=Adapter(); information=[None]
    def tools(name,args,access):
        assert access==scope
        return information[0].call(name,project='sqa',**args)
    registrations={name:{'name':name,'root':str(skills/name)} for name in ['cuda','local-coding-worker']}
    trusted=TrustedObserverFactory(skills,documents['source_identity']['observer_runtime_sha256'],backend=adapter,roots=[project,skills],tools=tools,skills=registrations)
    native_factory=SkillObserverFactory(trusted,skills_root=skills)
    documents['execution_policy']={'investigation_max_steps':6,'skill_max_steps':12,'basis':'Root-authorized supported native request budget 1..12 for multi-resource skill routing; native model, parser, sandbox and broker remain authoritative.'}
    def factory(service,job):
        worker=native_factory(service,job)
        if job.mode=='skill':
            original_run=worker.run
            def budgeted_run(request): return original_run({**request,'max_steps':12})
            worker.run=budgeted_run
        return worker
    factory.skills=native_factory.skills
    def compose():
        s=JobService(a.state/'jobs',packets=packets,worker_factory=factory,backend=adapter,retry_seconds=2)
        original=s.checkpoint
        def checkpoint(job,attempt,observations):
            result=original(job,attempt,observations)
            expected_path=str(project/'module.py')
            source_proofs=[read for observation in observations for read in observation.get('source_reads',[]) if read.get('path')==expected_path and read.get('method')=='direct_cat' and read.get('content_sha256')==sha(project/'module.py')]
            if pause[0] and source_proofs:
                pause[0]=False; checkpoint_ready.set()
                if not continue_checkpoint.wait(180): raise RuntimeError('preemption scheduling deadline')
            return result
        s.checkpoint=checkpoint
        information[0]=InformationService(config,packets,lambda _:snapshot,ContextHost('observer','sqa-real',frozenset({'sqa'})),job_lookup=lambda ident,access:s.lookup(ident,access_scope=access))
        return s
    if a.smoke:
        jobs=compose(); skill=SkillService(jobs,skills_root=skills)
        hint=information[0].call('read',project='sqa',paths=['README.md'])
        assert hint['status']=='ok'; assert packets.lookup(hint['packet'],access_scope=scope).packet.alias
        assert jobs.submit(question='test',access_scope=scope)['reason']=='durable_processing_unavailable'
        assert information[0].call('search',project='sqa',query={'kind':'investigation','target':'missing'})['status']=='partial'
        catalog=skill.catalog(access_scope=scope)
        assert any(row['name']=='cuda' and row['status']=='accessible' for row in catalog['skills']),catalog
        assert not backend._slots and not backend._leases and not turns
        write(a.output/'smoke.json',{'status':'passed','source_identity':documents['source_identity'],'zero_model_starts':True})
        print(json.dumps({'event':'interface_smoke','status':'passed'}),flush=True); return
    try:
        jobs=compose().start(); skill=SkillService(jobs,skills_root=skills)
        hint=information[0].call('read',project='sqa',paths=['README.md'])
        write(a.output/'hint.json',hint)
        hint_ref=packets.lookup(hint['packet'],access_scope=scope).packet.alias
        assert hint_ref, hint
        def terminal(ident):
            value=jobs.lookup(ident,access_scope=scope)
            return value if value['job']['status'] in TERMINAL else None
        documents['phase_order']=['read_answer_preflight']
        phase_started=time.monotonic(); phase_turn_start=len(turns)
        preflight=jobs.submit(question=PROTOCOL+'Read the known file module.py directly with cat, then explain calculate_total with one finding citing the observed packet. No discovery is needed. Your trusted current project directory is '+str(project)+'.',access_scope=scope,hints=[hint_ref],request_id='preflight')
        assert preflight['accepted']; documents['preflight_admission']=preflight
        documents['preflight']=wait(lambda:terminal(preflight['job_id']),240)
        assert documents['preflight']['job']['status']=='completed',documents['preflight']
        preflight_observation=next(o for o in documents['preflight']['observations'] if any(r.get('path')==str(project/'module.py') and r.get('method')=='direct_cat' and r.get('content_sha256')==sha(project/'module.py') for r in o.get('source_reads',[])))
        preflight_packet=preflight_observation['packet_id']
        assert any(preflight_packet in f['evidence_packets'] for f in documents['preflight']['job']['findings'])
        preflight_answer=packets.lookup(documents['preflight']['job']['result_packet'],access_scope=scope).packet
        preflight_meaning=(preflight_answer.payload.get('answer','')+' '+' '.join(f['text'] for f in documents['preflight']['job']['findings'])).lower()
        assert 'value + 1' in preflight_meaning or 'adding 1' in preflight_meaning or 'plus one' in preflight_meaning or 'increment' in preflight_meaning
        documents['preflight_metrics']={'status':'passed','turn_start':phase_turn_start,'turn_end':len(turns),'elapsed_seconds':time.monotonic()-phase_started,'checkpoint_pause':False,'actual_public_history_replayed':any(any(m['role']=='assistant' for m in t['request']['messages']) for t in turns[phase_turn_start:])}
        assert documents['preflight_metrics']['actual_public_history_replayed']
        print(json.dumps({'event':'read_answer_preflight','status':'passed','turns':len(turns)-phase_turn_start}),flush=True)
        documents['phase_order'].append('skill_authority')
        phase_started=time.monotonic(); phase_turn_start=len(turns)
        skill_job=skill.submit(query='Each turn must contain exactly ONE JSON object: one tool call OR one final answer, never consecutive objects. For CUDA on V100, read the installed entry and follow its legacy routing map into Volta, including references/legacy-skill-router.md and references/architectures/volta/router.md. Obtain exact native command observations of the relevant map resources. Select one modest exact excerpt from a visited map whose resource hash and line range are verified by your command evidence. Keep synthesis tiny, cite packets for findings, and name unvisited prerequisites as unresolved rather than inventing completeness.',skill='cuda',access_scope=scope,request_id='skill')
        documents['skill_admission']=skill_job; assert skill_job['accepted'],skill_job
        documents['skill_job']=wait(lambda:terminal(skill_job['job_id']),1200)
        read_proofs={read['path']:read for observation in documents['skill_job']['observations'] for read in observation.get('source_reads',[])}
        for relative in ['SKILL.md','references/legacy-skill-router.md','references/architectures/volta/router.md']:
            path=skills/'cuda'/relative
            assert str(path) in read_proofs and read_proofs[str(path)]['content_sha256']==sha(path),read_proofs
        documents['skill']=skill.poll(skill_job['job_id'],access_scope=scope)
        assert documents['skill'].get('status') in {'completed','partial'} and documents['skill'].get('excerpts'),documents['skill']
        assert any(e['resource'] in {'references/legacy-skill-router.md','references/architectures/volta/router.md'} for e in documents['skill']['excerpts'])
        for excerpt in documents['skill']['excerpts']:
            resource=skills/excerpt['skill']/excerpt['resource']
            assert sha(resource)==excerpt['content_sha256']
            exact=''.join(resource.read_text().splitlines(keepends=True)[excerpt['line_start']-1:excerpt['line_end']])
            assert exact==excerpt['content'] and excerpt['verbatim'] is True
        documents['skill_metrics']={'status':'passed','turn_start':phase_turn_start,'turn_end':len(turns),'elapsed_seconds':time.monotonic()-phase_started,'max_steps':12,'checkpoint_pause':False}
        print(json.dumps({'event':'skill_authority','status':'passed','turns':len(turns)-phase_turn_start,'excerpts':len(documents['skill']['excerpts'])}),flush=True)
        documents['phase_order'].append('busy_queue_preemption_restart')
        pause[0]=True; checkpoint_ready.clear(); continue_checkpoint.clear()
        scout=jobs.submit(question=PROTOCOL+'Read the known file module.py directly with cat, then explain calculate_total using one finding citing its observed packet. No discovery or search is needed for this known file. Your trusted current project directory is '+str(project)+'. Reuse retained verified observations after reconnect instead of reading an unchanged file again.',access_scope=scope,hints=[hint_ref],request_id='scout')
        assert scout['accepted']; documents['scout_admission']=scout
        def checkpoint_or_terminal():
            if checkpoint_ready.is_set(): return True
            current=jobs.lookup(scout['job_id'],access_scope=scope)
            if current['job']['status'] in TERMINAL:
                documents['early_scout_terminal']=current
                raise RuntimeError('scout ended before required source checkpoint: '+current['job']['status'])
            return False
        wait(checkpoint_or_terminal,720)
        initial=jobs.lookup(scout['job_id'],access_scope=scope); documents['checkpoint_before']=initial
        checkpoint_session=next(endpoint for endpoint in reversed(sessions) if endpoint['service_lease_id']==turns[-1]['session_id']); documents['checkpoint_session']=checkpoint_session
        module_observation=next(o for o in initial['observations'] if any(r.get('path')==str(project/'module.py') and r.get('content_sha256')==sha(project/'module.py') for r in o.get('source_reads',[])))
        module_packet=module_observation['packet_id']
        assert packets.lookup(module_packet,access_scope=scope).status=='ok'
        # Real worker is paused only after its real command and durable checkpoint.
        admissions=[jobs.submit(question=PROTOCOL+'Read the known file README.md directly with cat, then state its documented fixture purpose with one cited finding. No discovery or search is needed for this known file. Your trusted current project directory is '+str(project)+'.',access_scope=scope,hints=[hint_ref],request_id='queue-'+str(i)) for i in range(3)]
        assert all(x['accepted'] for x in admissions); assert 'busy' in json.dumps(admissions[-1]).lower()
        documents['busy_admissions']=admissions
        documents['useful_while_busy']=information[0].call('read',project='sqa',paths=['README.md','module.py'])
        jobs.shutdown(timeout=.01)
        spec={'schema_version':1,'project_root':str(project),'resources':{'gpu_uuids':GPU,'gpus':2,'cpu_threads':0,'ram_bytes':0,'isolate_nvlink_domain':False,'isolate_pcie_root':False},'argv':[sys.executable,str(skills/'cuda/scripts/qualify_observer_residency.py'),'--foreground-check'],'paths':[],'recipe':'baseline','preempt_grace_seconds':90,'timeout':60,'_storage_root':str(a.state/'controller')}
        write(a.output/'controller-spec.json',spec)
        controller=subprocess.Popen([sys.executable,str(skills/'cuda/scripts/cuda_controller.py'),'run','--spec',str(a.output/'controller-spec.json'),'--json'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'CUDA_RUNTIME_LIBRARY':'/usr/lib/x86_64-linux-gnu/libcudart.so.12.0.146','CUDA_RUNTIME_LIBRARY_SHA256':'960a404b602cc8c9493c4eb0e8ffdb8c3df6bec0ccfbd23f2ec7cbcc56cb5d3c'})
        wait(lambda:backend.preemption_status(checkpoint_session['service_lease_id']).get('preempt_requested'),90)
        continue_checkpoint.set(); assert jobs.shutdown(timeout=120)
        stopped=jobs.lookup(scout['job_id'],access_scope=scope); assert stopped['job']['status']=='yielding',stopped
        documents['checkpoint_yielded']=stopped
        def finished(): backend.poll(); return controller.poll() is not None
        wait(finished,150); stdout,stderr=controller.communicate(); result=json.loads(stdout)
        assert controller.returncode==0 and result.get('ok') is True,(result,stderr)
        documents['foreground']={'result':result,'stderr':stderr,'cleanup_receipts':list(backend.cleanup_receipts)}
        assert backend.cleanup_receipts and not backend._slots
        # Fresh dispatcher object opens existing durable records without inference.
        jobs=compose(); skill=SkillService(jobs,skills_root=skills)
        nturns=len(turns); nsessions=len(sessions)
        documents['poll_after_eviction']=jobs.lookup(scout['job_id'],access_scope=scope)
        documents['exact_after_eviction']=information[0].call('search',project='sqa',query={'kind':'investigation','target':scout['job_id']})
        assert len(turns)==nturns and len(sessions)==nsessions and not backend._slots
        documents['poll_starts_no_model']=True
        jobs.start()
        def terminal(ident):
            value=jobs.lookup(ident,access_scope=scope)
            return value if value['job']['status'] in TERMINAL else None
        documents['scout']=wait(lambda:terminal(scout['job_id']),720)
        assert documents['scout']['job']['status']=='completed',documents['scout']
        assert any(module_packet in finding['evidence_packets'] for finding in documents['scout']['job']['findings'])
        final_packet=packets.lookup(documents['scout']['job']['result_packet'],access_scope=scope).packet
        meaning=(final_packet.payload.get('answer','')+' '+' '.join(f['text'] for f in documents['scout']['job']['findings'])).lower()
        assert final_packet and ('value + 1' in meaning or 'adding 1' in meaning or 'plus one' in meaning or 'increment' in meaning),final_packet
        retained=[o['packet_id'] for o in initial['observations']]
        resumed=[o['packet_id'] for o in documents['scout']['observations']]
        assert all(ref in resumed for ref in retained)
        initial_paths=[read['path'] for o in initial['observations'] for read in o.get('source_reads',[])]
        assert str(project/'module.py') in initial_paths
        all_paths=[read['path'] for o in documents['scout']['observations'] for read in o.get('source_reads',[])]
        assert all(all_paths.count(path)==initial_paths.count(path) for path in initial_paths)
        documents['verified_checkpoint_reuse']={'retained_packet_ids':retained,'unchanged_source_sha256':sha(project/'module.py'),'no_repeated_source_read':True,'before_attempt':initial['job']['attempt'],'after_attempt':documents['scout']['job']['attempt'],'preserved_observations':all(ref in resumed for ref in retained)}
        documents['queued_results']=[wait(lambda ident=item['job_id']:terminal(ident),720) for item in admissions]
        assert all(item['job']['status']=='completed' for item in documents['queued_results']),documents['queued_results']
        documents['exact_scout']=information[0].call('search',project='sqa',query={'kind':'investigation','target':scout['job_id']})
        reloaded_session=next(endpoint for endpoint in sessions if endpoint['server_pid']!=checkpoint_session['server_pid'])
        documents['eviction']={'cleanup_receipts':documents['foreground']['cleanup_receipts'],'initial_session':checkpoint_session,'reloaded_session':reloaded_session}
        assert checkpoint_session['server_pid']!=reloaded_session['server_pid']
        documents['restart']={'dispatcher_before':'stopped','dispatcher_after':jobs.health(),'same_durable_db':str(jobs.path),'model_reloaded_independently':True,'model_before_pid':checkpoint_session['server_pid'],'model_after_pid':reloaded_session['server_pid'],'before_attempt':initial['job']['attempt'],'after_attempt':documents['scout']['job']['attempt']}
        documents['checkpoint']=documents['verified_checkpoint_reuse']
        documents['poll']={'poll':documents['poll_after_eviction'],'exact':documents['exact_after_eviction'],'starts_no_model':True}
        documents['completed']=True
    except Exception as error:
        documents['failure']={'type':type(error).__name__,'reason':str(error)[:2000]}
        raise
    finally:
        cleanup_errors=[]
        continue_checkpoint.set()
        if jobs and not jobs.shutdown(timeout=100): cleanup_errors.append('owned_dispatcher_did_not_stop')
        if controller and controller.poll() is None:
            try:
                controller.terminate(); controller.wait(timeout=15)
            except (subprocess.TimeoutExpired,OSError) as error:
                cleanup_errors.append('owned_controller_stop_unconfirmed:'+type(error).__name__)
        try: wait(lambda:backend.evict().get('quiescent'),60)
        except Exception as error: cleanup_errors.append('owned_model_cleanup_unconfirmed:'+type(error).__name__)
        def safe_observe(fn,label,fallback):
            try: return fn()
            except Exception as error:
                cleanup_errors.append(label+':'+type(error).__name__); return fallback
        documents['cleanup']={'receipts':backend.cleanup_receipts,'remaining_slots':list(backend._slots),'remaining_owned_leases':list(backend._leases),'observation':safe_observe(lambda:observe_residency(GPU),'residency_observation_failed',{'available':False,'devices':[],'processes':[]}),'unrelated_before':before,'unrelated_after':safe_observe(unrelated,'unrelated_observation_failed',None),'protected_identity_before':protected_before,'protected_identity_after':safe_observe(protected_identity,'protected_identity_failed',None)}
        checks={'unrelated_preserved':documents['cleanup']['unrelated_before']==documents['cleanup']['unrelated_after'],'protected_start_identity_preserved':documents['cleanup']['protected_identity_before']==documents['cleanup']['protected_identity_after'],'no_owned_slots':not documents['cleanup']['remaining_slots'],'no_owned_leases':not documents['cleanup']['remaining_owned_leases'],'observation_available':documents['cleanup']['observation']['available'] is True,'exact_approved_devices':{gpu['uuid'] for gpu in documents['cleanup']['observation']['devices']}==set(GPU),'no_approved_apps':not documents['cleanup']['observation']['processes'],'approved_vram_zero':all(gpu['memory_used_mib']==0 for gpu in documents['cleanup']['observation']['devices'])}
        cleanup_errors.extend(key for key,value in checks.items() if not value)
        documents['cleanup']['checks']=checks; documents['cleanup']['errors']=cleanup_errors
        if cleanup_errors: documents['completed']=False
        documents['turns']=turns; documents['sessions']=sessions
        artifacts={}
        for name,value in documents.items():
            clean,_=mask_payload(value); path=a.output/(name+'.json'); write(path,clean)
            artifacts[path.name]=sha(path)
        receipt={'format':'as1-paired-realproof/1','source_identity':documents['source_identity'],'status':'passed' if documents.get('completed') else 'failed','completed':documents.get('completed',False),'journeys':{k:{'status':'passed' if documents.get('completed') else 'failed','artifact':k+'.json'} for k in ['scout','skill','eviction','restart','checkpoint','poll']},'artifacts':artifacts,'inference_artifact':'turns.json','metrics':{'real_turn_count':len(turns),'total_visible_request_bytes':sum(t['request_visible_bytes'] for t in turns),'total_visible_output_bytes':sum(t['output_visible_bytes'] for t in turns),'total_active_seconds':sum(t['duration_seconds'] for t in turns),'usage':[t['result'].get('usage') for t in turns]},'cleanup':documents['cleanup']}
        clean,_=mask_payload(receipt); write(a.output/'receipt.json',clean)
        if cleanup_errors: raise RuntimeError('cleanup proof incomplete; retain unconfirmed leases: '+','.join(cleanup_errors))

if __name__=='__main__': main()
