#!/usr/bin/env python3
"""Install and verify baseline only. No fault injection or VM stop operations."""
import base64, concurrent.futures as cf, json, pathlib, subprocess, sys, time
from provision import C,D,P,ROOT,az,save,run
from scripts.experiments.common import sanitize_text
K3S='v1.35.9+k3s1'
KEY=str(P/'id_ed25519');KNOWN=str(P/'known_hosts')
def ssh(node,command,data=None):
 args=['ssh','-i',KEY,'-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+KNOWN,'-o','ConnectTimeout=15']
 if node!='server':
  proxy='ssh -i '+KEY+' -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile='+KNOWN+' -W %h:%p demoops@'+C['ips']['server']
  args+=['-o','ProxyCommand='+proxy]
 dest=C['ips']['server'] if node=='server' else {'appzone1':'10.60.1.11','appzone2':'10.60.1.12'}[node]
 return run(args+['demoops@'+dest,command],input=data,timeout=600)
def kube(*args,data=None):
 return ssh('server','sudo k3s kubectl '+ ' '.join(args),data)
def install():
 for node in ['server','appzone1','appzone2']:
  for attempt in range(30):
   try:ssh(node,'true');break
   except Exception:
    if attempt==29:raise
    time.sleep(5)
 config={'node-name':'demo-server','node-ip':'10.60.1.10','tls-san':[C['ips']['server']],'disable':['traefik','servicelb'],'node-label':['workload=system','topology.kubernetes.io/region=italynorth','topology.kubernetes.io/zone=italynorth-3']}
 def write(node,config):
  ssh(node,'sudo mkdir -p /etc/rancher/k3s && sudo tee /etc/rancher/k3s/config.yaml >/dev/null && sudo chmod 600 /etc/rancher/k3s/config.yaml',json.dumps(config))
 write('server',config)
 ssh('server',"curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION='"+K3S+"' sh -s - server")
 token=ssh('server','sudo cat /var/lib/rancher/k3s/server/node-token').strip()
 def worker(node):
  z='1' if node=='appzone1' else '2'
  config={'server':'https://10.60.1.10:6443','token':token,'node-name':'demo-'+node,'node-ip':'10.60.1.1'+z,'node-label':['workload=thesis-app','demo.thesis/worker='+node,'topology.kubernetes.io/region=italynorth','topology.kubernetes.io/zone=italynorth-'+z],'node-taint':['workload=thesis-app:NoSchedule']}
  write(node,config);ssh(node,"curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION='"+K3S+"' sh -s - agent")
  print(node+' joined',flush=True)
 with cf.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(worker,['appzone1','appzone2']))
 print(kube('wait','--for=condition=Ready','nodes','--all','--timeout=240s'),flush=True)
 print(kube('get','nodes','-o','wide'),flush=True)
 raw=ssh('server','sudo cat /etc/rancher/k3s/k3s.yaml').replace('127.0.0.1',C['ips']['server'])
 (P/'kubeconfig').write_text(raw);(P/'kubeconfig').chmod(0o600)

def deploy():
 kube('apply','-f','-',data=(ROOT/'k8s/azure/base/namespace.yaml').read_text())
 config={'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'thesis-app-config','namespace':'thesis-ha'},'data':{'KAFKA_BOOTSTRAP_SERVERS':C['eh']+'.servicebus.windows.net:9093','KAFKA_TOPICS':'logistic-center-events,delivery-base-events','KAFKA_GROUP_ID':'shipment-aggregator','KAFKA_SECURITY_PROTOCOL':'SASL_SSL','KAFKA_SASL_MECHANISM':'PLAIN','KAFKA_SASL_USERNAME':'$ConnectionString','HEALTH_PORT':'8081','AZURE_REGION':'italynorth'}}
 kube('apply','-f','-',data=json.dumps(config))
 db='postgresql://thesisadmin:'+C['password']+'@'+C['pg']+'.postgres.database.azure.com:5432/shipments?sslmode=require'
 C['database_url']=db;save()
 sec={'apiVersion':'v1','kind':'Secret','metadata':{'name':'thesis-app-secrets','namespace':'thesis-ha'},'type':'Opaque','stringData':{'DATABASE_URL':db,'KAFKA_SASL_PASSWORD':C['eh_connection']}}
 kube('apply','-f','-',data=json.dumps(sec))
 auth=base64.b64encode((C['pull_user']+':'+C['pull_password']).encode()).decode()
 dock={'auths':{C['registry']:{'username':C['pull_user'],'password':C['pull_password'],'auth':auth}}}
 pull={'apiVersion':'v1','kind':'Secret','metadata':{'name':'demo-acr-pull','namespace':'thesis-ha'},'type':'kubernetes.io/dockerconfigjson','stringData':{'.dockerconfigjson':json.dumps(dock)}}
 kube('apply','-f','-',data=json.dumps(pull))
 # Initialize the original schema once before concurrent application startup on fresh deployments.
 initname='schema-init-'+str(int(time.time()))
 initpod={'apiVersion':'v1','kind':'Pod','metadata':{'name':initname,'namespace':'thesis-ha'},'spec':{'restartPolicy':'Never','nodeSelector':{'demo.thesis/worker':'appzone2'},'tolerations':[{'key':'workload','operator':'Equal','value':'thesis-app','effect':'NoSchedule'}],'imagePullSecrets':[{'name':'demo-acr-pull'}],'containers':[{'name':'init','image':C['images']['thesis-experiment-tools'],'command':['python','-c','import os; from services.common.schema_init import ensure_projection_schema; ensure_projection_schema(os.environ["DATABASE_URL"])'],'envFrom':[{'secretRef':{'name':'thesis-app-secrets'}}]}]}}
 kube('apply','-f','-',data=json.dumps(initpod))
 kube('wait',"--for=jsonpath='{.status.phase}'=Succeeded",'pod/'+initname,'-n','thesis-ha','--timeout=180s')
 rendered=run(['kubectl','kustomize',str(D/'k8s')])
 for repo in ['thesis-api','thesis-aggregator']:
  rendered=rendered.replace('REPLACE_ACR_LOGIN_SERVER/'+repo+':REPLACE_IMAGE_TAG',C['images'][repo])
 if 'REPLACE_' in rendered:raise RuntimeError('Unresolved image placeholder')
 kube('apply','-f','-',data=rendered)
 for app in ['aggregator','api']:
  print(kube('rollout','status','deployment/'+app,'-n','thesis-ha','--timeout=300s'),flush=True)
 print(kube('get','pods','-n','thesis-ha','-o','wide'),flush=True)


# Kept callable separately so verification can be repeated without redeploying.
def verify():
 podname='baseline-verifier-'+str(int(time.time()))
 cm={'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'baseline-verifier-code','namespace':'thesis-ha'},'data':{'verify.py':(D/'verify_in_cluster.py').read_text()}}
 kube('apply','-f','-',data=json.dumps(cm))
 pod={'apiVersion':'v1','kind':'Pod','metadata':{'name':podname,'namespace':'thesis-ha'},'spec':{'restartPolicy':'Never','nodeSelector':{'demo.thesis/worker':'appzone2'},'tolerations':[{'key':'workload','operator':'Equal','value':'thesis-app','effect':'NoSchedule'}],'imagePullSecrets':[{'name':'demo-acr-pull'}],'containers':[{'name':'verify','image':C['images']['thesis-experiment-tools'],'command':['python','/demo/verify.py'],'envFrom':[{'configMapRef':{'name':'thesis-app-config'}},{'secretRef':{'name':'thesis-app-secrets'}}],'volumeMounts':[{'name':'code','mountPath':'/demo','readOnly':True}]}],'volumes':[{'name':'code','configMap':{'name':'baseline-verifier-code'}}]}}
 kube('apply','-f','-',data=json.dumps(pod))
 try:kube('wait',"--for=jsonpath='{.status.phase}'=Succeeded",'pod/'+podname,'-n','thesis-ha','--timeout=300s')
 except Exception:
  print(kube('logs',podname,'-n','thesis-ha'),flush=True);raise
 logs=kube('logs',podname,'-n','thesis-ha');print(logs,flush=True)
 result=json.loads(logs.strip().splitlines()[-1])
 pods=json.loads(kube('get','pods','-n','thesis-ha','-o','json'))['items']
 placement=[]
 for app in ['aggregator','api']:
  ready=[p for p in pods if p['metadata'].get('labels',{}).get('app')==app and any(x['type']=='Ready' and x['status']=='True' for x in p.get('status',{}).get('conditions',[]))]
  assert len(ready)==2 and {p['spec']['nodeName'] for p in ready}=={'demo-appzone1','demo-appzone2'},'Incorrect initial placement: '+app
  for p in ready:
   for key in ['node.kubernetes.io/not-ready','node.kubernetes.io/unreachable']:
    assert any(t.get('key')==key and t.get('effect')=='NoExecute' and t.get('tolerationSeconds')==30 for t in p['spec']['tolerations'])
   placement.append({'pod':p['metadata']['name'],'app':app,'node':p['spec']['nodeName'],'ready':True,'image':p['spec']['containers'][0]['image']})
 # External reachability from the recording host, using curl's system trust/network setup.
 endpoint='http://'+C['ips']['server']+':30080'
 health=json.loads(run(['curl','-fsS','--max-time','15',endpoint+'/ready']))
 query=json.dumps({'query':'query($id:String!){shipment(shipmentId:$id){shipmentId latestEventVersion}}','variables':{'id':result['seed_shipments'][0]}})
 external=json.loads(run(['curl','-fsS','--max-time','15','-H','Content-Type: application/json','--data-binary',query,endpoint+'/graphql/']))
 assert health['status']=='ok' and not external.get('errors') and external['data']['shipment']['latestEventVersion']==2
 nodes=json.loads(kube('get','nodes','-o','json'))
 clean_nodes=[{'name':x['metadata']['name'],'zone':x['metadata']['labels'].get('topology.kubernetes.io/zone'),'ready':any(y['type']=='Ready' and y['status']=='True' for y in x['status']['conditions']),'version':x['status']['nodeInfo']['kubeletVersion']} for x in nodes['items']]
 assert len(clean_nodes)==3 and all(x['ready'] for x in clean_nodes)
 result.update(pod_placement=placement,nodes=clean_nodes,external_graphql=external,graphql_endpoint=endpoint+'/graphql/',api_readiness=health,eviction_tolerance_seconds=30,failure_injected=False)
 resources=[]
 for rg in [C['rg'],C['shared_rg']]:resources+=az('resource','list','-g',rg,'--query','[].{name:name,type:type,resourceGroup:resourceGroup}')
 result['azure_resources']=resources
 result['vms']=az('vm','list','-g',C['rg'],'--show-details','--query','[].{name:name,zones:zones,size:hardwareProfile.vmSize,powerState:powerState}')
 assert {x['name']:x['zones'] for x in result['vms']}=={'vm-demo-k3s-server':['3'],'vm-demo-appzone1':['1'],'vm-demo-appzone2':['2']}
 out=D/'results'/'baseline.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');out.with_name('baseline-'+str(int(time.time()))+'.json').write_text(out.read_text())
 print('HEALTHY BASELINE READY; failure_injected=false',flush=True)
 print(json.dumps({'nodes':clean_nodes,'placement':placement,'graphql_endpoint':result['graphql_endpoint'],'resources':resources,'vms':result['vms']},indent=2),flush=True)

if __name__=='__main__':
 try:globals()[sys.argv[1]]()
 except Exception as e:print('FAILED: '+sanitize_text(e),file=sys.stderr);sys.exit(1)
