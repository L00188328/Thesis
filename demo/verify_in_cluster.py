"""Healthy-baseline verification and four seed events; never injects a fault."""
import argparse,json,os,time,urllib.request
from datetime import datetime,timezone
import psycopg
from kafka import KafkaProducer,KafkaConsumer,KafkaAdminClient
from scripts.experiments.common import kafka_client_config
from scripts.experiments.controlled_workload import event_for_sequence
from scripts.experiments.partition_key_manifest import select_pair,key_partition
from scripts.experiments.kafka_consumer_progress import discover_partitions,sample_offsets,describe_assignments
from services.common.schema_init import ensure_projection_schema
cfg=kafka_client_config(argparse.Namespace(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],security_protocol='SASL_SSL',sasl_mechanism='PLAIN'))
ensure_projection_schema(os.environ['DATABASE_URL'])
with psycopg.connect(os.environ['DATABASE_URL']) as db:
 assert db.execute('SELECT 1').fetchone()[0]==1
 print('PostgreSQL: reachable; original projection schema initialized',flush=True)
run='K3S-BASELINE-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
a,b=select_pair(run,2)
topics=os.environ['KAFKA_TOPICS'].split(',')
p=KafkaProducer(**cfg,key_serializer=lambda x:x.encode(),value_serializer=lambda x:json.dumps(x).encode(),acks='all')
ids=[];published=[]
for seq in range(1,5):
 topic,event=event_for_sequence(run,seq,a,b,*topics,datetime.now(timezone.utc).isoformat())
 md=p.send(topic,key=event['shipment_id'],value=event).get(timeout=30)
 assert md.partition==key_partition(event['shipment_id'],2)
 ids.append(event['event_id']);published.append({'event_id':event['event_id'],'shipment_id':event['shipment_id'],'topic':topic,'partition':md.partition,'offset':md.offset})
p.flush();p.close()
with psycopg.connect(os.environ['DATABASE_URL']) as db:
 for attempt in range(90):
  history=db.execute('SELECT event_id FROM all_shipment_events WHERE event_id=ANY(%s)',(ids,)).fetchall()
  states=db.execute('SELECT shipment_id,latest_event_version FROM current_shipment_state WHERE shipment_id=ANY(%s)',([a,b],)).fetchall()
  db.commit()
  if {r[0] for r in history}==set(ids) and dict(states)=={a:2,b:2}:break
  time.sleep(2)
 else:raise RuntimeError('Baseline seeds did not fully project')
consumer=KafkaConsumer(**cfg,group_id='shipment-aggregator',enable_auto_commit=False)
partitions=discover_partitions(consumer,topics)
assert len(partitions)==4
admin=KafkaAdminClient(**cfg)
for attempt in range(30):
 offsets=sample_offsets(consumer,partitions,'shipment-aggregator','kafka_admin')
 total=offsets[-1]
 if total['total_lag']==0 and not total['collector_error']:break
 time.sleep(2)
else:raise RuntimeError('No complete zero-lag sample')
assignments=describe_assignments(admin,'shipment-aggregator')
assert len(assignments)==2, 'Expected two aggregator consumer members'
assert sorted(len(x['assignments']) for x in assignments)==[2,2], 'Expected two partitions per member'
q={'query':'query($a:String!,$b:String!){a:shipment(shipmentId:$a){shipmentId latestEventVersion} b:shipment(shipmentId:$b){shipmentId latestEventVersion}}','variables':{'a':a,'b':b}}
req=urllib.request.Request('http://api.thesis-ha.svc.cluster.local/graphql/',data=json.dumps(q).encode(),headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=10) as r:response=json.load(r)
assert not response.get('errors') and response['data']['a']['latestEventVersion']==2 and response['data']['b']['latestEventVersion']==2
print(json.dumps({'baseline_ready':True,'run_id':run,'seed_shipments':[a,b],'expected_seed_events':4,'persisted_seed_events':len(history),'states':dict(states),'published':published,'consumer_offsets':offsets,'consumer_assignments':assignments,'graphql':response},sort_keys=True),flush=True)
admin.close();consumer.close()
