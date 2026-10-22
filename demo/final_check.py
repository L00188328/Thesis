"""Read-only final observations of an already deployed baseline."""
import csv,json,time
from baseline import C,D,az,kube
from scripts.experiments.availability_probe import execute_probe,build_payload
r=json.loads((D/'results/baseline.json').read_text())
fields=['sequence','started_timestamp_utc','finished_timestamp_utc','latency_ms','http_status','instance_id','region','success','error_category','error_detail']
rows=[]
with (D/'results/baseline-graphql-probes.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();start=time.monotonic()
 for n in range(60):
  time.sleep(max(0,start+n-time.monotonic()))
  row=execute_probe(r['graphql_endpoint'],build_payload(r['seed_shipments'][0]),r['seed_shipments'][0],2,5)
  row['sequence']=n+1;rows.append(row);w.writerow(row);f.flush()
r['graphql_probes']={'total':len(rows),'successful':sum(x['success']=='true' for x in rows),'failed':sum(x['success']!='true' for x in rows),'serving_pods':sorted({x['instance_id'] for x in rows if x['success']=='true'})}
assert r['graphql_probes']['failed']==0,'Baseline has failed probes'
assert set(r['graphql_probes']['serving_pods'])=={x['pod'] for x in r['pod_placement'] if x['app']=='api'},'Did not observe both API replicas serving'
r['pod_status']=json.loads(kube('get','pods','-n','thesis-ha','-o','json'))
for p in r['pod_status']['items']:
 if p['metadata'].get('labels',{}).get('app') in ['api','aggregator']:
  assert all(c['ready'] for c in p['status']['containerStatuses'])
r['firewall_rules']=az('postgres','flexible-server','firewall-rule','list','-g',C['shared_rg'],'--server-name',C['pg'],'--query','[].{name:name,startIpAddress:startIpAddress,endIpAddress:endIpAddress}')
r['event_hubs']=az('eventhubs','eventhub','list','-g',C['shared_rg'],'--namespace-name',C['eh'],'--query','[].{name:name,partitions:partitionCount,status:status}')
r['network_security_groups']=[az('network','nsg','show','-g',C['rg'],'-n',n,'--query','{name:name,rules:securityRules[].{name:name,source:sourceAddressPrefix,sources:sourceAddressPrefixes,ports:destinationPortRanges,port:destinationPortRange,access:access}}') for n in ['nsg-demo-server','nsg-demo-workers']]
r['postgres']=az('postgres','flexible-server','show','-g',C['shared_rg'],'-n',C['pg'],'--query','{name:name,state:state,version:version,zone:availabilityZone,ha:highAvailability.mode,sku:sku,storage:storage.storageSizeGb}')
r['created_children']={'subnet':'vnet-demo-k3s/nodes','server_nsg_rule':'nsg-demo-server/operator','event_hubs_authorization_rule':C['eh']+'/aggregator-kafka','consumer_groups':[C['eh']+'/'+x+'/$Default' for x in ['logistic-center-events','delivery-base-events']],'database':C['pg']+'/shipments','firewall_rules':[C['pg']+'/'+x['name'] for x in r['firewall_rules']],'acr_scope_map':C['acr']+'/demo-pull','acr_token':C['acr']+'/demo-pull'}
r['resource_groups']=[C['rg'],C['shared_rg']]
r['other_subscription_resources']=[x for x in az('resource','list','--query','[].{name:name,type:type,resourceGroup:resourceGroup}') if x['resourceGroup'].lower() not in {C['rg'].lower(),C['shared_rg'].lower()}]
(D/'results/baseline.json').write_text(json.dumps(r,indent=2)+'\n')
(D/'results/azure-inventory.json').write_text(json.dumps({k:r[k] for k in ['resource_groups','azure_resources','created_children','vms','network_security_groups','firewall_rules','postgres','event_hubs','other_subscription_resources']},indent=2)+'\n')
print(json.dumps({k:r[k] for k in ['baseline_ready','graphql_probes','vms','network_security_groups','postgres','event_hubs','other_subscription_resources']},indent=2))
