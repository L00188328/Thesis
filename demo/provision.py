#!/usr/bin/env python3
"""Explicit stages for the isolated demo baseline. Contains no failure action."""
import concurrent.futures as cf
import json, os, pathlib, secrets, subprocess, sys, time, urllib.request
ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from scripts.experiments.common import sanitize_text
from demo.azure_cli import run_cli
D=ROOT/'demo'; P=D/'.private'; P.mkdir(exist_ok=True)
STATE=pathlib.Path(os.environ.get('DEMO_STATE_FILE',str(P/'state.json')))
C=json.loads(STATE.read_text()) if STATE.exists() else dict(subscription='e21f069d-8303-4531-b864-98eab35ba089',region='italynorth',rg='rg-thesis-demo-k3s-20261022',shared_rg='rg-thesis-demo-shared-20261022',prefix='thf1demo20261022',password=secrets.token_urlsafe(32))
TAGS=['project=masters-thesis','purpose=live-demo','configuration=k3s-phase-f-demo']
def save():
 C.pop('container',None)  # Migrate obsolete state; no process/container IDs persist.
 STATE.write_text(json.dumps(C,indent=2)+'\n'); STATE.chmod(0o600)
def run(args,**kw):
 r=subprocess.run(args,capture_output=True,text=True,timeout=kw.pop('timeout',1800),**kw)
 if r.returncode: raise RuntimeError(sanitize_text(r.stderr[-7000:]))
 return r.stdout

def az(*args,timeout=1800):
 out=run_cli(C,*args,'--subscription',C['subscription'],'--only-show-errors','--output','json',executor=run,timeout=timeout)
 return json.loads(out) if out.strip() else None

def parallel(items, fn):
 with cf.ThreadPoolExecutor(max_workers=3) as pool:
  for value in pool.map(fn,items): pass

def network():
 C['operator_ip']=run(['curl','-fsS','--max-time','30','https://api.ipify.org']).strip();save()
 for rg in [C['rg'],C['shared_rg']]:
  if az('group','exists','--name',rg):
   old=az('group','show','--name',rg)
   if old.get('tags',{}).get('configuration')!='k3s-phase-f-demo':raise RuntimeError('Refusing existing unowned group '+rg)
  az('group','create','--name',rg,'--location',C['region'],'--tags',*TAGS)
 print('Demo resource groups ready',flush=True)
 az('network','vnet','create','-g',C['rg'],'-n','vnet-demo-k3s','-l',C['region'],'--address-prefixes','10.60.0.0/16','--subnet-name','nodes','--subnet-prefixes','10.60.1.0/24','--tags',*TAGS)
 for n in ['nsg-demo-server','nsg-demo-workers']:
  az('network','nsg','create','-g',C['rg'],'-n',n,'-l',C['region'],'--tags',*TAGS)
 az('network','nsg','rule','create','-g',C['rg'],'--nsg-name','nsg-demo-server','-n','operator','--priority','100','--access','Allow','--protocol','Tcp','--source-address-prefixes',C['operator_ip']+'/32','--destination-port-ranges','22','6443','30080')
 # Azure's default AllowVnetInBound permits cluster traffic; deny public inbound on workers.
 def pip(item):
  name,zone=item
  az('network','public-ip','create','-g',C['rg'],'-n','pip-'+name,'-l',C['region'],'--sku','Standard','--allocation-method','Static','--version','IPv4','--zone',zone,'--tags',*TAGS)
 parallel([('server','3'),('appzone1','1'),('appzone2','2')],pip)
 C['ips']={n:az('network','public-ip','show','-g',C['rg'],'-n','pip-'+n)['ipAddress'] for n in ['server','appzone1','appzone2']};save()
 print('VNet, subnet, NSGs and three zonal static IPv4 addresses ready',flush=True)

def shared():
 template=run_cli(C,'bicep','build','--file','/work/infra/azure/shared.bicep','--stdout','--only-show-errors',executor=run)
 (P/'shared.json').write_text(template)
 params={k:{'value':v} for k,v in dict(location=C['region'],namePrefix=C['prefix'],postgresAdminPassword=C['password'],tags=dict(project='masters-thesis',purpose='live-demo',configuration='k3s-phase-f-demo')).items()}
 (P/'parameters.json').write_text(json.dumps({'parameters':params}));(P/'parameters.json').chmod(0o600)
 az('deployment','group','create','-g',C['shared_rg'],'-n','demo-shared','--template-file','/work/demo/.private/shared.json','--parameters','@/work/demo/.private/parameters.json')
 C['acr']=C['prefix']+'acr';C['eh']=C['prefix']+'-events';C['pg']=C['prefix']+'-postgres';save()
 finish_shared()

def finish_shared():
 for n in ['appzone1','appzone2']:
  az('postgres','flexible-server','firewall-rule','create','-g',C['shared_rg'],'--server-name',C['pg'],'--name','demo-'+n,'--start-ip-address',C['ips'][n],'--end-ip-address',C['ips'][n])
 C['eh_connection']=az('eventhubs','namespace','authorization-rule','keys','list','-g',C['shared_rg'],'--namespace-name',C['eh'],'--name','aggregator-kafka')['primaryConnectionString'];save()
 print('ACR, Event Hubs (two two-partition hubs), PostgreSQL16/shipments ready; HA disabled',flush=True)

def images():
 login=az('acr','login','-n',C['acr'],'--expose-token')
 registry=login['loginServer']; C['registry']=registry;save()
 cfg=str(P/'docker-config')
 run(['docker','--config',cfg,'login',registry,'-u','00000000-0000-0000-0000-000000000000','--password-stdin'],input=login['accessToken'])
 C['images']={}
 for repo in ['thesis-api','thesis-aggregator','thesis-experiment-tools']:
  src='thesishaacr.azurecr.io/'+repo+':397ed5e'; dst=registry+'/'+repo+':397ed5e'
  original=json.loads(run(['docker','image','inspect',src]))[0]['RepoDigests'][0].split('@')[1]
  run(['docker','tag',src,dst]);run(['docker','--config',cfg,'push',dst])
  digest=az('acr','repository','show','-n',C['acr'],'--image',repo+':397ed5e')['digest']
  if digest!=original:raise RuntimeError('Published digest mismatch: '+repo)
  C['images'][repo]=registry+'/'+repo+'@'+digest;save();print(repo+' digest verified '+digest,flush=True)
 az('acr','scope-map','create','-r',C['acr'],'-n','demo-pull','--repository','thesis-api','content/read','--repository','thesis-aggregator','content/read','--repository','thesis-experiment-tools','content/read')
 az('acr','token','create','-r',C['acr'],'-n','demo-pull','--scope-map','demo-pull')
 cred=az('acr','token','credential','generate','-r',C['acr'],'-n','demo-pull','--expiration-in-days','30')
 C['pull_user']=cred['username'];C['pull_password']=cred['passwords'][0]['value'];save()

def vms():
 def create(item):
  name,zone,size,private=item
  az('vm','create','-g',C['rg'],'-n','vm-demo-'+('k3s-server' if name=='server' else name),'-l',C['region'],'--zone',zone,'--size',size,'--image','Ubuntu2404','--admin-username','demoops','--ssh-key-values','/work/demo/.private/id_ed25519.pub','--vnet-name','vnet-demo-k3s','--subnet','nodes','--private-ip-address',private,'--public-ip-address','pip-'+name,'--nsg','nsg-demo-server' if name=='server' else 'nsg-demo-workers','--os-disk-size-gb','64','--storage-sku','StandardSSD_LRS','--security-type','Standard','--tags',*TAGS)
  print(name+' VM provisioned in zone '+zone,flush=True)
 parallel([('server','3','Standard_B2s','10.60.1.10'),('appzone1','1','Standard_D2as_v4','10.60.1.11'),('appzone2','2','Standard_D2as_v4','10.60.1.12')],create)

if __name__=='__main__':
 save()
 try:globals()[sys.argv[1]]()
 except Exception as e:print('FAILED: '+sanitize_text(e),file=sys.stderr);sys.exit(1)
